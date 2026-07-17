from pathlib import Path

import numpy as np
import rasterio


def read_dem_metadata(dem_path: str | Path) -> dict:
    """
    Read and validate metadata from a single-band DEM GeoTIFF.
    """

    path = Path(dem_path)

    if not path.exists():
        raise FileNotFoundError(f"DEM file was not found: {path}")

    if not path.is_file():
        raise ValueError(f"DEM path is not a file: {path}")

    with rasterio.open(path) as dataset:
        if dataset.count != 1:
            raise ValueError(
                f"Expected a single-band DEM, but found {dataset.count} bands."
            )

        if dataset.crs is None:
            raise ValueError("DEM has no coordinate reference system (CRS).")

        elevation = dataset.read(1, masked=True)

        valid_pixel_count = int(np.ma.count(elevation))

        if valid_pixel_count == 0:
            raise ValueError("DEM contains no valid elevation values.")

        bounds = dataset.bounds
        transform = dataset.transform

        metadata = {
            "path": str(path),
            "crs": str(dataset.crs),
            "width": int(dataset.width),
            "height": int(dataset.height),
            "band_count": int(dataset.count),
            "bounds": {
                "left": float(bounds.left),
                "bottom": float(bounds.bottom),
                "right": float(bounds.right),
                "top": float(bounds.top),
            },
            "pixel_width": float(transform.a),
            "pixel_height": float(transform.e),
            "nodata_value": dataset.nodata,
            "data_type": dataset.dtypes[0],
            "minimum_elevation": float(elevation.min()),
            "maximum_elevation": float(elevation.max()),
            "mean_elevation": float(elevation.mean()),
            "valid_pixel_count": valid_pixel_count,
        }

    return metadata