#!/usr/bin/env python3
"""Create deterministic event-held-out splits from the research manifest."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

RESEARCH_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RESEARCH_DIR / "src"))

from floodlens_research.paths import research_data_root
from floodlens_research.splits import event_split


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path, default=research_data_root())
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--test-events", type=int, default=2)
    parser.add_argument("--validation-events", type=int, default=2)
    args = parser.parse_args()

    derived = args.data_root / "derived"
    manifest = pd.read_csv(derived / "manifest.csv")
    rainfall_path = args.data_root / "chirps" / "chirps_event_sequences.csv"
    eligible = manifest
    excluded_events: list[str] = []
    if rainfall_path.is_file():
        rainfall = pd.read_csv(rainfall_path, dtype={"event_id": str})
        complete_events = {
            str(event_id)
            for event_id, group in rainfall.groupby("event_id")
            if len(group) == 60 and group["precip_mm"].notna().all() and (group["precip_mm"] >= 0).all()
        }
        eligible = manifest[manifest["event_id"].astype(str).isin(complete_events)]
        excluded_events = sorted(set(manifest["event_id"].astype(str)) - complete_events)
        if excluded_events:
            print(f"Excluding incomplete-rainfall events from the split: {', '.join(excluded_events)}")
    assignments = event_split(
        eligible["event_id"].astype(str),
        seed=args.seed,
        test_events=args.test_events,
        validation_events=args.validation_events,
    )
    payload = {
        "strategy": "event-held-out",
        "seed": args.seed,
        "test_events": args.test_events,
        "validation_events": args.validation_events,
        "assignments": assignments,
        "excluded_events": excluded_events,
    }
    (derived / "event_split.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    for split in ("train", "validation", "test"):
        events = sorted(event_id for event_id, assigned in assignments.items() if assigned == split)
        chips = int(manifest[manifest["event_id"].astype(str).isin(events)].shape[0])
        print(f"{split}: {len(events)} events, {chips} chips -> {', '.join(events)}")


if __name__ == "__main__":
    main()
