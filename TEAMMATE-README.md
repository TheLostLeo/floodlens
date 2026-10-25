# FloodLens teammate and AI handoff guide

This file explains the current FloodLens project for a teammate or an AI coding
assistant. Read it before changing code. It describes the live application,
datasets, research ML work, current evidence, limits, and safe next work.

## 1. What FloodLens is

FloodLens is a **local neighbourhood flood-awareness demonstrator**. A resident
clicks a location on a map, selects a **1 km, 2 km, or 5 km** local assessment
circle, and receives three kinds of context:

1. **Relative terrain susceptibility** from bare-earth elevation;
2. **Forecast rainfall context** for the next 48 hours; and
3. **River-basin context** including the containing sub-basin, upstream area,
   and nearby mapped river.

The project runs locally with Docker. The public browser address is normally
`http://127.0.0.1:8000/`.

FloodLens does **not** claim to be an official warning service, evacuation
tool, flood-depth predictor, property-flood predictor, or flood-probability
calculator. A selected 1/2/5 km circle is **not a watershed**. A nearby river
or common basin does not prove that a selected property is hydraulically
connected to that river.

## 2. Current project state

| Area | Current state |
| --- | --- |
| Resident web application | Implemented and demonstrated locally |
| Map selection and radius UI | Implemented for exactly 1, 2, and 5 km |
| API, worker, and PostGIS jobs | Implemented |
| HydroBASINS/HydroRIVERS import | Asia data imported for the local demo |
| FABDEM terrain analysis | Implemented for mounted tile coverage |
| Open-Meteo rainfall context | Implemented |
| Research ML | Implemented separately under `research/` |
| ML connected to live resident app | **No** |
| Worldwide coverage | **No**; coverage is only where datasets/tiles are imported |

The user confirmed that a local Docker/browser analysis worked with Asia
HydroSHEDS data, FABDEM tiles, Open-Meteo rainfall, terrain output, and basin
context.

## 3. Important product and scientific rules

These rules are non-negotiable for every future change:

- Never fabricate terrain, rainfall, basin, river, flood-label, probability,
  or depth output when a source is missing.
- Return explicit `waiting_for_data`, `unavailable`, or `outside_coverage`
  states instead of pretending that data is global.
- Do not describe the terrain score as a probability, a flood prediction, or
  evidence that a home will flood.
- Keep local circle analysis separate from watershed analysis.
- Keep research ML results separate from the live resident application.
- Do not use legacy synthetic-model artifacts as scientific evidence.
- Do not expose database credentials, `.env` values, local dataset paths, or
  importer functionality through the public API.

## 4. Repository map

| Path | Purpose |
| --- | --- |
| `compose.yaml` | Docker services, networks, volumes, and local browser port |
| `Dockerfile` | Multi-stage root build: frontend build plus FastAPI-serving image |
| `apps/web/` | React + TypeScript + Leaflet user interface |
| `apps/api/app/` | FastAPI, worker, spatial processing, repository, schemas |
| `apps/api/migrations/` | PostGIS schema migrations |
| `apps/api/tests/` | Application/domain/terrain/weather/worker tests |
| `tools/` | Migration and HydroSHEDS import scripts/images |
| `data/imports/` | Local operator-provided FABDEM and HydroSHEDS files; not Git data |
| `research/` | Isolated real-label ML research pipeline; not resident app code |
| `docs/` | Architecture, methodology, metrics, PPT and operational documentation |
| `.agent/` | Maintained project knowledge and state; ignored by Git |

Useful detailed documents:

- [Architecture](docs/architecture.md)
- [Live request/data pipeline](docs/pipeline.md)
- [Frontend behaviour](docs/frontend.md)
- [Backend and database](docs/backend.md)
- [Data-source policy](docs/data-sources.md)
- [Metrics and research boundary](docs/metrics.md)
- [Research run results](research/results.md)

## 5. Architecture

```text
Resident browser at 127.0.0.1:8000
        |
        v
React + Leaflet frontend
        |
        v
FastAPI app container
        |
        v
PostgreSQL + PostGIS <---- background worker
                              |        |        |
                              |        |        +--> mounted FABDEM GeoTIFFs
                              |        +-----------> HydroBASINS/HydroRIVERS in PostGIS
                              +--------------------> Open-Meteo rainfall forecast
```

Docker services:

| Service | Role |
| --- | --- |
| `app` | Serves the compiled React site and FastAPI API on the same origin |
| `worker` | Claims queued jobs and computes weather, hydrology, and terrain context |
| `db` | PostgreSQL/PostGIS database for jobs, geometry, imports, and results |
| `migrate` | Operator-only migration tool profile |
| `importer` | Operator-only HydroBASINS/HydroRIVERS import tool profile |

`app` uses the normal `web` bridge network and the internal `data` network.
`db` is on the internal `data` network only. The worker uses `data` plus an
outbound `egress` network for Open-Meteo.

