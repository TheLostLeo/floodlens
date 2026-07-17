import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from terrain.reproject import reproject_dem_to_utm


source_dem = PROJECT_ROOT / "data" / "raw" / "dem" / "study_area_dem.tif"

output_dem = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "study_area_dem_utm44n.tif"
)

result = reproject_dem_to_utm(source_dem, output_dem)

print(f"Reprojection complete: {result}")