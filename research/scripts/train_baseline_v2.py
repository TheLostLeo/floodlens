#!/usr/bin/env python3
"""Train a spatial-summary gradient baseline on the frozen event split."""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "research/src"))

from floodlens_research.chip_features import sar_summary_features
from floodlens_research.metrics import binary_metrics, select_f1_threshold
from floodlens_research.paths import artifacts_root, research_data_root
from floodlens_research.segmentation import portable_path, read_chip

TARGET = "has_observed_water"
RAIN_FEATURES = ["rain_1d_mm", "rain_3d_mm", "rain_7d_mm", "rain_14d_mm", "rain_30d_mm", "rain_60d_mm"]


def main() -> None:
    table = pd.read_csv(research_data_root() / "derived/model_table.csv", dtype={"event_id": str})
    rows = []
    feature_names = None
    for index, row in table.iterrows():
        image, _ = read_chip(portable_path(row["s1_path"], ROOT), portable_path(row["label_path"], ROOT), 512)
        sar, names = sar_summary_features(image)
        feature_names = names + [f"log1p_{name}" for name in RAIN_FEATURES]
        rows.append(np.concatenate([sar, np.log1p(row[RAIN_FEATURES].to_numpy(np.float32))]))
        if (index + 1) % 100 == 0:
            print(f"features={index + 1}/{len(table)}", flush=True)
    features = np.asarray(rows, dtype=np.float32)
    train = table["split"].to_numpy() == "train"
    validation = table["split"].to_numpy() == "validation"
    test = table["split"].to_numpy() == "test"
    model = HistGradientBoostingClassifier(max_iter=300, learning_rate=.04, max_leaf_nodes=21, min_samples_leaf=12, l2_regularization=2, random_state=20261019)
    model.fit(features[train], table.loc[train, TARGET])
    validation_probability = model.predict_proba(features[validation])[:, 1]
    threshold, selection = select_f1_threshold(table.loc[validation, TARGET].to_numpy(), validation_probability)
    probabilities = model.predict_proba(features)[:, 1]
    metrics = {
        split: binary_metrics(table.loc[mask, TARGET].to_numpy(), probabilities[mask], threshold)
        for split, mask in (("train", train), ("validation", validation), ("test", test))
    }
    predictions = table[["sample_id", "event_id", "event_name", "split", TARGET]].copy()
    predictions["probability"] = probabilities
    predictions["prediction"] = (probabilities >= threshold).astype(int)
    run_dir = artifacts_root() / f"baseline-v2-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}"
    run_dir.mkdir(parents=True)
    joblib.dump(model, run_dir / "model.joblib")
    predictions.to_csv(run_dir / "predictions.csv", index=False)
    payload = {
        "model": "SpatialSummaryGradientBoostingClassifier",
        "target": "observed-water chip classification during documented flood events",
        "split_strategy": "frozen event-held-out",
        "seed": 20261019,
        "features": feature_names,
        "threshold_selection": {"split": "validation", "selected_threshold": threshold, "validation_metrics": selection},
        "metrics": metrics,
        "limitation": "SAR summaries preserve more distribution and texture information but still discard pixel geometry.",
    }
    (run_dir / "metrics.json").write_text(json.dumps(payload, indent=2) + "\n")
    print(json.dumps({"artifact": str(run_dir), "threshold": threshold, "test": metrics["test"]}, indent=2))


if __name__ == "__main__":
    main()
