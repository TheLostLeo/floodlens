import sys
from pathlib import Path

import numpy as np
import rasterio


PROJECT_ROOT = Path(__file__).resolve().parents[2]

ORIGINAL = PROJECT_ROOT / "data" / "processed" / "phase1_terrain" / "study_area_dem_utm44n.tif"
FILLED = PROJECT_ROOT / "data" / "processed" / "phase1_terrain" / "study_area_dem_filled.tif"
BREACHED = PROJECT_ROOT / "data" / "processed" / "phase1_terrain" / "study_area_dem_breached.tif"


def compare(original_path, corrected_path, label):
    with rasterio.open(original_path) as orig_ds:
        original = orig_ds.read(1, masked=True).astype("float64").filled(np.nan)

    with rasterio.open(corrected_path) as corr_ds:
        corrected = corr_ds.read(1, masked=True).astype("float64").filled(np.nan)

    difference = corrected - original
    valid = np.isfinite(difference)
    changed = difference[valid & (difference != 0)]
    total_valid = int(valid.sum())

    print(f"\n{label}")
    print(f"  Source: {corrected_path.name}")
    print(
        f"  Pixels changed:  {changed.size:,} / {total_valid:,} "
        f"({100 * changed.size / total_valid:.3f}%)"
    )
    if changed.size > 0:
        print(f"  Mean change:     {changed.mean():.3f} m")
        print(f"  Max change:      {changed.max():.3f} m")
        print(f"  95th pct change: {np.percentile(changed, 95):.3f} m")


def main():
    print("Comparing depression-removal methods against the original UTM DEM")
    compare(ORIGINAL, FILLED, "FILL (fill_depressions)")
    compare(ORIGINAL, BREACHED, "BREACH (breach_depressions)")


if __name__ == "__main__":
    main()
