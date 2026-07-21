from pathlib import Path

import rasterio
from whitebox import WhiteboxTools


def fill_dem_sinks(source_path, output_path):
    """
    Fill artificial depressions in a projected DEM.

    This prepares the DEM for flow-direction and flow-accumulation analysis.
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
                "Sink filling requires a projected DEM with metre-based coordinates."
            )

    wbt = WhiteboxTools()
    wbt.set_verbose_mode(True)

    def _log(message):
        print(f"[fill_depressions] {message}")

    result = wbt.fill_depressions(
        dem=str(source_path),
        output=str(output_path),
        fix_flats=True,
        callback=_log,
    )

    if result != 0 or not output_path.exists():
        raise RuntimeError("WhiteboxTools could not create the filled DEM.")

    return output_path