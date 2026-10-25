from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path
from typing import Any


def flatten_positions(value: Any) -> list[tuple[float, float]]:
    if isinstance(value, (list, tuple)) and len(value) == 2 and all(isinstance(item, (int, float)) for item in value):
        return [(float(value[0]), float(value[1]))]
    if isinstance(value, (list, tuple)):
        output: list[tuple[float, float]] = []
        for child in value:
            output.extend(flatten_positions(child))
        return output
    return []


def load_event_metadata(metadata_path: Path) -> list[dict[str, object]]:
    content = json.loads(metadata_path.read_text())
    events: list[dict[str, object]] = []
    for feature in content.get("features", []):
        properties = feature.get("properties", {})
        positions = flatten_positions(feature.get("geometry", {}).get("coordinates", []))
        if not positions or not properties.get("location") or not properties.get("s1_date"):
            continue
        longitudes, latitudes = zip(*positions)
        event_date = str(properties["s1_date"]).replace("/", "-")
        events.append({
            "event_id": str(properties.get("ID", properties["location"])),
            "event_name": str(properties["location"]),
            "event_date": event_date,
            "longitude": (min(longitudes) + max(longitudes)) / 2,
            "latitude": (min(latitudes) + max(latitudes)) / 2,
        })
    if not events:
        raise ValueError(f"No usable event records found in {metadata_path}")
    return events


def antecedent_dates(event_date: str, days: int) -> tuple[date, date]:
    if days < 1:
        raise ValueError("days must be at least 1")
    end = date.fromisoformat(event_date)
    return end - timedelta(days=days - 1), end
