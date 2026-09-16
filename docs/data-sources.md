# Data sources and integrity policy

## Milestone 3 imports

Download HydroBASINS and HydroRIVERS from the official HydroSHEDS distribution:

- HydroBASINS: `https://www.hydrosheds.org/products/hydrobasins`
- HydroRIVERS: `https://www.hydrosheds.org/products/hydrorivers`

Begin with one representative regional package and HydroBASINS level 8; do not download every optional product at once.

Before import:

1. Record the official download page and dataset release/version.
2. Read and retain the licence/attribution terms.
3. Preserve the downloaded archive checksum separately; the current tool also records the extracted `.shp` checksum.
4. Extract `.shp`, `.dbf`, `.prj`, and `.shx` together into `data/imports/`.
5. Confirm that basin and river packages cover the same named region.
6. If the database volume predates Milestone 3, run the local migration tool described in the README.

The importer expects standard HydroSHEDS fields such as `HYBAS_ID`, `NEXT_DOWN`, `MAIN_BAS`, `PFAF_ID`, `SUB_AREA`, `UP_AREA`, `ORDER_`, `ENDO`, and `COAST` for basins; and `HYRIV_ID`, `NEXT_DOWN`, `MAIN_RIV`, `HYBAS_L12`, `LENGTH_KM`, `UPLAND_SKM`, `DIS_AV_CMS`, and `ORD_STRA` for rivers. Field compatibility must be checked against the exact downloaded release before running it.

Import provenance is a readiness gate. Having one region imported means the datasets are available, not globally complete; a point outside imported polygons returns `outside_coverage`.

## Milestone 4 terrain source

- **FABDEM:** bounded bare-earth neighbourhood terrain tiles. Use GeoTIFF or
  Cloud-Optimized GeoTIFF tiles covering the selected demo area. Place only
  the needed `.tif` or `.tiff` files under `data/imports/fabdem/`.
- Official tile archive: `https://data.bris.ac.uk/datasets/s5hqmjcdj8yo2ibzi9b4ew3sn/`
- FABDEM v1.2 tiles are 30 m elevation in metres, EPSG:4326, with nodata
  values. The worker reads the mounted files locally and does not download
  them through the public API.
- FABDEM is non-commercial; review the current licence before any use beyond a
  student demo.

## Milestone 5 runtime sources

- **Open-Meteo:** live forecast rainfall context; failures remain unavailable
  and are never replaced with fabricated weather.
- **OpenStreetMap:** map background only in the current UI.

## Later optional sources

- **MERIT Hydro:** conditioned elevation, flow direction, upstream area, and
  HAND context by selected tile.
- **OpenStreetMap feature extracts:** optional mapped buildings, roads, drains,
  and waterways, cached and attributed under provider policy.

Copernicus GLO-30 is a digital surface model containing buildings and vegetation. It must not be treated raw as bare-earth local drainage terrain.

## Research-only sources

- Global Flood Database: historical labels for event/geography-held-out structured ML evaluation.
- Sen1Floods11: optional post-event Sentinel-1 flood mapping.

The legacy synthetic model artifacts are not valid training labels or real-world validation for the resident product.

## Non-negotiable behavior

- No synthetic DEM, weather, watershed, flood label, risk probability, or depth in resident results.
- Missing, stale, failed, or outside-coverage data is shown explicitly.
- Local 1/2/5 km circles are not watersheds.
- Global datasets do not resolve street drains, culverts, kerbs, levees, walls, or sewer failures.
- Every completed future result records source, version, resolution/time where available, algorithm version, quality flags, and limitations.
