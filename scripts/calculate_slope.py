import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_FOLDER = PROJECT_ROOT / "src"

sys.path.insert(0, str(SRC_FOLDER))

from terrain.slope import calculate_slope_degrees


SOURCE_DEM = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "study_area_dem_utm44n.tif"
)

OUTPUT_SLOPE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "slope_degrees.tif"
)


def main():
    output_path = calculate_slope_degrees(SOURCE_DEM, OUTPUT_SLOPE)

    print("\nFloodLens slope calculation complete\n")
    print(f"Output file: {output_path}")


if __name__ == "__main__":
    main()