#!/usr/bin/env python3
"""Train full-resolution tiled research models with validation checkpoints."""

from __future__ import annotations

import argparse
import copy
import csv
import json
import random
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "research" / "src"))

from floodlens_research.segmentation import (
    add_counts,
    confusion,
    load_split,
    masked_bce_dice_loss,
    pixel_features,
    portable_path,
    read_chip,
    scores,
    select_threshold,
    tile_windows,
    validate_assignments,
)
from floodlens_research.segmentation_model import FloodUNet


def load_rows() -> list[dict[str, str]]:
    with (ROOT / "data/research/derived/manifest.csv").open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    assignments = load_split(ROOT / "data/research/derived/event_split.json")
    rows = [row for row in rows if str(row["event_id"]) in assignments]
    validate_assignments(rows, assignments)
    for row in rows:
        row["split"] = assignments[str(row["event_id"])]
        row["s1_path"] = str(portable_path(row["s1_path"], ROOT))
        row["label_path"] = str(portable_path(row["label_path"], ROOT))
    return rows


def load_native(row: dict[str, str]) -> tuple[np.ndarray, np.ndarray]:
    return read_chip(Path(row["s1_path"]), Path(row["label_path"]), 512)


def compute_normalizer(rows: list[dict[str, str]]) -> tuple[np.ndarray, np.ndarray]:
    count = 0
    total = np.zeros(2, dtype=np.float64)
    squared = np.zeros(2, dtype=np.float64)
    for row in rows:
        if row["split"] != "train":
            continue
        image, label = load_native(row)
        valid = label >= 0
        pixels = image[:, valid]
        count += pixels.shape[1]
        total += pixels.sum(axis=1, dtype=np.float64)
        squared += np.square(pixels, dtype=np.float64).sum(axis=1)
    mean = total / count
    variance = np.maximum(squared / count - np.square(mean), 1e-10)
    return mean.astype(np.float32), np.sqrt(variance).astype(np.float32)


def crop(image: np.ndarray, label: np.ndarray, top: int, left: int, size: int):
    return image[:, top : top + size, left : left + size], label[top : top + size, left : left + size]


def random_crop(image: np.ndarray, label: np.ndarray, size: int, rng: np.random.Generator):
    max_top = label.shape[0] - size
    max_left = label.shape[1] - size
    best = None
    for _ in range(8):
        top = int(rng.integers(0, max_top + 1))
        left = int(rng.integers(0, max_left + 1))
        candidate = crop(image, label, top, left, size)
        best = candidate
        if np.mean(candidate[1] >= 0) >= 0.5:
            break
    return best


def augment(image: np.ndarray, label: np.ndarray, rng: np.random.Generator):
    turns = int(rng.integers(0, 4))
    image = np.rot90(image, turns, axes=(1, 2)).copy()
    label = np.rot90(label, turns).copy()
    if rng.random() < 0.5:
        image = image[:, :, ::-1].copy()
        label = label[:, ::-1].copy()
    if rng.random() < 0.5:
        image = image[:, ::-1, :].copy()
        label = label[::-1, :].copy()
    return image, label


def tensors(items, mean, std, device):
    import torch

    images = np.stack([item[0] for item in items]).astype(np.float32)
    labels = np.stack([item[1] for item in items])
    images = (images - mean[None, :, None, None]) / std[None, :, None, None]
    return (
        torch.from_numpy(images).to(device),
        torch.from_numpy((labels == 1).astype(np.float32)[:, None]).to(device),
        torch.from_numpy((labels >= 0).astype(np.float32)[:, None]).to(device),
    )


def train_epoch(model, rows, optimizer, mean, std, tile_size, batch_size, rng, device):
    model.train()
    shuffled = list(rows)
    rng.shuffle(shuffled)
    batch = []
    losses = []
    for row in shuffled:
        image, label = load_native(row)
        patch = random_crop(image, label, tile_size, rng)
        batch.append(augment(*patch, rng))
        if len(batch) < batch_size:
            continue
        x, y, valid = tensors(batch, mean, std, device)
        optimizer.zero_grad()
        loss = masked_bce_dice_loss(model(x), y, valid)
        loss.backward()
        optimizer.step()
        losses.append(float(loss.detach().cpu()))
        batch.clear()
    if batch:
        x, y, valid = tensors(batch, mean, std, device)
        optimizer.zero_grad()
        loss = masked_bce_dice_loss(model(x), y, valid)
        loss.backward()
        optimizer.step()
        losses.append(float(loss.detach().cpu()))
    return float(np.mean(losses))


