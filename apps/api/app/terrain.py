from __future__ import annotations

import math
from pathlib import Path
from typing import Any

ALGORITHM_VERSION = "terrain-baseline-v1"


class TerrainUnavailable(Exception):
    def __init__(self, message: str, status: str = "unavailable", missing_datasets: list[str] | None = None):
        super().__init__(message)
        self.status = status
        self.missing_datasets = missing_datasets or []


def classify_score(score: float) -> str:
    if score < 0.34:
        return "lower relative terrain susceptibility"
    if score < 0.67:
        return "moderate relative terrain susceptibility"
    return "higher relative terrain susceptibility"


def score_from_metrics(
    point_elevation_m: float,
    p10_elevation_m: float,
    p90_elevation_m: float,
    median_slope_percent: float,
) -> dict[str, Any]:
    relief = max(p90_elevation_m - p10_elevation_m, 0.1)
    low_position = 1.0 - max(0.0, min(1.0, (point_elevation_m - p10_elevation_m) / relief))
    flatness = 1.0 - max(0.0, min(1.0, median_slope_percent / 5.0))
    low_relief = 1.0 - max(0.0, min(1.0, relief / 25.0))
    score = (0.55 * low_position) + (0.25 * flatness) + (0.20 * low_relief)
    return {
        "score": round(score * 100),
        "label": classify_score(score),
        "factors": [
            {
                "name": "relative elevation",
                "score": round(low_position * 100),
                "explanation": "Higher when the selected point sits low compared with nearby bare-earth terrain.",
            },
            {
                "name": "local flatness",
                "score": round(flatness * 100),
                "explanation": "Higher when nearby slopes are gentle enough for water to pond or move slowly.",
            },
            {
                "name": "local relief",
                "score": round(low_relief * 100),
                "explanation": "Higher when the surrounding terrain has little vertical separation.",
            },
        ],
    }


def unavailable_result(message: str, status: str = "unavailable", missing_datasets: list[str] | None = None) -> dict[str, Any]:
    return {
        "status": status,
        "message": message,
        "missing_datasets": missing_datasets or [],
        "limitations": _limitations(),
    }


def evaluate_terrain(
    latitude: float,
    longitude: float,
    radius_km: int,
    terrain_dir: str,
    dataset_version: str,
    resolution_m: float,
) -> dict[str, Any]:
    tiles = _terrain_tiles(Path(terrain_dir))
    if not tiles:
        return unavailable_result(
            "FABDEM GeoTIFF tiles are not mounted. Place matching tiles under data/imports/fabdem and rebuild or restart the worker.",
            missing_datasets=["fabdem"],
        )

    try:
        sample = _sample_tiles(tiles, latitude, longitude, radius_km, resolution_m)
    except TerrainUnavailable as error:
        return unavailable_result(str(error), status=error.status, missing_datasets=error.missing_datasets)

    scored = score_from_metrics(
        sample["point_elevation_m"],
        sample["p10_elevation_m"],
        sample["p90_elevation_m"],
        sample["median_slope_percent"],
    )
    return {
        "status": "available",
        "message": "Local bare-earth terrain susceptibility is available.",
        **scored,
        "metrics": sample,
        "provenance": {
            "dataset": "FABDEM",
            "version": dataset_version,
            "algorithm_version": ALGORITHM_VERSION,
            "resolution_m": resolution_m,
            "tile_count": len(tiles),
            "tiles_used": sample["tiles_used"],
        },
        "quality_flags": sample["quality_flags"],
        "missing_datasets": [],
        "limitations": _limitations(),
    }


def _terrain_tiles(terrain_dir: Path) -> list[Path]:
    if not terrain_dir.exists():
        return []
    return sorted([*terrain_dir.glob("*.tif"), *terrain_dir.glob("*.tiff")])


