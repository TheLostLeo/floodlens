# Phase 1 — Terrain Data Foundation

## Goal

Phase 1 prepares reliable terrain data for FloodLens.

Floodwater moves downhill and collects in low-lying drainage paths. Before FloodLens can estimate flood susceptibility, it needs an elevation dataset that is valid, correctly projected, and measured in metres.

All Phase 1 code lives under `src/terrain/` and `src/hydrology/`, runnable via the scripts in `scripts/phase1_terrain/`. All Phase 1 data lives under `data/raw/phase1_terrain/` and `data/processed/phase1_terrain/`.

## Step 1 — Download the DEM via the OpenTopography API

The DEM is fetched automatically for a bounding box using the [OpenTopography Global DEM API](https://portal.opentopography.org) — this is the pipeline's actual, current DEM source (no manual download step).

```text
src/terrain/fetch_dem.py
scripts/phase1_terrain/fetch_dem.py
```

This requires a free OpenTopography API key. Copy `.env.example` to `.env` and set `OPENTOPOGRAPHY_API_KEY` (`.env` is git-ignored and must never be committed).

Before downloading, the selected area's bounding box is expanded outward with `buffer_bounds()`, because surface runoff can flow in from higher terrain just outside the user's selection. The buffer distance is configurable (default 5 km).

```text
python scripts/phase1_terrain/fetch_dem.py
```

Dataset used:

```text
SRTM GL1, approximately 30 metre resolution
```

Output:

```text
data/raw/phase1_terrain/dem/study_area_dem_api.tif
```

This file is not modified. It remains the original source dataset. An earlier manually-downloaded DEM has been archived (unused) at `data/raw/phase1_terrain/dem/old/study_area_dem_manual.tif` for reference only.

## Step 2 — Inspect the raw DEM in QGIS

The raw DEM was opened in QGIS to confirm that it contains terrain data.

Raw DEM properties (current study-area selection):

| Property | Value |
|---|---|
| File format | GeoTIFF |
| CRS | EPSG:4326 — WGS 84 |
| Width | 1,953 pixels |
| Height | 2,484 pixels |
| Pixel size | Approximately 30 m, represented in degrees |
| NoData value | -32768 |
| Exact elevation range | -10 m to 382 m |

QGIS is used for visual validation. Python performs the backend calculations.

## Step 3 — Inspect the DEM with Python

A Python module was created:

```text
src/terrain/dem_reader.py
```

A script was also created:

```text
scripts/phase1_terrain/inspect_dem.py
```

The inspection code confirms:

- the DEM file exists;
- it has one raster band;
- it has a coordinate reference system;
- it has valid elevation pixels;
- its NoData values are excluded from statistics;
- its dimensions, bounds, pixel size, and elevation values are known.

This prevents FloodLens from performing calculations on an invalid input file.

## Step 4 — Reproject the DEM into metres

The raw DEM uses `EPSG:4326`, which stores location using latitude and longitude degrees.

Degrees are not suitable for slope calculations because the distance represented by one degree changes by location. FloodLens therefore reprojects the DEM into:

```text
EPSG:32644 — WGS 84 / UTM Zone 44N
```

UTM coordinates use metres, allowing terrain calculations to use real horizontal distances.

The processed DEM was created at:

```text
data/processed/phase1_terrain/study_area_dem_utm44n.tif
```

Processed DEM properties (current study-area selection):

| Property | Value |
|---|---|
| CRS | EPSG:32644 |
| Units | metres |
| Pixel size | 30 m × 30 m |
| Width | 1,971 pixels |
| Height | 2,552 pixels |
| NoData value | -32768 |
| Elevation range | -9 m to 381 m |

## Step 5 — Calculate slope

Slope measures how steep the ground is at every DEM pixel. It is important because water generally moves faster down steeper terrain and can collect in flatter, low-lying locations.

```text
src/terrain/slope.py
scripts/phase1_terrain/calculate_slope.py
```

It reads `data/processed/phase1_terrain/study_area_dem_utm44n.tif` and produces:

```text
data/processed/phase1_terrain/slope_degrees.tif
```

### How slope is calculated

For each terrain pixel, FloodLens compares its elevation with the surrounding pixels.

It calculates:

- horizontal elevation change: `dz/dx`
- vertical elevation change: `dz/dy`
- total terrain gradient:

```text
gradient = √((dz/dx)² + (dz/dy)²)
```

Then it converts the gradient into an angle:

```text
slope in degrees = arctan(gradient) × 180 / π
```

Expected slope values:

| Slope | Meaning |
|---|---|
| 0° | completely flat |
| 0°–5° | nearly flat terrain |
| 5°–15° | gentle slope |
| 15°–30° | steep slope |
| above 30° | very steep terrain |
| 90° | vertical surface |

The slope output preserves the same map location, dimensions, CRS, and NoData areas as the UTM DEM.

## Step 6 — Fill or breach depressions

Raw DEMs contain artificial pits (sinks) that would otherwise trap simulated water and break flow-direction analysis. FloodLens can correct these two ways:

```text
src/hydrology/fill_sinks.py          → scripts/phase1_terrain/fill_sinks.py
src/hydrology/breach_depressions.py  → scripts/phase1_terrain/breach_depressions.py
```

- **Fill** raises low pixels until every cell has a downhill escape route. Simple, but can flatten broad low-lying areas.
- **Breach** cuts a narrow drainage channel through a depression instead, which is more conservative and preserves natural terrain shape. This is the version used going forward.

Breaching uses WhiteboxTools' `breach_depressions_least_cost` (not the legacy `breach_depressions`). The legacy tool was found to corrupt depressions that touch the raster edge (e.g. a coastline pixel dropped from 0 m to roughly -77,770 m, with over 3 million pixels shifted more than 100 m despite a 5 m depth cap). `breach_depressions_least_cost` with `fill=True` does not have this defect and is the recommended modern replacement.

Output:

```text
data/processed/phase1_terrain/study_area_dem_filled.tif
data/processed/phase1_terrain/study_area_dem_breached.tif
```

## Step 7 — Calculate flow direction

Flow direction (D8) assigns each pixel a pointer to the one neighbouring pixel that water would flow into next.

```text
src/hydrology/flow_direction.py
scripts/phase1_terrain/flow_direction.py
```

Input: `data/processed/phase1_terrain/study_area_dem_breached.tif`
Output: `data/processed/phase1_terrain/flow_direction.tif`

## Step 8 — Calculate flow accumulation

Flow accumulation counts how many upslope pixels drain into each pixel. High values mark natural drainage paths and locations where surface runoff is likely to collect.

```text
src/hydrology/flow_accumulation.py
scripts/phase1_terrain/flow_accumulation.py
```

Input: `data/processed/phase1_terrain/flow_direction.tif` (the D8 pointer raster from Step 7, not the DEM itself — this avoids recomputing flow direction a second time and keeps the two rasters consistent)
Output: `data/processed/phase1_terrain/flow_accumulation.tif`

## Step 9 — Extract drainage paths

Thresholding the flow-accumulation raster isolates pixels that carry enough upslope drainage area to be considered a natural drainage path (stream, channel, or gully).

```text
src/hydrology/extract_streams.py
scripts/phase1_terrain/extract_streams.py
```

Input: `data/processed/phase1_terrain/flow_accumulation.tif`
Output: `data/processed/phase1_terrain/drainage_paths.tif`

The default threshold (1,000 contributing cells, ≈0.9 km² of upslope area at 30 m resolution) is a starting point and may need tuning per study area.

## Phase 1 completion criteria

Phase 1 is complete when these files exist and are verified in QGIS:

```text
data/raw/phase1_terrain/dem/study_area_dem_api.tif
data/processed/phase1_terrain/study_area_dem_utm44n.tif
data/processed/phase1_terrain/slope_degrees.tif
data/processed/phase1_terrain/study_area_dem_breached.tif
data/processed/phase1_terrain/flow_direction.tif
data/processed/phase1_terrain/flow_accumulation.tif
data/processed/phase1_terrain/drainage_paths.tif
```

The next phase ([Phase 2 — Water Bodies Mapping](phase-2-water-bodies.md)) adds real rivers, lakes, and reservoirs from OpenStreetMap.