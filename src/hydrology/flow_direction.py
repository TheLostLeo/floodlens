from pathlib import Path

import rasterio
from whitebox import WhiteboxTools


def calculate_flow_direction(source_path, output_path):
    """
    Calculate D8 flow direction from a hydrologically-corrected DEM.

    Each pixel receives a pointer value indicating which of its eight
    neighbours water would flow into next. This step must run on a DEM
    that has already had its depressions filled or breached, otherwise
    flow paths can dead-end in artificial pits.
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
                "Flow direction requires a projected DEM with metre-based coordinates."
            )

    wbt = WhiteboxTools()
    wbt.set_verbose_mode(False)

    result = wbt.d8_pointer(
        dem=str(source_path),
        output=str(output_path),
        esri_pntr=False,
    )

    if result != 0 or not output_path.exists():
        raise RuntimeError("WhiteboxTools could not create the flow-direction raster.")

    return output_path
