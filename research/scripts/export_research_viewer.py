#!/usr/bin/env python3
"""Export held-out predictions into the static, offline research viewer."""

from __future__ import annotations

import csv
import json
import sys
import warnings
from pathlib import Path

import numpy as np
import rasterio
from rasterio.errors import NotGeoreferencedWarning

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "research" / "src"))

from floodlens_research.segmentation import load_split, portable_path, read_chip
from floodlens_research.classification_artifacts import load_classification_artifacts

warnings.filterwarnings("ignore", category=NotGeoreferencedWarning)


def current_artifact() -> Path:
    pointer = ROOT / "research/artifacts/segmentation-current.json"
    if pointer.is_file():
        payload = json.loads(pointer.read_text())
        return ROOT / payload["path"]
    return ROOT / "research/artifacts/segmentation-latest"


def write_png(path: Path, rgb: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(path, "w", driver="PNG", height=rgb.shape[0], width=rgb.shape[1], count=3, dtype="uint8") as target:
        target.write(np.moveaxis(rgb, -1, 0))


def sar_rgb(image: np.ndarray) -> np.ndarray:
    channels = []
    for band in image:
        low, high = np.nanpercentile(band, [2, 98])
        channels.append(np.clip((band - low) / max(high - low, 1e-6), 0, 1))
    vv, vh = channels
    return (np.stack((vv, vh, (vv + vh) / 2), -1) * 255).astype(np.uint8)


def mask_rgb(mask: np.ndarray) -> np.ndarray:
    rgb = np.zeros((*mask.shape, 3), dtype=np.uint8)
    rgb[mask == 0] = [24, 42, 54]
    rgb[mask == 1] = [39, 181, 214]
    rgb[mask < 0] = [105, 105, 105]
    return rgb


def error_rgb(truth: np.ndarray, prediction: np.ndarray) -> np.ndarray:
    rgb = np.zeros((*truth.shape, 3), dtype=np.uint8)
    valid = truth >= 0
    rgb[valid & (truth == prediction)] = [31, 74, 82]
    rgb[valid & (truth == 0) & (prediction == 1)] = [244, 163, 64]
    rgb[valid & (truth == 1) & (prediction == 0)] = [238, 82, 99]
    rgb[~valid] = [90, 90, 90]
    return rgb


def test_metrics(report: dict, model_name: str) -> dict:
    model = report["models"][model_name]
    return model.get("test", model.get("splits", {}).get("test", {}))


def experiment_history(current: Path, current_report: dict) -> list[dict]:
    reports = [(current, current_report)]
    prototype = ROOT / "research/artifacts/segmentation-latest/metrics.json"
    if prototype.is_file() and prototype.parent != current:
        reports.append((prototype.parent, json.loads(prototype.read_text())))
    history = []
    for path, report in reports:
        history.append({
            "artifact_id": report.get("artifact_id", path.name),
            "created_at": report.get("created_at"),
            "resolution": report.get("native_resolution", report.get("resolution")),
            "tile_size": report.get("tile_size"),
            "best_epoch": report.get("best_epoch"),
            "models": {name: test_metrics(report, name) for name in ("extra_trees", "unet") if name in report.get("models", {})},
        })
    return history


def main() -> None:
    artifact = current_artifact()
    metrics = json.loads((artifact / "metrics.json").read_text())
    predictions = np.load(artifact / "predictions.npz")
    classifiers = load_classification_artifacts(ROOT / "research/artifacts")
    size = int(metrics.get("native_resolution", metrics.get("resolution", 512)))
    assignments = load_split(ROOT / "data/research/derived/event_split.json")
    with (ROOT / "data/research/derived/manifest.csv").open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    output = ROOT / "research/viewer/data"
    output.mkdir(parents=True, exist_ok=True)
    samples = []
    for row in rows:
        if assignments.get(str(row["event_id"])) != "test":
            continue
        image, truth = read_chip(portable_path(row["s1_path"], ROOT), portable_path(row["label_path"], ROOT), size)
        sample_id = row["sample_id"]
        write_png(output / f"{sample_id}-sar.png", sar_rgb(image))
        write_png(output / f"{sample_id}-label.png", mask_rgb(truth))
        models = {}
        for model_name, key in (("extra_trees", "tree"), ("unet", "unet")):
            probability = predictions[f"{key}__{sample_id}"]
            threshold = metrics["models"][model_name]["threshold"]
            predicted = (probability >= threshold).astype(np.int16)
            prediction_path = f"data/{sample_id}-{model_name}.png"
            errors_path = f"data/{sample_id}-{model_name}-errors.png"
            write_png(ROOT / "research/viewer" / prediction_path, mask_rgb(predicted))
            write_png(ROOT / "research/viewer" / errors_path, error_rgb(truth, predicted))
            chip = next(item for item in metrics["models"][model_name]["chips"] if item["sample_id"] == sample_id)
            models[model_name] = {"prediction": prediction_path, "errors": errors_path, "metrics": chip}
        samples.append({
            "sample_id": sample_id,
            "event_id": row["event_id"],
            "event_name": row["event_name"],
            "event_date": row["event_date"],
            "latitude": float(row["latitude"]),
            "longitude": float(row["longitude"]),
            "sar": f"data/{sample_id}-sar.png",
            "label": f"data/{sample_id}-label.png",
            "models": models,
            "classifiers": classifiers["samples"][sample_id],
        })
    models = {}
    for name, model in metrics["models"].items():
        events = model.get("events", [])
        models[name] = {
            "threshold": model["threshold"],
            "test": test_metrics(metrics, name),
            "events": [event for event in events if event.get("split", "test") == "test"],
        }
    run_keys = (
        "artifact_id", "created_at", "native_resolution", "tile_size", "overlap", "seed",
        "epochs_requested", "epochs_trained", "best_epoch", "checkpoint_selection",
        "threshold_selection", "elapsed_seconds",
    )
    payload = {
        "title": "FloodLens historical-event research viewer",
        "disclaimer": "Research-only observed-water mapping. Labels may include permanent water. This is not a forecast, warning, depth estimate, or property-level result.",
        "run": {key: metrics.get(key) for key in run_keys},
        "experiments": experiment_history(artifact, metrics),
        "models": models,
        "classifiers": classifiers["models"],
        "samples": samples,
    }
    (output / "viewer-data.json").write_text(json.dumps(payload, indent=2) + "\n")
    print(f"Exported {len(samples)} held-out chips from {artifact.name} to {output}")


if __name__ == "__main__":
    main()
