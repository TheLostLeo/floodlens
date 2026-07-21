"""Read local FloodLens terrain rasters for the web API."""

from pathlib import Path

import numpy as np
import rasterio
from rasterio.warp import transform


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ELEVATION_PATH = PROJECT_ROOT / "data" / "processed" / "phase1_terrain" / "study_area_dem_utm44n.tif"
SLOPE_PATH = PROJECT_ROOT / "data" / "processed" / "phase1_terrain" / "slope_degrees.tif"


def _sample_raster(path: Path, longitude: float, latitude: float) -> float | None:
    """Return a valid raster value at a WGS84 coordinate, or None if unavailable."""
    if not path.exists():
        return None

    with rasterio.open(path) as dataset:
        x, y = transform("EPSG:4326", dataset.crs, [longitude], [latitude])
        projected_x, projected_y = x[0], y[0]

        if not (
            dataset.bounds.left <= projected_x <= dataset.bounds.right
            and dataset.bounds.bottom <= projected_y <= dataset.bounds.top
        ):
            return None

        value = float(next(dataset.sample([(projected_x, projected_y)]))[0])
        if dataset.nodata is not None and np.isclose(value, dataset.nodata):
            return None
        if not np.isfinite(value):
            return None
        return value


def terrain_at_point(longitude: float, latitude: float) -> dict:
    """Return local terrain values and a cautious drainage interpretation."""
    elevation = _sample_raster(ELEVATION_PATH, longitude, latitude)
    slope = _sample_raster(SLOPE_PATH, longitude, latitude)

    if elevation is None or slope is None:
        return {
            "data_available": False,
            "message": "This point is outside the DEM tiles currently available on this computer.",
        }

    tendency = "high" if slope < 1 else "moderate" if slope < 3 else "low"

    return {
        "data_available": True,
        "elevation_m": round(elevation, 2),
        "slope_degrees": round(slope, 2),
        "water_collection_tendency": tendency,
        "message": "Terrain-only indicator based on local slope. It is not a flood forecast and does not yet use rainfall, rivers, drains, or flow accumulation.",
    }