## 6. Resident analysis flow

1. User clicks the Leaflet map.
2. UI places a marker and lets the user choose 1, 2, or 5 km.
3. UI sends a `POST /api/analyses` request with coordinates and radius.
4. FastAPI validates the request and stores a UUID job in PostGIS.
5. The worker atomically claims one queued job using `FOR UPDATE SKIP LOCKED`.
6. The worker checks Open-Meteo, HydroBASINS/HydroRIVERS, and FABDEM.
7. It saves structured JSON context and updates job progress/status.
8. The UI polls `GET /api/analyses/{id}` every 1.5 seconds.
9. The user sees result cards, map overlays, or an explicit missing-data state.

Job states:

```text
queued -> running -> complete
                  -> waiting_for_data -> queued after safe requeue
                  -> failed
```

`waiting_for_data` is expected when a required local spatial source is missing
or outside the imported/mounted coverage. It is not a prediction result.

## 7. Public API

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/health/live` | Process liveness check |
| `GET` | `/health/ready` | Database readiness check |
| `POST` | `/api/analyses` | Create a validated analysis job; returns HTTP 202 |
| `GET` | `/api/analyses/{analysis_id}` | Read status and stored analysis context |
| `POST` | `/api/analyses/{analysis_id}/requeue` | Requeue only a waiting-for-data job |
| `GET` | `/api/basins/context` | Get available/unavailable/outside-coverage basin context |

Input validation rejects invalid coordinates and radii other than 1, 2, or 5.
The API must never accept local filesystem paths, database credentials, or
dataset-import requests from a resident browser.

## 8. Live datasets

| Dataset | Used for | Current local scope | Key limitation |
| --- | --- | --- | --- |
| FABDEM v1.2 | 30 m bare-earth elevation, slope, local relief, terrain score | Mounted Chennai-area tiles | Does not model drains, culverts, walls, or sewer systems |
| HydroBASINS Standard level 8 | Containing sub-basin and upstream context | Asia import | Imported area is not worldwide coverage |
| HydroRIVERS | Nearby mapped river and distance | Asia import | Proximity is not property-level connectivity |
| Open-Meteo | 48-hour hourly rainfall context | Live provider request | Context only, not official alerting |
| OpenStreetMap | Basemap | Browser map | Not a flood or terrain source |

Verified local import evidence:

- **28,907** Asia HydroBASINS level-8 polygons
- **1,428,959** Asia HydroRIVERS features
- Chennai 5 km demo: terrain score **56/100**, coverage **97%**, **84,222**
  valid terrain cells, point elevation **18.55 m**, relief **25.15 m**, median
  slope **0.72%**

### Terrain score

The live worker computes a deterministic index from real FABDEM samples:

```text
terrain score = 55% low relative position
              + 25% flatness
              + 20% low local relief
```

Display bands are 0–33 lower, 34–66 moderate, and 67–100 higher **relative
terrain susceptibility**. The score is not an ML probability and is not a
validated flood-outcome classifier.

## 9. Database and provenance

Important PostGIS groups include:

| Table/group | Purpose |
| --- | --- |
| `analyses` | UUID job, coordinates, radius, progress, status, timestamps |
| `weather_provenance` | Open-Meteo request/result status and source information |
| `dataset_imports` | Dataset version, region, source, checksum, count, readiness |
| `basins` and `rivers` | Imported HydroSHEDS geometry and attributes |
| `analysis_basin_context` | Stored hydrology result for a job |
| `analysis_terrain_context` | Stored terrain result for a job |
| `analysis_rainfall_context` | Stored rainfall result for a job |

Geometry is stored in EPSG:4326. Nearby-river calculations use PostGIS
`geography` distance calculations before conversion to kilometres.

The importer only reads mounted `.shp` files beneath `/imports`; it stages data
with `shp2pgsql`, normalizes it, and stores import provenance. It is an
operator-only command, not a browser endpoint.

## 10. Research ML pipeline

`research/` is a reproducible, **research-only** flood-event mapping workflow.
It is intentionally not imported by the resident API, worker, or frontend.

### Research datasets

| Input | Purpose |
| --- | --- |
| Sen1Floods11 v1.1 hand-labelled subset | Sentinel-1 VV/VH chips and observed-water labels |
| Sen1Floods11 metadata | Event dates and geometry |
| CHIRPS v2 daily data | 60-day antecedent rainfall at event centroids |

Actual local run:

| Dataset stage | Result |
| --- | ---: |
| Paired S1 / label / JRC reference files | 446 per layer |
| Valid labelled chips after checks | 440 |
| Documented events | 11 |
| Events with complete 60-day CHIRPS | 10 |
| Chips used by rainfall experiments | 410 |
| Positive observed-water chips before rainfall exclusion | 169 / 440 |

Five chips had no valid `0`/`1` label pixels. One had no finite SAR values.
Spain was excluded from rainfall modelling because one source pixel was invalid.
No values were imputed.

### ML target and evaluation

Target: `has_observed_water` means a chip contains at least 5% labelled water
during a documented flood event. This is not yet claimed to represent temporary
floodwater only; permanent-water treatment needs further validation.

The split is by whole flood event, never random chips:

| Split | Events | Chips |
| --- | --- | ---: |
| Train | Bolivia, Sri Lanka, India, Cambodia, Nigeria, Somalia | 199 |
| Validation | USA, Paraguay | 135 |
| Test | Ghana, Pakistan | 76 |

This prevents spatial leakage where parts of the same flood event would appear
in both training and test sets.

### Models and held-out results

| Model | Inputs | Test F1 | Precision | Recall | PR-AUC | ROC-AUC |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Gradient-boosting baseline | Mean Sentinel-1 VV/VH + 1/3/7/14/30/60-day rain totals | 0.468 | 0.355 | 0.688 | 0.664 | 0.787 |
| Rainfall LSTM | Full 60-day rain sequence + mean Sentinel-1 VV/VH | 0.615 | 0.800 | 0.500 | 0.658 | 0.746 |

Thresholds were chosen using the validation events only, then frozen before
test evaluation. Baseline threshold: 0.30. LSTM threshold: 0.61.

The LSTM has a higher F1 and fewer false positives, but the baseline has higher
recall and higher PR-AUC/ROC-AUC. The test contains only two independent
events, so neither model should be called universally better. These values are
not the accuracy of the live web application.

## 11. How to run locally

Run the application stack:

```bash
cd /storage/projects/floodlens
sudo docker compose up --build
```

Open `http://127.0.0.1:8000/` in the same computer's browser.

