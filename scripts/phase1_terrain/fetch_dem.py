import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from terrain.fetch_dem import buffer_bounds, fetch_dem


# Study-area selection (Tamil Nadu). Adjust to your own area of interest.
SELECTION = {"west": 79.75, "south": 12.75, "east": 80.20, "north": 13.35}
BUFFER_KM = 5.0

OUTPUT_DEM = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "phase1_terrain"
    / "dem"
    / "study_area_dem_api.tif"
)


def main():
    bounds = buffer_bounds(**SELECTION, buffer_km=BUFFER_KM)

    output_path = fetch_dem(
        south=bounds["south"],
        north=bounds["north"],
        west=bounds["west"],
        east=bounds["east"],
        output_path=OUTPUT_DEM,
    )

    print(f"DEM download complete: {output_path}")


if __name__ == "__main__":
    main()
