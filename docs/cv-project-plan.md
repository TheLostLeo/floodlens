# FloodLens CV-Ready Project Plan

This is the practical path from the current local demonstrator to an
80-90% complete portfolio project. The goal is to show a real, defensible
geospatial system: data engineering, backend, frontend, scientific integrity,
ML research, and reproducible deployment.

## What to say on a CV

Use a claim like this:

> Built FloodLens, a Dockerized neighbourhood flood-awareness platform using
> React, Leaflet, FastAPI, PostGIS, HydroSHEDS, FABDEM, Open-Meteo, and an
> isolated real-label ML research pipeline. Implemented provenance-aware data
> imports, async analysis jobs, partial-coverage handling, terrain
> susceptibility scoring, rainfall context, basin/river context, and
> event-held-out flood-mapping experiments.

Avoid saying that it predicts exact floods, gives official alerts, estimates
water depth, or provides a validated flood probability.

## What 80-90% means

| Area | 80-90% target |
| --- | --- |
| Resident demo | Works end-to-end for at least 2-3 documented regions with imported basin, river, terrain, and weather context |
| Dataset provenance | Every imported dataset has version, coverage, source URL, licence note, checksum, feature count, and import date |
| UI | Shows coverage readiness, unavailable/outside-coverage states, terrain score, rainfall context, basin context, and limitations clearly |
| Backend | Has guarded analysis jobs, worker processing, health endpoints, requeue, and integration tests |
| Data engineering | Has repeatable import commands and import reports for each region |
| Research ML | Uses real labels, held-out events/regions, saved metrics, and documented limitations |
| Presentation | Has a slide deck, demo script, architecture diagram, metrics table, and risk/ethics slide |

## Dataset expansion roadmap

Start with a few regions instead of trying to claim global coverage. A strong
CV project is better with three verified regions than a fragile worldwide
claim.

### Region 1: existing local demo

- Keep Chennai / Tamil Nadu as the primary demo if the local FABDEM and Asia
  HydroSHEDS data are already present.
- Record the exact point, radius, run date, source versions, and output cards.

### Region 2: second Indian urban flood case

Recommended choices:

- Mumbai / Mithi River area.
- Bengaluru / lake-drainage context.
- Guwahati / Brahmaputra-adjacent context.

Add:

- FABDEM tiles covering the chosen city.
- Existing Asia HydroBASINS/HydroRIVERS coverage if already imported.
- Optional local context in the presentation from public reports, but do not
  encode unverified local reports as model labels.

### Region 3: international contrast case

Recommended choices:

- Dhaka, Bangladesh.
- Bangkok, Thailand.
- Houston, USA.

Add:

- Matching HydroBASINS/HydroRIVERS regional package if not already imported.
- FABDEM tiles for the demo circle.
- A separate demo screenshot showing outside-coverage behavior before import
  and available behavior after import.

## Dataset import steps

1. Pick a region and a single demo point.
2. Download HydroBASINS and HydroRIVERS from the official HydroSHEDS pages.
3. Record the official source URL, version, licence terms, and archive checksum.
4. Extract all shapefile sidecars into `data/imports/`.
5. Run migrations if the database volume predates the basin tables.
6. Run the importer with explicit provenance:

```sh
docker compose --profile tools run --rm \
  -e BASINS_FILE=/imports/<hydrobasins-level-8>.shp \
  -e RIVERS_FILE=/imports/<hydrorivers>.shp \
  -e BASIN_LEVEL=8 \
  -e DATASET_VERSION=<download-version> \
  -e COVERAGE=<region-name> \
  -e BASINS_SOURCE_URL=<official-hydrobasins-url> \
  -e RIVERS_SOURCE_URL=<official-hydrorivers-url> \
  importer
```

7. Add FABDEM `.tif` or `.tiff` tiles for the demo area under:

```text
data/imports/fabdem/
```

8. Restart the worker/app and run a fresh analysis.
9. Open `/api/datasets/coverage` and save the response as import evidence.
10. Export a database-backed dataset report:

```sh
docker compose --profile tools run --rm --entrypoint /bin/sh importer /tools/export_dataset_report.sh
```

## Extra datasets to consider

These are good next additions, but each needs a clear role and provenance.

| Dataset | Why it helps | How to use it safely |
| --- | --- | --- |
| MERIT Hydro | Better conditioned hydrology and HAND-style context | Add as a research/advanced terrain feature, not as exact flood depth |
| OpenStreetMap waterways/drains/roads | Urban drainage and exposure context | Show as mapped context only; OSM completeness varies |
| JRC Global Surface Water | Permanent/seasonal water context | Use to avoid confusing permanent water with floodwater in research labels |
| Global Flood Database | More historical flood events | Use only in held-out research evaluation |
| Soil moisture or land cover | Better susceptibility explanation | Keep source/date/resolution visible |
| Local gauge or government flood reports | Strong validation evidence | Use only where licence and event definitions are clear |

## Implementation backlog for a full project

1. Add an import-report export command that writes a JSON/Markdown evidence
   file per region.
2. Add disposable PostGIS integration tests for create -> worker -> complete or
   waiting states.
3. Add a small coverage map panel showing imported regions and FABDEM tile
   availability.
4. Add a demo selector for saved example points.
5. Add a final presentation deck generated from `docs/presentation-outline.md`.
6. Add monitoring-style worker stats: queued, running, waiting, complete,
   failed counts.
7. Expand research ML with more independent events and permanent-water masking.

## What not to do

- Do not train on random chip splits and claim high accuracy.
- Do not show F1 as resident-app accuracy.
- Do not replace missing FABDEM, basin, river, or weather data with synthetic
  values.
- Do not describe the 1/2/5 km circle as a watershed.
- Do not call imported regional coverage worldwide coverage.
