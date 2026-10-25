#!/usr/bin/env python3
"""Train a small rainfall-sequence LSTM with an event-held-out test set."""

from __future__ import annotations

import argparse
import json
import random
import sys
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from torch import nn
from torch.utils.data import DataLoader, TensorDataset

RESEARCH_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RESEARCH_DIR / "src"))

from floodlens_research.metrics import binary_metrics, select_f1_threshold
from floodlens_research.paths import artifacts_root, research_data_root

STATIC_FEATURES = ["vv_mean_db", "vh_mean_db"]
TARGET = "has_observed_water"


class RainfallLSTM(nn.Module):
    def __init__(self, static_features: int, hidden_size: int = 32) -> None:
        super().__init__()
        self.lstm = nn.LSTM(input_size=1, hidden_size=hidden_size, batch_first=True)
        self.head = nn.Sequential(
            nn.Linear(hidden_size + static_features, 32),
            nn.ReLU(),
            nn.Dropout(0.15),
            nn.Linear(32, 1),
        )

    def forward(self, sequence: torch.Tensor, static: torch.Tensor) -> torch.Tensor:
        _, (hidden, _) = self.lstm(sequence)
        return self.head(torch.cat([hidden[-1], static], dim=1)).squeeze(1)


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def load_data(data_root: Path) -> tuple[pd.DataFrame, np.ndarray]:
    derived = data_root / "derived"
    table = pd.read_csv(derived / "model_table.csv", dtype={"event_id": str})
    packed = np.load(derived / "rainfall_sequences.npz")
    sample_ids = packed["sample_id"].astype(str)
    if list(table["sample_id"].astype(str)) != list(sample_ids):
        raise ValueError("Rainfall sequence order does not match model_table.csv; rebuild features.")
    sequences = packed["rainfall_mm"].astype(np.float32)
    if table[STATIC_FEATURES + [TARGET]].isna().any().any() or not np.isfinite(sequences).all():
        raise ValueError("Missing model values found; do not impute them silently.")
    groups = {split: set(frame["event_id"].astype(str)) for split, frame in table.groupby("split")}
    if set(groups) != {"train", "validation", "test"} or groups["train"] & groups["validation"] or groups["train"] & groups["test"] or groups["validation"] & groups["test"]:
        raise ValueError("Event-held-out split is missing or leaky")
    if table.loc[table["split"] == "train", TARGET].nunique() != 2:
        raise ValueError("Training split has only one target class; choose a different frozen split.")
    return table, sequences


def normalise(train: np.ndarray, values: np.ndarray) -> np.ndarray:
    mean = train.mean(axis=0, keepdims=True)
    std = train.std(axis=0, keepdims=True)
    return (values - mean) / np.maximum(std, 1e-6)


def tensors(table: pd.DataFrame, sequence: np.ndarray, indices: np.ndarray, static: np.ndarray, device: torch.device) -> TensorDataset:
    return TensorDataset(
        torch.tensor(sequence[indices], dtype=torch.float32, device=device).unsqueeze(-1),
        torch.tensor(static[indices], dtype=torch.float32, device=device),
        torch.tensor(table.iloc[indices][TARGET].to_numpy(dtype=np.float32), dtype=torch.float32, device=device),
    )


