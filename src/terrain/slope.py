from pathlib import Path

import numpy as np
import rasterio


def calculate_slope_degrees(source_path, output_path):
    """
    Calculate slope in degrees from a projected DEM.

    The input DEM must use metre-based coordinates,
    for example EPSG:32644.
    """

    source_path = Path(source_path)
    output_path = Path(output_path)

    if not source_path.exists():
        raise FileNotFoundError(f"DEM file was not found: {source_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with rasterio.open(source_path) as src:
        if src.count != 1:
            raise ValueError(
                f"Expected one DEM band, but found {src.count} bands."
            )

        if src.crs is None:
            raise ValueError("DEM has no CRS.")

        if src.crs.is_geographic:
            raise ValueError(
                "Slope requires a projected DEM with metre-based coordinates."
            )

        pixel_width = abs(src.transform.a)
        pixel_height = abs(src.transform.e)

        if pixel_width == 0 or pixel_height == 0:
            raise ValueError("DEM has invalid pixel dimensions.")

        nodata_value = src.nodata

        if nodata_value is None:
            nodata_value = -9999.0

        dem = src.read(1, masked=True).astype(np.float32)

        # Convert NoData cells to NaN before calculations.
        elevation = dem.filled(np.nan)

        # Calculate elevation change per metre in both directions.
        gradient_y, gradient_x = np.gradient(
            elevation,
            pixel_height,
            pixel_width,
        )

        # Convert terrain gradient to slope angle in degrees.
        slope_radians = np.arctan(
            np.sqrt(gradient_x ** 2 + gradient_y ** 2)
        )

        slope_degrees = np.degrees(slope_radians)

        # Valid terrain slope must be between 0 and 90 degrees.
        slope_degrees = np.clip(slope_degrees, 0, 90)

        # Keep NoData areas as NoData in the final slope raster.
        slope_degrees[~np.isfinite(slope_degrees)] = nodata_value

        output_profile = src.profile.copy()
        output_profile.update(
            dtype="float32",
            count=1,
            nodata=float(nodata_value),
            compress="lzw",
        )

        with rasterio.open(output_path, "w", **output_profile) as dst:
            dst.write(slope_degrees.astype(np.float32), 1)
            dst.set_band_description(1, "Slope in degrees")

    return output_path