import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from hydrology.breach_depressions import breach_dem_depressions


SOURCE_DEM = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "phase1_terrain"
    / "study_area_dem_utm44n.tif"
)

OUTPUT_DEM = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "phase1_terrain"
    / "study_area_dem_breached.tif"
)


result = breach_dem_depressions(SOURCE_DEM, OUTPUT_DEM)

print(f"Depression breaching complete: {result}")