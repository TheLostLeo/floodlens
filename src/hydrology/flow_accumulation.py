from pathlib import Path

import rasterio
from whitebox import WhiteboxTools


VALID_OUT_TYPES = {"cells", "catchment area", "specific contributing area"}


def calculate_flow_accumulation(pointer_path, output_path, out_type="cells"):
    """
    Calculate D8 flow accumulation from an existing D8 flow-direction
    (pointer) raster, as produced by `flow_direction.calculate_flow_direction`.

    Each pixel's value represents how much upslope area drains into it
    (measured in `out_type` units). High values mark natural drainage
    paths and locations where surface runoff is likely to collect.

    Consuming the pointer raster directly (instead of the DEM) avoids
    recomputing D8 flow direction a second time, and guarantees this
    accumulation raster is consistent with the flow-direction raster.
    """

    pointer_path = Path(pointer_path)
    output_path = Path(output_path)

    if not pointer_path.exists():
        raise FileNotFoundError(f"Flow-direction file was not found: {pointer_path}")

    if out_type not in VALID_OUT_TYPES:
        raise ValueError(f"out_type must be one of {sorted(VALID_OUT_TYPES)}.")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with rasterio.open(pointer_path) as src:
        if src.count != 1:
            raise ValueError(
                f"Expected one band, but found {src.count} bands."
            )

        if src.crs is None:
            raise ValueError("Flow-direction raster has no CRS.")

        if src.crs.is_geographic:
            raise ValueError(
                "Flow accumulation requires a projected raster with metre-based coordinates."
            )

    wbt = WhiteboxTools()
    wbt.set_verbose_mode(False)

    result = wbt.d8_flow_accumulation(
        i=str(pointer_path),
        output=str(output_path),
        out_type=out_type,
        pntr=True,
    )

    if result != 0 or not output_path.exists():
        raise RuntimeError("WhiteboxTools could not create the flow-accumulation raster.")

    return output_path
