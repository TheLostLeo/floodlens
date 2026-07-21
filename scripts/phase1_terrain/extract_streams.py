import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from hydrology.extract_streams import extract_drainage_paths


FLOW_ACCUMULATION = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "phase1_terrain"
    / "flow_accumulation.tif"
)

OUTPUT_RASTER = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "phase1_terrain"
    / "drainage_paths.tif"
)

# Pixels are 30m x 30m (900 sq m). A threshold of 1000 contributing
# cells corresponds to roughly 0.9 sq km of upslope drainage area, a
# starting point for identifying natural drainage paths in this study
# area. Lower it to show more, finer drainage paths.
THRESHOLD_CELLS = 1000


result = extract_drainage_paths(FLOW_ACCUMULATION, OUTPUT_RASTER, THRESHOLD_CELLS)

print(f"Drainage-path extraction complete: {result}")
