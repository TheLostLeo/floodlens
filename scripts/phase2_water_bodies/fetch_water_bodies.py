import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from water_bodies.fetch_water_bodies import download_water_bodies


# Same study-area selection used in scripts/phase1_terrain/fetch_dem.py
SELECTION = {"west": 79.75, "south": 12.75, "east": 80.20, "north": 13.35}

OUTPUT_PATH = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "phase2_water_bodies"
    / "water_bodies.geojson"
)


def main():
    output_path = download_water_bodies(
        south=SELECTION["south"],
        north=SELECTION["north"],
        west=SELECTION["west"],
        east=SELECTION["east"],
        output_path=OUTPUT_PATH,
    )

    print(f"Water-bodies download complete: {output_path}")


if __name__ == "__main__":
    main()
