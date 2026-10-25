"""Load matching chip-classification runs for the static research viewer."""

from __future__ import annotations

import csv
import json
from pathlib import Path


def _latest(artifacts: Path, prefix: str) -> Path:
    candidates = sorted(path for path in artifacts.glob(f"{prefix}-*") if (path / "metrics.json").is_file())
    if not candidates:
        raise FileNotFoundError(f"No {prefix} research artifact was found")
    return candidates[-1]


def _read_run(path: Path) -> tuple[dict, dict[str, dict]]:
    metrics = json.loads((path / "metrics.json").read_text())
    predictions: dict[str, dict] = {}
    with (path / "predictions.csv").open(newline="") as handle:
        for row in csv.DictReader(handle):
            if row["split"] != "test":
                continue
            predictions[row["sample_id"]] = {
                "probability": float(row["probability"]),
                "prediction": int(row["prediction"]),
                "verified": int(row["has_observed_water"]),
            }
    return metrics, predictions


def load_classification_artifacts(artifacts: Path) -> dict:
    pointer_path = artifacts / "classification-current.json"
    if pointer_path.is_file():
        pointer = json.loads(pointer_path.read_text())
        runs = {name: artifacts / pointer[name] for name in ("baseline", "lstm")}
        if any(not (path / "metrics.json").is_file() for path in runs.values()):
            raise FileNotFoundError("A selected classification artifact is missing")
    else:
        runs = {name: _latest(artifacts, prefix) for name, prefix in (("baseline", "baseline"), ("lstm", "lstm"))}
    loaded = {name: _read_run(path) for name, path in runs.items()}
    sample_sets = {name: set(predictions) for name, (_, predictions) in loaded.items()}
    if sample_sets["baseline"] != sample_sets["lstm"]:
        raise ValueError("Classifier test samples do not match")

    samples: dict[str, dict] = {}
    for sample_id in sorted(sample_sets["baseline"]):
        samples[sample_id] = {name: predictions[sample_id] for name, (_, predictions) in loaded.items()}
    models = {}
    for name, (metrics, _) in loaded.items():
        models[name] = {
            "artifact_id": runs[name].name,
            "model": metrics.get("model"),
            "threshold": metrics["threshold_selection"]["selected_threshold"],
            "test": metrics["metrics"]["test"],
        }
    return {"models": models, "samples": samples}
