#!/usr/bin/env python3
"""Build an auditable chip-level manifest from downloaded Sen1Floods11 files."""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

import numpy as np
import rasterio
from rasterio.warp import transform_bounds

RESEARCH_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RESEARCH_DIR / "src"))

from floodlens_research.events import load_event_metadata
from floodlens_research.paths import research_data_root


def key(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


EVENT_NAME_ALIASES = {
    # The v1.1 hand-labelled filenames use the river-system name while the
    # official metadata calls the same documented event Cambodia (event ID 4).
    "mekong": "cambodia",
}


def companion(path: Path, source_layer: str, target_layer: str) -> Path:
    return path.parent.parent / target_layer / path.name.replace(source_layer, target_layer)


def chip_summary(s1_path: Path, label_path: Path, jrc_path: Path | None, positive_threshold: float) -> dict[str, float | int]:
    with rasterio.open(s1_path) as source, rasterio.open(label_path) as labels:
        sar = source.read(masked=True).astype(np.float64)
        label = labels.read(1, masked=True)
        valid = (~np.ma.getmaskarray(label)) & np.isin(np.asarray(label), [0, 1])
        valid_pixels = int(valid.sum())
        if valid_pixels == 0:
            raise ValueError("no valid 0/1 label pixels")
        vv = np.asarray(sar[0])
        vh = np.asarray(sar[1])
        finite = valid & np.isfinite(vv) & np.isfinite(vh)
        if not finite.any():
            raise ValueError("no finite VV/VH values over valid labels")
        bounds = transform_bounds(source.crs, "EPSG:4326", *source.bounds, densify_pts=21)
        observed_water_fraction = float((np.asarray(label)[valid] == 1).mean())
        jrc_mean: float | None = None
        if jrc_path and jrc_path.is_file():
            with rasterio.open(jrc_path) as jrc_source:
                jrc = jrc_source.read(1, masked=True)
                jrc_valid = valid & ~np.ma.getmaskarray(jrc)
                if jrc_valid.any():
                    jrc_mean = float(np.asarray(jrc)[jrc_valid].mean())
        return {
            "valid_pixels": valid_pixels,
            "observed_water_fraction": observed_water_fraction,
            "has_observed_water": int(observed_water_fraction >= positive_threshold),
            "vv_mean_db": float(vv[finite].mean()),
            "vh_mean_db": float(vh[finite].mean()),
            "longitude": (bounds[0] + bounds[2]) / 2,
            "latitude": (bounds[1] + bounds[3]) / 2,
            "jrc_water_mean": jrc_mean,
        }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path, default=research_data_root())
    parser.add_argument("--positive-threshold", type=float, default=0.05)
    args = parser.parse_args()
    if not 0 < args.positive_threshold <= 1:
        raise SystemExit("--positive-threshold must be in (0, 1]")

    dataset = args.data_root / "sen1floods11" / "v1.1"
    s1_dir = dataset / "data/flood_events/HandLabeled/S1Hand"
    metadata_path = dataset / "Sen1Floods11_Metadata.geojson"
    output = args.data_root / "derived"
    output.mkdir(parents=True, exist_ok=True)
    metadata = {key(str(event["event_name"])): event for event in load_event_metadata(metadata_path)}

    rows: list[dict[str, object]] = []
    skipped: list[dict[str, str]] = []
    for s1_path in sorted(s1_dir.rglob("*_S1Hand.tif")):
        label_path = companion(s1_path, "S1Hand", "LabelHand")
        jrc_path = companion(s1_path, "S1Hand", "JRCWaterHand")
        filename_event_name = s1_path.name.split("_", 1)[0]
        event_name = EVENT_NAME_ALIASES.get(key(filename_event_name), key(filename_event_name))
        event = metadata.get(event_name)
        try:
            if event is None:
                raise ValueError(f"no metadata record matched filename event {filename_event_name}")
            if not label_path.is_file():
                raise ValueError(f"missing paired label: {label_path.name}")
            summary = chip_summary(s1_path, label_path, jrc_path, args.positive_threshold)
            rows.append({
                "sample_id": s1_path.stem.removesuffix("_S1Hand"),
                "event_id": event["event_id"],
                "event_name": event["event_name"],
                "event_date": event["event_date"],
                "s1_path": str(s1_path.resolve()),
                "label_path": str(label_path.resolve()),
                "jrc_path": str(jrc_path.resolve()) if jrc_path.is_file() else "",
                **summary,
            })
        except Exception as error:
            skipped.append({"s1_path": str(s1_path), "reason": str(error)})

    if not rows:
        raise SystemExit(f"No usable paired chips found below {s1_dir}")
    rows.sort(key=lambda row: str(row["sample_id"]))
    fieldnames = list(rows[0])
    with (output / "manifest.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    with (output / "manifest_skipped.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["s1_path", "reason"])
        writer.writeheader()
        writer.writerows(skipped)
    (output / "manifest_metadata.json").write_text(json.dumps({
        "dataset": "Sen1Floods11 v1.1 hand-labelled subset",
        "target": "observed water/no-water during documented flood events",
        "positive_threshold": args.positive_threshold,
        "chips": len(rows),
        "skipped": len(skipped),
        "warning": "JRC values are retained for audit only; do not claim temporary-flood labels until their semantics are verified.",
    }, indent=2) + "\n")
    print(f"Saved {len(rows)} usable chips; skipped {len(skipped)}. Manifest: {output / 'manifest.csv'}")


if __name__ == "__main__":
    main()
