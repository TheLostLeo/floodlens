#!/usr/bin/env python3
"""Fetch small, reproducible CHIRPS rainfall sequences for labelled events."""

from __future__ import annotations

import argparse
import csv
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio

RESEARCH_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RESEARCH_DIR / "src"))

from floodlens_research.events import antecedent_dates, load_event_metadata
from floodlens_research.paths import research_data_root

CHIRPS_COG = "https://data.chc.ucsb.edu/products/CHIRPS-2.0/global_daily/cogs/p05"


def chirps_url(day: object) -> str:
    return f"{CHIRPS_COG}/{day:%Y}/chirps-v2.0.{day:%Y.%m.%d}.cog"


def fetch_event(event: dict[str, object], days: int, timeout: int) -> tuple[list[dict[str, object]], dict[str, object] | None]:
    try:
        start, end = antecedent_dates(str(event["event_date"]), days)
        records: list[dict[str, object]] = []
        with rasterio.Env(
            GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR",
            CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".cog",
            GDAL_HTTP_TIMEOUT=str(timeout),
        ):
            current = start
            while current <= end:
                source_url = chirps_url(current)
                with rasterio.open(f"/vsicurl/{source_url}") as dataset:
                    value = next(dataset.sample([(float(event["longitude"]), float(event["latitude"]))], masked=True))[0]
                if np.ma.is_masked(value) or not np.isfinite(float(value)) or float(value) < 0:
                    raise ValueError(f"invalid precipitation at {current.isoformat()}")
                records.append({
                    "event_id": str(event["event_id"]),
                    "event_name": str(event["event_name"]),
                    "event_date": str(event["event_date"]),
                    "date": current.isoformat(),
                    "precip_mm": float(value),
                    "source_url": source_url,
                })
                current += timedelta(days=1)
        return records, None
    except Exception as error:  # record provider/data failure instead of inventing rainfall
        return [], {"event_id": str(event["event_id"]), "event_name": str(event["event_name"]), "error": str(error)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=60)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--data-root", type=Path, default=research_data_root())
    args = parser.parse_args()

    metadata = args.data_root / "sen1floods11" / "v1.1" / "Sen1Floods11_Metadata.geojson"
    output_dir = args.data_root / "chirps"
    output_dir.mkdir(parents=True, exist_ok=True)
    events = load_event_metadata(metadata)
    records: list[dict[str, object]] = []
    errors: list[dict[str, object]] = []
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        futures = [pool.submit(fetch_event, event, args.days, args.timeout) for event in events]
        for future in as_completed(futures):
            rows, error = future.result()
            records.extend(rows)
            if error:
                errors.append(error)

    records.sort(key=lambda row: (str(row["event_id"]), str(row["date"])))
    with (output_dir / "chirps_event_sequences.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["event_id", "event_name", "event_date", "date", "precip_mm", "source_url"])
        writer.writeheader()
        writer.writerows(records)
    with (output_dir / "chirps_download_errors.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["event_id", "event_name", "error"])
        writer.writeheader()
        writer.writerows(sorted(errors, key=lambda row: str(row["event_id"])))
    print(f"Saved {len(records)} daily rainfall records; {len(errors)} events failed or were incomplete.")


if __name__ == "__main__":
    main()
