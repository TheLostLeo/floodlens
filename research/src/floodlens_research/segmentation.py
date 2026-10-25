"""Shared, auditable utilities for the research-only water-mask experiments."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

import numpy as np
import rasterio
from rasterio.enums import Resampling

SPLITS = {"train", "validation", "test"}


def tile_windows(height: int, width: int, tile_size: int, overlap: int) -> list[tuple[int, int, int, int]]:
    """Return edge-aligned overlapping windows that cover an image completely."""
    if tile_size <= 0 or overlap < 0 or overlap >= tile_size:
        raise ValueError("tile_size must be positive and overlap must be in [0, tile_size)")
    if height < tile_size or width < tile_size:
        raise ValueError("image dimensions must be at least tile_size")
    stride = tile_size - overlap
    tops = list(range(0, height - tile_size + 1, stride))
    lefts = list(range(0, width - tile_size + 1, stride))
    if tops[-1] != height - tile_size:
        tops.append(height - tile_size)
    if lefts[-1] != width - tile_size:
        lefts.append(width - tile_size)
    return [(top, left, top + tile_size, left + tile_size) for top in tops for left in lefts]


def masked_bce_dice_loss(logits, truth, valid, positive_weight: float = 2.0):
    """Combine masked pixel classification and region-overlap losses."""
    import torch
    import torch.nn.functional as functional

    weight = torch.tensor([positive_weight], dtype=logits.dtype, device=logits.device)
    bce = functional.binary_cross_entropy_with_logits(
        logits, truth, reduction="none", pos_weight=weight
    )
    masked_bce = (bce * valid).sum() / valid.sum().clamp_min(1)
    probability = torch.sigmoid(logits) * valid
    masked_truth = truth * valid
    intersection = (probability * masked_truth).sum()
    dice = (2 * intersection + 1.0) / (probability.sum() + masked_truth.sum() + 1.0)
    return masked_bce + (1.0 - dice)


def portable_path(value: str, repository_root: Path) -> Path:
    """Resolve manifests written on another OS without silently searching by name."""
    path = Path(value)
    if path.is_file():
        return path
    marker = "/data/research/"
    normal = value.replace("\\", "/")
    if marker in normal:
        candidate = repository_root / "data" / "research" / normal.split(marker, 1)[1]
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(f"Research raster is unavailable: {value}")


def validate_assignments(rows: Iterable[dict[str, object]], assignments: dict[str, str]) -> None:
    for row in rows:
        event_id = str(row["event_id"])
        if event_id not in assignments:
            raise ValueError(f"Event {event_id} has no frozen split assignment")
        if assignments[event_id] not in SPLITS:
            raise ValueError(f"Event {event_id} has unknown split {assignments[event_id]!r}")


def read_chip(s1_path: Path, label_path: Path, size: int) -> tuple[np.ndarray, np.ndarray]:
    with rasterio.open(s1_path) as source, rasterio.open(label_path) as labels:
        if source.crs != labels.crs or not np.allclose(source.bounds, labels.bounds, rtol=0, atol=1e-9):
            raise ValueError(f"Misaligned source and label rasters: {s1_path.name}")
        image = source.read(
            out_shape=(2, size, size), resampling=Resampling.average
        ).astype(np.float32)
        source_valid = source.read_masks(
            out_shape=(2, size, size), resampling=Resampling.nearest
        ).all(axis=0)
        label = labels.read(
            out_shape=(1, size, size), resampling=Resampling.nearest
        )[0].astype(np.int16)
        label_valid = labels.read_masks(
            out_shape=(1, size, size), resampling=Resampling.nearest
        )[0].astype(bool)
    valid = source_valid & label_valid & np.isfinite(image).all(axis=0)
    label[~valid] = -1
    label[~np.isin(label, (0, 1))] = -1
    image[:, ~source_valid] = 0
    return image, label


def pixel_features(image: np.ndarray) -> np.ndarray:
    if image.ndim != 3 or image.shape[0] != 2:
        raise ValueError("Expected a two-band (VV, VH) image")
    _, height, width = image.shape
    yy, xx = np.mgrid[0:height, 0:width]
    x = xx.astype(np.float32) / max(width - 1, 1)
    y = yy.astype(np.float32) / max(height - 1, 1)
    vv, vh = image
    return np.stack((vv, vh, vv - vh, x, y), axis=-1)


def confusion(truth: np.ndarray, prediction: np.ndarray) -> dict[str, int]:
    valid = np.isin(truth, (0, 1))
    actual = truth[valid] == 1
    predicted = prediction[valid] == 1
    return {
        "tp": int(np.sum(actual & predicted)),
        "fp": int(np.sum(~actual & predicted)),
        "fn": int(np.sum(actual & ~predicted)),
        "tn": int(np.sum(~actual & ~predicted)),
    }


def scores(counts: dict[str, int]) -> dict[str, float | None]:
    tp, fp, fn = counts["tp"], counts["fp"], counts["fn"]
    precision = tp / (tp + fp) if tp + fp else None
    recall = tp / (tp + fn) if tp + fn else None
    iou = tp / (tp + fp + fn) if tp + fp + fn else None
    f1 = 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else None
    return {"precision": precision, "recall": recall, "f1": f1, "iou": iou}


def add_counts(items: Iterable[dict[str, int]]) -> dict[str, int]:
    totals = {key: 0 for key in ("tp", "fp", "fn", "tn")}
    for item in items:
        for key in totals:
            totals[key] += item[key]
    return totals


def select_threshold(truths: list[np.ndarray], probabilities: list[np.ndarray]) -> float:
    best = (float("-inf"), 0.5)
    for threshold in np.linspace(0.2, 0.8, 13):
        counts = add_counts(confusion(y, p >= threshold) for y, p in zip(truths, probabilities))
        value = scores(counts)["f1"]
        candidate = (-1.0 if value is None else value, float(threshold))
        if candidate > best:
            best = candidate
    return best[1]


def load_split(path: Path) -> dict[str, str]:
    payload = json.loads(path.read_text())
    return {str(key): str(value) for key, value in payload["assignments"].items()}
