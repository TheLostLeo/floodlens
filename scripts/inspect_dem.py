import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_FOLDER = PROJECT_ROOT / "src"

sys.path.insert(0, str(SRC_FOLDER))

from terrain.dem_reader import read_dem_metadata


#DEM_PATH = PROJECT_ROOT / "data" / "raw" / "dem" / "study_area_dem.tif"
#DEM_PATH = PROJECT_ROOT / "data" / "processed" / "study_area_dem_utm44n.tif"
DEM_PATH = PROJECT_ROOT / "data" / "processed" / "slope_degrees.tif"

def main():
    metadata = read_dem_metadata(DEM_PATH)

    print("\nFloodLens DEM inspection result\n")
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()