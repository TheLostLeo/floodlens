from __future__ import annotations

import random
from collections.abc import Iterable


def event_split(event_ids: Iterable[str], *, seed: int, test_events: int, validation_events: int) -> dict[str, str]:
    unique = sorted(set(event_ids))
    minimum = test_events + validation_events + 1
    if len(unique) < minimum:
        raise ValueError(f"Need at least {minimum} independent events; found {len(unique)}")
    if test_events < 1 or validation_events < 1:
        raise ValueError("test_events and validation_events must both be at least 1")
    shuffled = unique[:]
    random.Random(seed).shuffle(shuffled)
    assignments = {event_id: "test" for event_id in shuffled[:test_events]}
    assignments.update({event_id: "validation" for event_id in shuffled[test_events:test_events + validation_events]})
    assignments.update({event_id: "train" for event_id in shuffled[test_events + validation_events:]})
    return assignments
