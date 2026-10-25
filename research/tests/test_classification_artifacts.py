import csv
import json

import pytest

from floodlens_research.classification_artifacts import load_classification_artifacts


def write_run(root, name, model, threshold, rows):
    run = root / name
    run.mkdir()
    (run / "metrics.json").write_text(json.dumps({
        "model": model,
        "threshold_selection": {"selected_threshold": threshold},
        "metrics": {"test": {"f1": 0.6, "pr_auc": 0.7}},
    }))
    with (run / "predictions.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["sample_id", "split", "has_observed_water", "probability", "prediction"])
        writer.writeheader()
        writer.writerows(rows)


def test_loads_latest_matching_runs_and_only_test_predictions(tmp_path):
    rows = [
        {"sample_id": "train-chip", "split": "train", "has_observed_water": 1, "probability": .9, "prediction": 1},
        {"sample_id": "test-chip", "split": "test", "has_observed_water": 0, "probability": .2, "prediction": 0},
    ]
    write_run(tmp_path, "baseline-20260101T000000Z", "old", .1, rows)
    write_run(tmp_path, "baseline-20260102T000000Z", "HistGradientBoostingClassifier", .3, rows)
    write_run(tmp_path, "lstm-20260102T000000Z", "RainfallLSTM", .6, rows)

    result = load_classification_artifacts(tmp_path)

    assert result["models"]["baseline"]["threshold"] == .3
    assert result["models"]["lstm"]["threshold"] == .6
    assert result["samples"]["test-chip"]["lstm"] == {
        "probability": .2, "prediction": 0, "verified": 0,
    }
    assert "train-chip" not in result["samples"]


def test_rejects_classifier_runs_with_different_test_samples(tmp_path):
    write_run(tmp_path, "baseline-20260102T000000Z", "baseline", .3, [
        {"sample_id": "a", "split": "test", "has_observed_water": 0, "probability": .2, "prediction": 0},
    ])
    write_run(tmp_path, "lstm-20260102T000000Z", "lstm", .6, [
        {"sample_id": "b", "split": "test", "has_observed_water": 1, "probability": .8, "prediction": 1},
    ])

    with pytest.raises(ValueError, match="test samples do not match"):
        load_classification_artifacts(tmp_path)


def test_pointer_keeps_rejected_candidate_out_of_current_export(tmp_path):
    rows = [{"sample_id": "a", "split": "test", "has_observed_water": 1, "probability": .8, "prediction": 1}]
    write_run(tmp_path, "baseline-good", "baseline", .3, rows)
    write_run(tmp_path, "lstm-good", "lstm", .6, rows)
    write_run(tmp_path, "lstm-v2-rejected", "candidate", .1, rows)
    (tmp_path / "classification-current.json").write_text(json.dumps({
        "baseline": "baseline-good", "lstm": "lstm-good",
    }))

    result = load_classification_artifacts(tmp_path)

    assert result["models"]["lstm"]["artifact_id"] == "lstm-good"
