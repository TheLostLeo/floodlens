import numpy as np

from floodlens_research.metrics import select_f1_threshold
from floodlens_research.splits import event_split


def test_event_split_is_disjoint_and_deterministic():
    first = event_split(["a", "b", "c", "d", "e"], seed=42, test_events=1, validation_events=1)
    second = event_split(["e", "d", "c", "b", "a"], seed=42, test_events=1, validation_events=1)
    assert first == second
    assert set(first.values()) == {"train", "validation", "test"}


def test_threshold_selection_uses_best_validation_f1():
    threshold, metrics = select_f1_threshold(
        np.array([0, 0, 1, 1]), np.array([0.10, 0.40, 0.60, 0.90])
    )
    assert 0.40 < threshold <= 0.60
    assert metrics["f1"] == 1.0
