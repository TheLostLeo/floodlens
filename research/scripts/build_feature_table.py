#!/usr/bin/env python3
"""Join checked rainfall sequences to chip labels without filling missing data."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

RESEARCH_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RESEARCH_DIR / "src"))

from floodlens_research.paths import research_data_root


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path, default=research_data_root())
    parser.add_argument("--days", type=int, default=60)
    args = parser.parse_args()
    if args.days < 7:
        raise SystemExit("--days must be at least 7")

    derived = args.data_root / "derived"
    manifest = pd.read_csv(derived / "manifest.csv", dtype={"event_id": str})
    split_payload = json.loads((derived / "event_split.json").read_text())
    rainfall_path = args.data_root / "chirps" / "chirps_event_sequences.csv"
    rainfall = pd.read_csv(rainfall_path, dtype={"event_id": str}, parse_dates=["date"])
    expected = args.days
    sequences: dict[str, np.ndarray] = {}
    excluded: list[dict[str, str]] = []
    for event_id, group in rainfall.groupby("event_id"):
        ordered = group.sort_values("date")
        values = ordered["precip_mm"].to_numpy(dtype=float)
        if len(values) != expected or not np.isfinite(values).all() or (values < 0).any():
            excluded.append({"event_id": str(event_id), "reason": f"requires {expected} finite non-negative daily values; got {len(values)}"})
            continue
        sequences[str(event_id)] = values

    assignments = {str(key): value for key, value in split_payload["assignments"].items()}
    rows: list[dict[str, object]] = []
    sequences_by_sample: dict[str, np.ndarray] = {}
    for row in manifest.to_dict(orient="records"):
        event_id = str(row["event_id"])
        sequence = sequences.get(event_id)
        if sequence is None:
            continue
        rows.append({
            **row,
            "split": assignments[event_id],
            "rain_1d_mm": float(sequence[-1:].sum()),
            "rain_3d_mm": float(sequence[-3:].sum()),
            "rain_7d_mm": float(sequence[-7:].sum()),
            "rain_14d_mm": float(sequence[-14:].sum()),
            "rain_30d_mm": float(sequence[-30:].sum()),
            "rain_60d_mm": float(sequence.sum()),
        })
        sequences_by_sample[str(row["sample_id"])] = sequence
    if not rows:
        raise SystemExit("No manifest rows had complete CHIRPS sequences. Inspect chirps_download_errors.csv.")

    table = pd.DataFrame(rows).sort_values("sample_id").reset_index(drop=True)
    sequences_array = np.asarray(
        [sequences_by_sample[str(sample_id)] for sample_id in table["sample_id"]],
        dtype=np.float32,
    )
    table.to_csv(derived / "model_table.csv", index=False)
    np.savez_compressed(
        derived / "rainfall_sequences.npz",
        sample_id=table["sample_id"].astype(str).to_numpy(dtype=str),
        rainfall_mm=sequences_array,
    )
    used_event_ids = sorted(table["event_id"].astype(str).unique())
    manifest_event_ids = sorted(manifest["event_id"].astype(str).unique())
    reported_excluded = excluded + [
        {
            "event_id": event_id,
            "reason": "no complete downloaded CHIRPS sequence for this manifest event",
        }
        for event_id in manifest_event_ids
        if event_id not in sequences
    ]
    report = {
        "sequence_days": args.days,
        "usable_events": used_event_ids,
        "excluded_events": reported_excluded,
        "usable_chips": int(len(table)),
        "chips_by_split": {split: int(count) for split, count in table["split"].value_counts().items()},
        "events_by_split": {split: int(count) for split, count in table.groupby("split")["event_id"].nunique().items()},
        "target": "has_observed_water based on the label-water fraction threshold in manifest_metadata.json",
    }
    (derived / "feature_report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
