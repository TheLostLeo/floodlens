import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from terrain.reproject import reproject_dem_to_utm


source_dem = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "phase1_terrain"
    / "dem"
    / "study_area_dem_api.tif"
)

if not source_dem.exists():
    raise FileNotFoundError(
        "No API-fetched DEM found at "
        f"{source_dem}. Run scripts/phase1_terrain/fetch_dem.py first "
        "(requires OPENTOPOGRAPHY_API_KEY in your .env file - see .env.example). "
        "The old manually-downloaded DEM has been archived at "
        "data/raw/phase1_terrain/dem/old/study_area_dem_manual.tif and is no "
        "longer used by this pipeline."
    )

output_dem = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "phase1_terrain"
    / "study_area_dem_utm44n.tif"
)

result = reproject_dem_to_utm(source_dem, output_dem)

print(f"Reprojection complete: {result}")