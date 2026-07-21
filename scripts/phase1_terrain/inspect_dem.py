import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_FOLDER = PROJECT_ROOT / "src"

sys.path.insert(0, str(SRC_FOLDER))

from terrain.dem_reader import read_dem_metadata


def main():
    parser = argparse.ArgumentParser(
        description="Inspect FloodLens raster metadata."
    )

    parser.add_argument(
        "--input",
        required=True,
        help="Path to the GeoTIFF file to inspect.",
    )

    args = parser.parse_args()

    input_path = Path(args.input).expanduser().resolve()

    metadata = read_dem_metadata(input_path)

    print("\nFloodLens raster inspection result\n")
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()