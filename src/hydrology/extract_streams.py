from pathlib import Path

import rasterio
from whitebox import WhiteboxTools


def extract_drainage_paths(flow_accumulation_path, output_path, threshold):
    """
    Extract a drainage-path raster from a flow-accumulation raster.

    Pixels whose accumulated upslope contribution is at or above
    `threshold` (in the same units as the flow-accumulation raster,
    typically contributing cell count) are classified as part of a
    natural drainage path.
    """

    flow_accumulation_path = Path(flow_accumulation_path)
    output_path = Path(output_path)

    if not flow_accumulation_path.exists():
        raise FileNotFoundError(
            f"Flow-accumulation file was not found: {flow_accumulation_path}"
        )

    if threshold <= 0:
        raise ValueError("threshold must be a positive number.")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with rasterio.open(flow_accumulation_path) as src:
        if src.count != 1:
            raise ValueError(
                f"Expected one band, but found {src.count} bands."
            )

    wbt = WhiteboxTools()
    wbt.set_verbose_mode(False)

    result = wbt.extract_streams(
        flow_accum=str(flow_accumulation_path),
        output=str(output_path),
        threshold=threshold,
    )

    if result != 0 or not output_path.exists():
        raise RuntimeError("WhiteboxTools could not create the drainage-path raster.")

    return output_path
