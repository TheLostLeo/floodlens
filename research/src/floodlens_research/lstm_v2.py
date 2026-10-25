"""Feature and weighting utilities for the event-balanced rainfall LSTM."""

from __future__ import annotations

import numpy as np


def rainfall_features(rainfall: np.ndarray) -> tuple[np.ndarray, list[str]]:
    rainfall = np.asarray(rainfall, dtype=np.float32)
    if rainfall.ndim != 2 or rainfall.shape[1] < 60:
        raise ValueError("Expected a two-dimensional rainfall array with at least 60 days")
    windows = (1, 3, 7, 14, 30, 60)
    names = [f"rain_{days}d_mm" for days in windows]
    values = [rainfall[:, -days:].sum(axis=1) for days in windows]

    rolling_three = np.stack([
        rainfall[:, start : start + 3].sum(axis=1)
        for start in range(rainfall.shape[1] - 2)
    ], axis=1)
    names += ["max_1d_mm", "max_3d_mm", "wet_days_7", "wet_days_30", "wet_days_60", "days_since_peak"]
    values += [
        rainfall.max(axis=1),
        rolling_three.max(axis=1),
        (rainfall[:, -7:] > 0).sum(axis=1),
        (rainfall[:, -30:] > 0).sum(axis=1),
        (rainfall[:, -60:] > 0).sum(axis=1),
        rainfall.shape[1] - 1 - rainfall.argmax(axis=1),
    ]
    return np.stack(values, axis=1).astype(np.float32), names


def event_balanced_weights(event_ids: np.ndarray) -> np.ndarray:
    event_ids = np.asarray(event_ids).astype(str)
    unique, counts = np.unique(event_ids, return_counts=True)
    lookup = {event: 1.0 / count for event, count in zip(unique, counts)}
    weights = np.asarray([lookup[event] for event in event_ids], dtype=np.float32)
    return weights / weights.mean()