def validation_crops(rows, tile_size):
    result = []
    offset = (512 - tile_size) // 2
    for row in rows:
        image, label = load_native(row)
        result.append((row, *crop(image, label, offset, offset, tile_size)))
    return result


def predict_crops(model, items, mean, std, batch_size, device):
    import torch

    probabilities = []
    model.eval()
    with torch.no_grad():
        for start in range(0, len(items), batch_size):
            batch = items[start : start + batch_size]
            x, _, _ = tensors([(item[1], item[2]) for item in batch], mean, std, device)
            values = torch.sigmoid(model(x))[:, 0].cpu().numpy()
            probabilities.extend(values.astype(np.float32))
    return probabilities


def tiled_predict(model, image, mean, std, tile_size, overlap, batch_size, device):
    import torch

    windows = tile_windows(image.shape[1], image.shape[2], tile_size, overlap)
    total = np.zeros(image.shape[1:], dtype=np.float32)
    count = np.zeros(image.shape[1:], dtype=np.float32)
    model.eval()
    with torch.no_grad():
        for start in range(0, len(windows), batch_size):
            group = windows[start : start + batch_size]
            patches = [image[:, top:bottom, left:right] for top, left, bottom, right in group]
            fake_labels = [np.zeros((tile_size, tile_size), dtype=np.int16) for _ in group]
            x, _, _ = tensors(list(zip(patches, fake_labels)), mean, std, device)
            predictions = torch.sigmoid(model(x))[:, 0].cpu().numpy()
            for probability, (top, left, bottom, right) in zip(predictions, group):
                total[top:bottom, left:right] += probability
                count[top:bottom, left:right] += 1
    return total / np.maximum(count, 1)


