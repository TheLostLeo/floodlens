from __future__ import annotations

from typing import Any

import numpy as np
from sklearn.metrics import average_precision_score, confusion_matrix, f1_score, precision_score, recall_score, roc_auc_score


def select_f1_threshold(y_true: np.ndarray, probability: np.ndarray) -> tuple[float, dict[str, Any]]:
    """Choose a threshold using validation data only, never held-out test data."""
    candidates = np.round(np.arange(0.05, 0.96, 0.01), 2)
    scored = [(binary_metrics(y_true, probability, float(threshold)), float(threshold)) for threshold in candidates]
    best_metrics, best_threshold = max(
        scored,
        key=lambda item: (item[0]["f1"], item[0]["precision"], item[1]),
    )
    return best_threshold, best_metrics


def binary_metrics(y_true: np.ndarray, probability: np.ndarray, threshold: float = 0.5) -> dict[str, Any]:
    y_true = np.asarray(y_true, dtype=int)
    probability = np.asarray(probability, dtype=float)
    if len(y_true) == 0:
        raise ValueError("Cannot score an empty test set")
    prediction = (probability >= threshold).astype(int)
    output: dict[str, Any] = {
        "threshold": threshold,
        "samples": int(len(y_true)),
        "positive_samples": int(y_true.sum()),
        "f1": float(f1_score(y_true, prediction, zero_division=0)),
        "precision": float(precision_score(y_true, prediction, zero_division=0)),
        "recall": float(recall_score(y_true, prediction, zero_division=0)),
        "confusion_matrix": confusion_matrix(y_true, prediction, labels=[0, 1]).tolist(),
    }
    if len(np.unique(y_true)) == 2:
        output["pr_auc"] = float(average_precision_score(y_true, probability))
        output["roc_auc"] = float(roc_auc_score(y_true, probability))
    else:
        output["pr_auc"] = None
        output["roc_auc"] = None
    return output
