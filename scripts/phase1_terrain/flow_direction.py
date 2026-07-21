import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from hydrology.flow_direction import calculate_flow_direction


SOURCE_DEM = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "phase1_terrain"
    / "study_area_dem_breached.tif"
)

OUTPUT_RASTER = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "phase1_terrain"
    / "flow_direction.tif"
)


result = calculate_flow_direction(SOURCE_DEM, OUTPUT_RASTER)

print(f"Flow-direction calculation complete: {result}")