def tree_training_data(rows, max_pixels, seed):
    rng = np.random.default_rng(seed)
    train_rows = [row for row in rows if row["split"] == "train"]
    per_chip = max(100, max_pixels // len(train_rows))
    features, targets = [], []
    for row in train_rows:
        image, label = load_native(row)
        x = pixel_features(image).reshape(-1, 5)
        y = label.ravel()
        valid = np.flatnonzero(y >= 0)
        chosen = rng.choice(valid, min(per_chip, len(valid)), replace=False)
        features.append(x[chosen])
        targets.append(y[chosen])
    return np.concatenate(features), np.concatenate(targets)


def tree_predict(model, image):
    features = pixel_features(image).reshape(-1, 5)
    return model.predict_proba(features)[:, 1].reshape(image.shape[1:]).astype(np.float32)


def summarize_test(rows, truths, probabilities, threshold):
    chips = []
    by_event: dict[str, list[dict[str, int]]] = {}
    for row, truth, probability in zip(rows, truths, probabilities):
        counts = confusion(truth, probability >= threshold)
        chips.append({"sample_id": row["sample_id"], "event_id": row["event_id"], "event_name": row["event_name"], **counts, **scores(counts)})
        by_event.setdefault(row["event_name"], []).append(counts)
    aggregate = add_counts(confusion(y, p >= threshold) for y, p in zip(truths, probabilities))
    events = []
    for event_name, items in by_event.items():
        counts = add_counts(items)
        events.append({"event_name": event_name, **counts, **scores(counts)})
    return chips, events, {**aggregate, **scores(aggregate)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--epochs", type=int, default=12)
    parser.add_argument("--patience", type=int, default=3)
    parser.add_argument("--tile-size", type=int, default=128)
    parser.add_argument("--overlap", type=int, default=32)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max-tree-pixels", type=int, default=160_000)
    args = parser.parse_args()

    import joblib
    import torch
    from sklearn.ensemble import ExtraTreesClassifier

    started = time.time()
    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    device = torch.device("cpu")
    rows = load_rows()
    train_rows = [row for row in rows if row["split"] == "train"]
    validation_rows = [row for row in rows if row["split"] == "validation"]
    test_rows = [row for row in rows if row["split"] == "test"]
    mean, std = compute_normalizer(rows)
    fixed_validation = validation_crops(validation_rows, args.tile_size)

    model = FloodUNet(base_channels=8).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-4)
    rng = np.random.default_rng(args.seed)
    history = []
    best_iou = float("-inf")
    best_epoch = 0
    best_state = None
    stale_epochs = 0
    for epoch in range(1, args.epochs + 1):
        loss = train_epoch(model, train_rows, optimizer, mean, std, args.tile_size, args.batch_size, rng, device)
        probabilities = predict_crops(model, fixed_validation, mean, std, args.batch_size, device)
        counts = add_counts(confusion(item[2], probability >= 0.5) for item, probability in zip(fixed_validation, probabilities))
        validation_scores = scores(counts)
        value = -1.0 if validation_scores["iou"] is None else validation_scores["iou"]
        history.append({"epoch": epoch, "train_loss": loss, "validation_iou_at_0_5": validation_scores["iou"], "validation_f1_at_0_5": validation_scores["f1"]})
        print(f"epoch={epoch} loss={loss:.4f} validation_iou={value:.4f}", flush=True)
        if value > best_iou:
            best_iou = value
            best_epoch = epoch
            best_state = copy.deepcopy(model.state_dict())
            stale_epochs = 0
        else:
            stale_epochs += 1
            if stale_epochs >= args.patience:
                break
    model.load_state_dict(best_state)

    validation_probabilities = predict_crops(model, fixed_validation, mean, std, args.batch_size, device)
    validation_truths = [item[2] for item in fixed_validation]
    unet_threshold = select_threshold(validation_truths, validation_probabilities)

    tree_x, tree_y = tree_training_data(rows, args.max_tree_pixels, args.seed)
    tree = ExtraTreesClassifier(n_estimators=100, max_depth=24, min_samples_leaf=3, n_jobs=-1, random_state=args.seed, class_weight="balanced")
    tree.fit(tree_x, tree_y)
    tree_validation = [tree_predict(tree, item[1]) for item in fixed_validation]
    tree_threshold = select_threshold(validation_truths, tree_validation)

    test_truths = []
    unet_test = []
    tree_test = []
    for index, row in enumerate(test_rows, start=1):
        image, label = load_native(row)
        test_truths.append(label)
        unet_test.append(tiled_predict(model, image, mean, std, args.tile_size, args.overlap, args.batch_size, device).astype(np.float32))
        tree_test.append(tree_predict(tree, image))
        print(f"test_inference={index}/{len(test_rows)} sample={row['sample_id']}", flush=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    artifact_id = f"segmentation-v2-{timestamp}"
    output = ROOT / "research" / "artifacts" / artifact_id
    output.mkdir(parents=True, exist_ok=False)
    torch.save(model.state_dict(), output / "unet.pt")
    joblib.dump(tree, output / "extra_trees.joblib")
    np.savez_compressed(
        output / "predictions.npz",
        **{f"tree__{row['sample_id']}": value for row, value in zip(test_rows, tree_test)},
        **{f"unet__{row['sample_id']}": value for row, value in zip(test_rows, unet_test)},
    )
    models = {}
    for name, threshold, predictions in (
        ("extra_trees", tree_threshold, tree_test),
        ("unet", unet_threshold, unet_test),
    ):
        chips, events, test_metrics = summarize_test(test_rows, test_truths, predictions, threshold)
        models[name] = {"threshold": threshold, "test": test_metrics, "events": events, "chips": chips}
    report = {
        "status": "completed",
        "artifact_id": artifact_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "task": "observed-water segmentation research; not forecasting",
        "native_resolution": 512,
        "tile_size": args.tile_size,
        "overlap": args.overlap,
        "seed": args.seed,
        "epochs_requested": args.epochs,
        "epochs_trained": len(history),
        "best_epoch": best_epoch,
        "checkpoint_selection": "highest validation center-crop IoU at threshold 0.5",
        "threshold_selection": "highest validation center-crop F1",
        "normalization": {"mean": mean.tolist(), "std": std.tolist(), "fit_split": "train"},
        "models": models,
        "elapsed_seconds": round(time.time() - started, 2),
    }
    (output / "history.json").write_text(json.dumps(history, indent=2) + "\n")
    (output / "metrics.json").write_text(json.dumps(report, indent=2) + "\n")
    pointer = {"artifact_id": artifact_id, "path": str(output.relative_to(ROOT)).replace("\\", "/")}
    (ROOT / "research/artifacts/segmentation-current.json").write_text(json.dumps(pointer, indent=2) + "\n")
    print(json.dumps({"artifact": str(output), "best_epoch": best_epoch, "models": {key: value["test"] for key, value in models.items()}}, indent=2))


if __name__ == "__main__":
    main()
