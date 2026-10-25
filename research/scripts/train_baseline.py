#!/usr/bin/env python3
"""Train and score a real-label tabular baseline on held-out flood events."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier

RESEARCH_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RESEARCH_DIR / "src"))

from floodlens_research.metrics import binary_metrics, select_f1_threshold
from floodlens_research.paths import artifacts_root, research_data_root

FEATURES = ["vv_mean_db", "vh_mean_db", "rain_1d_mm", "rain_3d_mm", "rain_7d_mm", "rain_14d_mm", "rain_30d_mm", "rain_60d_mm"]
TARGET = "has_observed_water"


def validate_splits(table: pd.DataFrame) -> None:
    required = {"train", "validation", "test"}
    present = set(table["split"])
    if present != required:
        raise ValueError(f"Expected train/validation/test, found {sorted(present)}")
    train = table[table["split"] == "train"]
    if train[TARGET].nunique() != 2:
        raise ValueError("Training split has only one target class; choose another event split or target threshold.")
    event_sets = {split: set(group["event_id"].astype(str)) for split, group in table.groupby("split")}
    if event_sets["train"] & event_sets["validation"] or event_sets["train"] & event_sets["test"] or event_sets["validation"] & event_sets["test"]:
        raise ValueError("Event leakage detected between splits")


def evaluate_split(model: HistGradientBoostingClassifier, frame: pd.DataFrame, threshold: float) -> tuple[dict[str, object], pd.DataFrame]:
    probability = model.predict_proba(frame[FEATURES])[:, 1]
    predictions = frame[["sample_id", "event_id", "event_name", "split", TARGET]].copy()
    predictions["probability"] = probability
    predictions["prediction"] = (probability >= threshold).astype(int)
    return binary_metrics(frame[TARGET].to_numpy(), probability, threshold), predictions


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path, default=research_data_root())
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    table = pd.read_csv(args.data_root / "derived" / "model_table.csv", dtype={"event_id": str})
    if table[FEATURES + [TARGET]].isna().any().any():
        raise ValueError("Model table has missing features or labels; do not impute them silently.")
    validate_splits(table)
    train = table[table["split"] == "train"]
    model = HistGradientBoostingClassifier(max_iter=200, learning_rate=0.05, max_leaf_nodes=15, l2_regularization=1.0, random_state=args.seed)
    model.fit(train[FEATURES], train[TARGET])
    validation = table[table["split"] == "validation"]
    validation_probability = model.predict_proba(validation[FEATURES])[:, 1]
    threshold, validation_selection_metrics = select_f1_threshold(
        validation[TARGET].to_numpy(), validation_probability
    )

    run_dir = artifacts_root() / f"baseline-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}"
    run_dir.mkdir(parents=True)
    result: dict[str, object] = {
        "model": "HistGradientBoostingClassifier",
        "target": "observed-water chip classification during documented flood events",
        "split_strategy": "event-held-out",
        "seed": args.seed,
        "features": FEATURES,
        "threshold_selection": {
            "split": "validation",
            "criterion": "maximum F1 over thresholds 0.05 to 0.95 in 0.01 increments",
            "selected_threshold": threshold,
            "validation_metrics": validation_selection_metrics,
        },
        "events_by_split": {split: sorted(group["event_id"].astype(str).unique().tolist()) for split, group in table.groupby("split")},
        "metrics": {},
    }
    all_predictions: list[pd.DataFrame] = []
    for split, frame in table.groupby("split"):
        metrics, predictions = evaluate_split(model, frame, threshold)
        result["metrics"][split] = metrics
        all_predictions.append(predictions)
    pd.concat(all_predictions).to_csv(run_dir / "predictions.csv", index=False)
    (run_dir / "metrics.json").write_text(json.dumps(result, indent=2) + "\n")
    (run_dir / "command.txt").write_text(" ".join(sys.argv) + "\n")
    joblib.dump(model, run_dir / "model.joblib")
    print(f"Completed baseline. Held-out metrics: {run_dir / 'metrics.json'}")


if __name__ == "__main__":
    main()
