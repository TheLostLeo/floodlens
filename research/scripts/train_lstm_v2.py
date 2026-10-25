#!/usr/bin/env python3
"""Train an event-balanced rainfall LSTM with out-of-fold threshold selection."""

from __future__ import annotations

import argparse
import json
import random
import sys
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd

RESEARCH_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RESEARCH_DIR / "src"))

from floodlens_research.lstm_v2 import event_balanced_weights, rainfall_features
from floodlens_research.metrics import binary_metrics, select_f1_threshold
from floodlens_research.paths import artifacts_root, research_data_root

TARGET = "has_observed_water"
SAR_FEATURES = ["vv_mean_db", "vh_mean_db"]


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    import torch
    torch.manual_seed(seed)


def normalise(fit: np.ndarray, values: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    mean = fit.mean(axis=0, keepdims=True)
    std = fit.std(axis=0, keepdims=True)
    return ((values - mean) / np.maximum(std, 1e-6)).astype(np.float32), mean, std


def load_data(root: Path):
    table = pd.read_csv(root / "derived/model_table.csv", dtype={"event_id": str})
    packed = np.load(root / "derived/rainfall_sequences.npz")
    sequences = packed["rainfall_mm"].astype(np.float32)
    if list(table["sample_id"].astype(str)) != list(packed["sample_id"].astype(str)):
        raise ValueError("Rainfall sequence order does not match model_table.csv")
    rain_features, rain_names = rainfall_features(sequences)
    static = np.concatenate([table[SAR_FEATURES].to_numpy(np.float32), np.log1p(rain_features)], axis=1)
    return table, np.log1p(sequences), static, SAR_FEATURES + rain_names


def make_model(static_features: int):
    import torch
    from torch import nn

    class EventRainfallLSTM(nn.Module):
        def __init__(self):
            super().__init__()
            self.lstm = nn.LSTM(input_size=1, hidden_size=24, batch_first=True)
            self.static = nn.Sequential(nn.Linear(static_features, 24), nn.ReLU(), nn.Dropout(.15))
            self.head = nn.Sequential(nn.Linear(48, 24), nn.ReLU(), nn.Dropout(.15), nn.Linear(24, 1))

        def forward(self, sequence, static):
            _, (hidden, _) = self.lstm(sequence)
            return self.head(torch.cat([hidden[-1], self.static(static)], dim=1)).squeeze(1)

    return EventRainfallLSTM()


def fit_predict(table, sequences, static, train_idx, predict_idx, epochs, seed):
    import torch
    from torch import nn

    set_seed(seed)
    sequence_values, _, _ = normalise(sequences[train_idx], sequences)
    static_values, _, _ = normalise(static[train_idx], static)
    model = make_model(static.shape[1])
    optimiser = torch.optim.AdamW(model.parameters(), lr=8e-4, weight_decay=2e-4)
    targets = torch.tensor(table.iloc[train_idx][TARGET].to_numpy(np.float32))
    event_weights = event_balanced_weights(table.iloc[train_idx]["event_id"].to_numpy())
    positives = float((targets == 1).sum())
    class_weight = (len(targets) - positives) / max(positives, 1)
    sample_weights = torch.tensor(event_weights) * torch.where(targets == 1, class_weight, 1.0)
    x_sequence = torch.tensor(sequence_values[train_idx]).unsqueeze(-1)
    x_static = torch.tensor(static_values[train_idx])
    loss_fn = nn.BCEWithLogitsLoss(weight=sample_weights)
    model.train()
    for _ in range(epochs):
        optimiser.zero_grad()
        loss = loss_fn(model(x_sequence, x_static), targets)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 2.0)
        optimiser.step()
    model.eval()
    with torch.no_grad():
        probability = torch.sigmoid(model(
            torch.tensor(sequence_values[predict_idx]).unsqueeze(-1),
            torch.tensor(static_values[predict_idx]),
        )).numpy()
    return model, probability


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path, default=research_data_root())
    parser.add_argument("--seed", type=int, default=20261019)
    parser.add_argument("--epochs", type=int, default=120)
    args = parser.parse_args()
    table, sequences, static, feature_names = load_data(args.data_root)
    test_idx = np.flatnonzero(table["split"].to_numpy() == "test")
    development_idx = np.flatnonzero(table["split"].to_numpy() != "test")
    test_events = sorted(table.iloc[test_idx]["event_id"].unique())

    oof_probability = np.full(len(table), np.nan, dtype=np.float32)
    fold_metrics = []
    development_events = sorted(table.iloc[development_idx]["event_id"].unique())
    for fold, event_id in enumerate(development_events):
        validation_idx = np.flatnonzero((table["event_id"].to_numpy() == event_id) & (table["split"].to_numpy() != "test"))
        training_idx = np.setdiff1d(development_idx, validation_idx)
        _, probability = fit_predict(table, sequences, static, training_idx, validation_idx, args.epochs, args.seed + fold)
        oof_probability[validation_idx] = probability
        fold_metrics.append({"event_id": str(event_id), **binary_metrics(table.iloc[validation_idx][TARGET].to_numpy(), probability, .5)})
    if not np.isfinite(oof_probability[development_idx]).all():
        raise RuntimeError("Out-of-fold predictions are incomplete")
    threshold, oof_metrics = select_f1_threshold(
        table.iloc[development_idx][TARGET].to_numpy(), oof_probability[development_idx]
    )

    final_model, test_probability = fit_predict(
        table, sequences, static, development_idx, test_idx, args.epochs, args.seed
    )
    development_probability = oof_probability[development_idx]
    metrics = {
        "development_oof": binary_metrics(table.iloc[development_idx][TARGET].to_numpy(), development_probability, threshold),
        "test": binary_metrics(table.iloc[test_idx][TARGET].to_numpy(), test_probability, threshold),
    }
    all_probability = np.full(len(table), np.nan, dtype=np.float32)
    all_probability[development_idx] = development_probability
    all_probability[test_idx] = test_probability
    predictions = table[["sample_id", "event_id", "event_name", "split", TARGET]].copy()
    predictions["probability"] = all_probability
    predictions["prediction"] = (all_probability >= threshold).astype(int)

    run_dir = artifacts_root() / f"lstm-v2-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}"
    run_dir.mkdir(parents=True)
    import torch
    torch.save({"state_dict": final_model.state_dict(), "static_features": feature_names, "sequence_transform": "log1p"}, run_dir / "model.pt")
    predictions.to_csv(run_dir / "predictions.csv", index=False)
    payload = {
        "model": "EventBalancedRainfallLSTM",
        "target": "observed-water chip classification during documented flood events",
        "split_strategy": "frozen event-held-out test with leave-one-event-out development predictions",
        "seed": args.seed,
        "epochs": args.epochs,
        "sequence_transform": "log1p then train-fold standardisation",
        "static_features": feature_names,
        "event_balanced_loss": True,
        "threshold_selection": {
            "split": "development out-of-fold events only",
            "criterion": "maximum F1 over thresholds 0.05 to 0.95 in 0.01 increments",
            "selected_threshold": threshold,
            "validation_metrics": oof_metrics,
        },
        "development_folds": fold_metrics,
        "events_by_split": {"development": development_events, "test": test_events},
        "metrics": metrics,
        "limitation": "Only two test events are available; this remains research and is not a resident flood forecast.",
    }
    (run_dir / "metrics.json").write_text(json.dumps(payload, indent=2) + "\n")
    (run_dir / "command.txt").write_text(" ".join(sys.argv) + "\n")
    print(json.dumps({"artifact": str(run_dir), "threshold": threshold, "test": metrics["test"]}, indent=2))


if __name__ == "__main__":
    main()
