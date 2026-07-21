from pathlib import Path

import rasterio
from whitebox import WhiteboxTools


def breach_dem_depressions(source_path, output_path, search_distance=100):
    """
    Create narrow drainage paths through artificial DEM depressions.

    Uses WhiteboxTools' least-cost breaching algorithm, the tool's
    recommended replacement for the legacy `breach_depressions` method
    (which can produce severe, physically impossible artifacts near
    depressions that touch the raster edge, e.g. a coastline). Any
    depression that cannot be resolved within `search_distance` cells
    is filled instead, so the output is always fully drainable.

    This is a conservative alternative to raising broad areas with
    unconstrained sink filling.
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
                "Depression breaching requires metre-based projected coordinates."
            )

    wbt = WhiteboxTools()
    wbt.set_verbose_mode(True)

    def _log(message):
        print(f"[breach_depressions] {message}")

    result = wbt.breach_depressions_least_cost(
        dem=str(source_path),
        output=str(output_path),
        dist=search_distance,
        fill=True,
        callback=_log,
    )

    if result != 0 or not output_path.exists():
        raise RuntimeError("WhiteboxTools could not create the breached DEM.")

    return output_path