@torch.no_grad()
def probabilities(model: nn.Module, dataset: TensorDataset) -> np.ndarray:
    model.eval()
    sequence, static, _ = dataset.tensors
    return torch.sigmoid(model(sequence, static)).detach().cpu().numpy()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path, default=research_data_root())
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--epochs", type=int, default=40)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--device", choices=["auto", "cpu", "cuda"], default="auto")
    args = parser.parse_args()
    if args.device == "cuda" and not torch.cuda.is_available():
        raise SystemExit("CUDA was requested but is not available")
    device = torch.device("cuda" if args.device == "auto" and torch.cuda.is_available() else args.device if args.device != "auto" else "cpu")
    set_seed(args.seed)
    table, raw_sequences = load_data(args.data_root)
    train_idx = np.flatnonzero(table["split"].to_numpy() == "train")
    val_idx = np.flatnonzero(table["split"].to_numpy() == "validation")
    test_idx = np.flatnonzero(table["split"].to_numpy() == "test")
    sequences = normalise(raw_sequences[train_idx], raw_sequences)
    static_raw = table[STATIC_FEATURES].to_numpy(dtype=np.float32)
    static = normalise(static_raw[train_idx], static_raw)
    train_set = tensors(table, sequences, train_idx, static, device)
    val_set = tensors(table, sequences, val_idx, static, device)
    test_set = tensors(table, sequences, test_idx, static, device)
    loader = DataLoader(train_set, batch_size=args.batch_size, shuffle=True, generator=torch.Generator().manual_seed(args.seed))
    model = RainfallLSTM(static_features=len(STATIC_FEATURES)).to(device)
    y_train = train_set.tensors[2]
    positives = y_train.sum().item()
    pos_weight = torch.tensor([(len(y_train) - positives) / max(positives, 1.0)], device=device)
    loss_function = nn.BCEWithLogitsLoss(pos_weight=pos_weight)
    optimiser = torch.optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-4)
    best_state: dict[str, torch.Tensor] | None = None
    best_score = -1.0
    best_epoch = 0
    for epoch in range(1, args.epochs + 1):
        model.train()
        for sequence, static_batch, target in loader:
            optimiser.zero_grad()
            loss = loss_function(model(sequence, static_batch), target)
            loss.backward()
            optimiser.step()
        validation_probability = probabilities(model, val_set)
        validation_score = binary_metrics(val_set.tensors[2].cpu().numpy(), validation_probability)["f1"]
        if validation_score > best_score:
            best_score = float(validation_score)
            best_epoch = epoch
            best_state = {name: value.detach().cpu().clone() for name, value in model.state_dict().items()}
    if best_state is None:
        raise RuntimeError("LSTM produced no validation checkpoint")
    model.load_state_dict(best_state)
    validation_probability = probabilities(model, val_set)
    selected_threshold, validation_selection_metrics = select_f1_threshold(
        val_set.tensors[2].cpu().numpy(), validation_probability
    )

    run_dir = artifacts_root() / f"lstm-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}"
    run_dir.mkdir(parents=True)
    all_predictions: list[pd.DataFrame] = []
    metrics: dict[str, object] = {}
    for name, indices, dataset in (("train", train_idx, train_set), ("validation", val_idx, val_set), ("test", test_idx, test_set)):
        probability = probabilities(model, dataset)
        metrics[name] = binary_metrics(
            table.iloc[indices][TARGET].to_numpy(), probability, selected_threshold
        )
        predictions = table.iloc[indices][["sample_id", "event_id", "event_name", "split", TARGET]].copy()
        predictions["probability"] = probability
        predictions["prediction"] = (probability >= selected_threshold).astype(int)
        all_predictions.append(predictions)
    torch.save({"state_dict": model.state_dict(), "static_features": STATIC_FEATURES, "sequence_days": raw_sequences.shape[1]}, run_dir / "model.pt")
    pd.concat(all_predictions).to_csv(run_dir / "predictions.csv", index=False)
    payload = {
        "model": "RainfallLSTM",
        "target": "observed-water chip classification during documented flood events",
        "split_strategy": "event-held-out",
        "device": str(device),
        "seed": args.seed,
        "epochs_requested": args.epochs,
        "best_validation_epoch": best_epoch,
        "threshold_selection": {
            "split": "validation",
            "criterion": "maximum F1 over thresholds 0.05 to 0.95 in 0.01 increments",
            "selected_threshold": selected_threshold,
            "validation_metrics": validation_selection_metrics,
        },
        "static_features": STATIC_FEATURES,
        "rainfall_sequence_days": int(raw_sequences.shape[1]),
        "events_by_split": {split: sorted(group["event_id"].astype(str).unique().tolist()) for split, group in table.groupby("split")},
        "metrics": metrics,
        "limitation": "This benchmark has few independent flood events. The saved held-out result is exploratory research, not a resident-facing flood forecast or warning.",
    }
    (run_dir / "metrics.json").write_text(json.dumps(payload, indent=2) + "\n")
    (run_dir / "command.txt").write_text(" ".join(sys.argv) + "\n")
    print(f"Completed LSTM. Held-out metrics: {run_dir / 'metrics.json'}")


if __name__ == "__main__":
    main()
