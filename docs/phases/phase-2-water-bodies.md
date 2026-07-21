# Phase 2 — Water Bodies Mapping

## Goal

Phase 2 adds real surface-water features — rivers, streams, canals, lakes, and reservoirs — to FloodLens.

Terrain and drainage-path analysis from Phase 1 can predict *where water would tend to flow*, but it does not know where water already permanently exists. Combining Phase 1's terrain-derived drainage paths with actual mapped water bodies from Phase 2 lets FloodLens tell the difference between an ephemeral runoff channel and an existing river or reservoir — both of which raise flood risk, but for different reasons.

All Phase 2 code lives under `src/water_bodies/`, runnable via the scripts in `scripts/phase2_water_bodies/`. All Phase 2 data lives under `data/raw/phase2_water_bodies/` and `data/processed/phase2_water_bodies/`.

## Step 1 — Fetch water bodies from OpenStreetMap

Rivers, streams, canals, lakes, and reservoirs are pulled from OpenStreetMap using the public [Overpass API](https://overpass-api.de) — no API key required.

```text
src/water_bodies/overpass_client.py
src/water_bodies/fetch_water_bodies.py
scripts/phase2_water_bodies/fetch_water_bodies.py
```

The Overpass query requests, for a given bounding box:

- `waterway` = `river`, `stream`, or `canal` — mapped as line features;
- `natural` = `water` — mapped as polygons when the way is closed (lakes, ponds);
- `landuse` = `reservoir` — mapped as polygons (reservoirs).

The bounding box used matches the same study-area selection as Phase 1's DEM fetch (`scripts/phase1_terrain/fetch_dem.py`), so both phases describe the same area.

```text
python scripts/phase2_water_bodies/fetch_water_bodies.py
```

Output:

```text
data/raw/phase2_water_bodies/water_bodies.geojson
```

This file is not modified. It remains the original source dataset, in WGS84 (EPSG:4326), the same CRS returned by OpenStreetMap.

## Step 2 — Convert Overpass results to GeoJSON

Overpass returns its own JSON format with inline node geometry (`out geom;`). `overpass_to_geojson()` converts each element into a standard GeoJSON `Feature`:

- closed ways (first and last coordinate identical) become `Polygon` features — lakes and reservoirs;
- open ways become `LineString` features — rivers, streams, and canals.

Each feature keeps its original OpenStreetMap tags (e.g. `waterway`, `name`) as GeoJSON `properties`.

## Next steps (not yet implemented)

- Reproject `water_bodies.geojson` into the same projected CRS as the Phase 1 terrain rasters (EPSG:32644) so the two phases can be combined directly.
- Rasterize water-body polygons/lines to the DEM's grid, so they can be compared pixel-for-pixel against slope, flow accumulation, and drainage paths.
- Cross-reference Phase 1 drainage paths against mapped rivers to distinguish "matches an existing river" from "runoff-only channel with no permanent water".

## Phase 2 completion criteria

Phase 2 is complete when this file exists and has been visually verified in QGIS against the study area boundary:

```text
data/raw/phase2_water_bodies/water_bodies.geojson
```

The next phase will combine Phase 1 terrain/hydrology outputs with Phase 2 water bodies and rainfall data to produce the first flood-susceptibility indicators.