def _sample_tiles(tiles: list[Path], latitude: float, longitude: float, radius_km: int, resolution_m: float) -> dict[str, Any]:
    import numpy as np
    import rasterio
    from rasterio.errors import RasterioError
    from rasterio.transform import xy
    from rasterio.warp import transform
    from rasterio.windows import from_bounds

    radius_m = radius_km * 1000.0
    lat_delta = radius_km / 111.32
    lon_delta = radius_km / max(111.32 * math.cos(math.radians(latitude)), 1.0)
    values = []
    point_values = []
    slopes = []
    used = []
    quality_flags = []

    for tile in tiles:
        try:
            with rasterio.open(tile) as dataset:
                if dataset.crs is None:
                    quality_flags.append(f"{tile.name}: missing CRS")
                    continue
                transformed_x, transformed_y = transform(
                    "EPSG:4326",
                    dataset.crs,
                    [longitude - lon_delta, longitude + lon_delta],
                    [latitude - lat_delta, latitude + lat_delta],
                )
                window = from_bounds(
                    min(transformed_x),
                    min(transformed_y),
                    max(transformed_x),
                    max(transformed_y),
                    dataset.transform,
                ).round_offsets().round_lengths()
                if window.width <= 0 or window.height <= 0:
                    continue
                data = dataset.read(1, window=window, masked=True)
                if data.size == 0:
                    continue
                rows, cols = np.indices(data.shape)
                xs, ys = xy(dataset.window_transform(window), rows.ravel(), cols.ravel())
                lon_grid, lat_grid = transform(dataset.crs, "EPSG:4326", np.asarray(xs).ravel(), np.asarray(ys).ravel())
                lon_grid = np.asarray(lon_grid).reshape(data.shape)
                lat_grid = np.asarray(lat_grid).reshape(data.shape)
                metres_per_degree_lon = 111_320.0 * math.cos(math.radians(latitude))
                dx = (lon_grid - longitude) * metres_per_degree_lon
                dy = (lat_grid - latitude) * 111_320.0
                inside = (dx * dx + dy * dy) <= (radius_m * radius_m)
                valid = inside & ~np.ma.getmaskarray(data) & np.isfinite(np.asarray(data))
                if not valid.any():
                    continue
                local_values = np.asarray(data)[valid].astype("float64")
                values.append(local_values)
                used.append(tile.name)

                point_x, point_y = transform("EPSG:4326", dataset.crs, [longitude], [latitude])
                point_sample = next(dataset.sample([(point_x[0], point_y[0])], masked=True))[0]
                if not np.ma.is_masked(point_sample) and np.isfinite(float(point_sample)):
                    point_values.append(float(point_sample))

                filled = data.astype("float64").filled(np.nan)
                if min(filled.shape) > 2:
                    gradient_y, gradient_x = np.gradient(filled, resolution_m, resolution_m)
                    slope_percent = np.sqrt((gradient_x ** 2) + (gradient_y ** 2)) * 100.0
                    slopes.append(slope_percent[valid & np.isfinite(slope_percent)])
        except (OSError, RasterioError, TypeError, ValueError) as error:
            quality_flags.append(f"{tile.name}: {error}")

    if not values:
        raise TerrainUnavailable(
            "FABDEM tiles are mounted, but the selected point is outside their coverage.",
            status="outside_coverage",
        )

    all_values = np.concatenate(values)
    slope_values = np.concatenate([item for item in slopes if item.size]) if slopes else np.array([0.0])
    point_elevation = point_values[0] if point_values else float(np.median(all_values))
    p10 = float(np.percentile(all_values, 10))
    p90 = float(np.percentile(all_values, 90))
    valid_cell_count = int(all_values.size)
    expected_cells = max(int(math.pi * (radius_m / max(resolution_m, 1.0)) ** 2), 1)
    coverage_ratio = min(valid_cell_count / expected_cells, 1.0)
    if coverage_ratio < 0.75:
        quality_flags.append("partial terrain coverage inside the selected circle")

    return {
        "point_elevation_m": round(float(point_elevation), 2),
        "min_elevation_m": round(float(np.min(all_values)), 2),
        "mean_elevation_m": round(float(np.mean(all_values)), 2),
        "p10_elevation_m": round(p10, 2),
        "p90_elevation_m": round(p90, 2),
        "local_relief_m": round(max(p90 - p10, 0.0), 2),
        "median_slope_percent": round(float(np.nanmedian(slope_values)), 2),
        "valid_cell_count": valid_cell_count,
        "coverage_ratio": round(coverage_ratio, 2),
        "tiles_used": used,
        "quality_flags": quality_flags,
    }


def _limitations() -> list[str]:
    return [
        "This is relative terrain susceptibility, not a flood probability, depth estimate, or warning.",
        "FABDEM is bare-earth terrain; it does not include drainage capacity, blocked culverts, levees, walls, or sewer surcharge.",
        "The score is deterministic and explainable; it is not a trained ML model or evidence of historic flood performance.",
    ]
