import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

from floodlens_research.segmentation import (
    add_counts,
    confusion,
    masked_bce_dice_loss,
    pixel_features,
    scores,
    tile_windows,
    validate_assignments,
    read_chip,
)


def test_confusion_ignores_unknown_and_counts_errors():
    truth = np.array([[1, 0, -1], [1, 0, 1]])
    pred = np.array([[1, 1, 1], [0, 0, 1]])
    counts = confusion(truth, pred)
    assert counts == {"tp": 2, "fp": 1, "fn": 1, "tn": 1}
    assert scores(counts)["iou"] == .5


def test_no_water_scores_are_undefined_not_perfect():
    assert scores(dict(tp=0, fp=0, fn=0, tn=20))["iou"] is None


def test_split_rejects_missing_or_unknown_assignments():
    with pytest.raises(ValueError):
        validate_assignments([{"event_id": "1"}], {"1": "training"})
    with pytest.raises(ValueError):
        validate_assignments([{"event_id": "1"}], {})


def test_features_are_finite_and_preserve_shape():
    image = np.ones((2, 8, 8), dtype=np.float32)
    features = pixel_features(image)
    assert features.shape == (8, 8, 5)
    assert np.isfinite(features).all()


def test_add_counts_accepts_one_shot_generator():
    items = ({"tp": 1, "fp": 2, "fn": 3, "tn": 4} for _ in range(2))
    assert add_counts(items) == {"tp": 2, "fp": 4, "fn": 6, "tn": 8}


def test_tile_windows_cover_full_image_with_overlap_and_edge_alignment():
    windows = tile_windows(height=512, width=512, tile_size=128, overlap=32)
    assert windows[0] == (0, 0, 128, 128)
    assert windows[-1] == (384, 384, 512, 512)
    coverage = np.zeros((512, 512), dtype=np.uint8)
    for top, left, bottom, right in windows:
        coverage[top:bottom, left:right] += 1
    assert coverage.min() >= 1
    assert coverage.max() > 1


def test_masked_bce_dice_loss_ignores_unknown_pixels_and_rewards_overlap():
    torch = pytest.importorskip("torch")
    truth = torch.tensor([[[[1.0, 0.0], [0.0, 0.0]]]])
    valid = torch.tensor([[[[1.0, 1.0], [0.0, 0.0]]]])
    good = torch.tensor([[[[5.0, -5.0], [100.0, -100.0]]]])
    bad = torch.tensor([[[[-5.0, 5.0], [-100.0, 100.0]]]])
    assert masked_bce_dice_loss(good, truth, valid) < masked_bce_dice_loss(bad, truth, valid)


def test_read_chip_excludes_source_nodata_from_label(tmp_path):
    image_path = tmp_path / "image.tif"
    label_path = tmp_path / "label.tif"
    profile = {
        "driver": "GTiff", "height": 4, "width": 4, "crs": "EPSG:4326",
        "transform": from_origin(0, 4, 1, 1), "dtype": "float32", "nodata": -999.0,
    }
    image = np.ones((2, 4, 4), dtype=np.float32)
    image[:, 1, 2] = -999.0
    with rasterio.open(image_path, "w", count=2, **profile) as target:
        target.write(image)
    with rasterio.open(label_path, "w", count=1, **{**profile, "dtype": "int16", "nodata": -1}) as target:
        target.write(np.ones((1, 4, 4), dtype=np.int16))
    _, label = read_chip(image_path, label_path, 4)
    assert label[1, 2] == -1
