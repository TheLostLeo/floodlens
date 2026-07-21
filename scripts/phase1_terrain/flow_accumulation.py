import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from hydrology.flow_accumulation import calculate_flow_accumulation


FLOW_DIRECTION = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "phase1_terrain"
    / "flow_direction.tif"
)

OUTPUT_RASTER = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "phase1_terrain"
    / "flow_accumulation.tif"
)


result = calculate_flow_accumulation(FLOW_DIRECTION, OUTPUT_RASTER)

print(f"Flow-accumulation calculation complete: {result}")