Stop services while keeping the database volume:

```bash
sudo docker compose down
```

Do **not** use `docker compose down -v` unless intentionally deleting imported
PostGIS data.

Run research tests when the research environment is already installed:

```bash
PYTHONPATH=research/src .venv-research/bin/python -m pytest research/tests -q
```

The ML pipeline is documented in [research/README.md](research/README.md).
It has separate dependencies and does not require Docker/PostGIS.

## 12. Verification already completed

| Check | Last recorded result |
| --- | --- |
| Application-focused Python tests | 9 passed |
| Research pipeline tests | 4 passed |
| Frontend production build | Passed |
| Frontend `npm audit` | 0 vulnerabilities reported at locked versions |
| Research dependency check | `pip check` passed |
| User-local Docker/browser analysis | Completed with imported Asia/FABDEM data |

Full API integration tests still need a disposable PostGIS test environment.

## 13. Safe next work

Good next tasks:

1. Add end-to-end API tests against a temporary PostGIS database.
2. Add migration version tracking and structured worker retry/health logs.
3. Add a clear data-coverage badge to the UI.
4. Add import reports with license, checksum, source version, date, and count.
5. Add more operator-imported regions, while always showing true coverage.
6. Add more independent historical flood events, especially India/deployment
   geography, before expanding ML claims.
7. Add calibrated local drainage, soil moisture, streamflow, or gauge data only
   with provenance and validation.

Do not make these changes without checking the relevant source code and docs
first. Avoid unrelated rewrites of Docker, data imports, or the resident
product boundary.

## 14. Prompt for another AI assistant

Copy this into an AI chat together with this repository:

```text
You are working on FloodLens, a local neighbourhood flood-awareness project.
Read TEAMMATE-README.md, AGENTS.md, .agent/index.md, and .agent/STATE.md before
editing. Preserve the existing dirty worktree and do not reset, clean, commit,
push, download datasets, install packages, run Docker, or run importers unless
explicitly asked.

The live app is React/Leaflet + FastAPI + PostGIS + worker in Docker. It shows
real FABDEM terrain context, Open-Meteo rainfall context, and HydroBASINS/
HydroRIVERS basin/river context for a selected 1/2/5 km circle. It is not an
official flood warning, property-flood predictor, depth prediction, or flood
probability. Do not fabricate missing data. Return unavailable or
outside-coverage states.

The separate research/ directory contains real-label Sen1Floods11 + CHIRPS
research models. Its event-held-out LSTM F1 is 0.615 on a two-event test, but
this is exploratory research and must never be presented as live-app accuracy
or connected to resident-facing results without a separate validated decision.

First inspect relevant source files, explain your plan briefly, make the
smallest safe change, run focused verification, inspect the diff, and report
what changed and what remains unverified.
```

## 15. Before changing anything

1. Run `git status --short` and preserve unrelated user changes.
2. Read `AGENTS.md`, `.agent/index.md`, and `.agent/STATE.md`.
3. Treat current source and configuration as stronger evidence than old notes.
4. Make a small task-specific plan before structural work.
5. Run focused checks only after changes; report blocked checks honestly.
6. Do not stage, commit, push, deploy, or delete user data unless explicitly
   requested.
