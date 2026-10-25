# FloodLens

Neighbourhood flood-awareness application through Milestone 5. The current resident demo focuses on India and the neighbouring subcontinent; assessments are available only where real datasets cover the chosen point and circle. FloodLens separates a small neighbourhood assessment area from its larger river-basin context. It is **not** an official alert service, evacuation tool, exact flood-depth predictor, or proof that a property will flood.

## Implemented source

- React/TypeScript/Leaflet point-and-radius UI (1, 2, or 5 km).
- FastAPI analysis creation, polling, guarded requeue, and basin-context APIs.
- PostgreSQL/PostGIS job, weather provenance, HydroBASINS, HydroRIVERS, import provenance, and per-analysis context schema.
- Separate worker with transactional `SKIP LOCKED` job claiming.
- Real Open-Meteo adapter with explicit unavailable behavior.
- HydroBASINS containing/upstream context and nearby same-sub-basin river lookup after data import.
- FABDEM-gated deterministic terrain susceptibility baseline.
- Open-Meteo rainfall-pressure interpretation with explicit unavailable behavior.
- Explainable result cards with provenance, limitations, and quality flags.
- Explicit `waiting_for_data` state before required spatial data exists; no synthetic fallback.

The repository root is the authoritative resident-facing rebuild. Historical
synthetic-model prototype code and artifacts have been removed.

## Project handbook and PPT material

Presentation-ready technical material is in [docs/README.md](docs/README.md).
It links architecture, pipeline, software stack, methodology, frontend,
backend, numerical metrics, current status, risks, future ML work, and a
slide-by-slide PPT outline. The metrics document explicitly separates measured
engineering evidence from the completed, research-only ML benchmark. Its F1
and related metrics are not claims about the resident web application.

For a teammate or another AI coding assistant, start with
[TEAMMATE-README.md](TEAMMATE-README.md). It explains the system, datasets,
research boundary, current verification, and safe development rules.

## Research ML pipeline

The research-only, real-label ML workflow is documented in
[research/README.md](research/README.md). It uses a separate environment and
does not change the resident-facing awareness result. Its event-held-out
baseline and LSTM experiments report metrics only after a completed run writes
held-out predictions to `research/artifacts/`.

## Local configuration

For the India-focused project presentation, use the [five-minute demo guide](docs/local-demo.md). It records verified Chennai terrain points, startup checks and remaining live-verification gaps.


1. Install Docker Desktop (or Docker Engine with the Compose plugin).
2. For the fastest local demo, run `docker compose up --build` and open `http://localhost:8000`.
3. Optionally copy `.env.example` to `.env` and set a private database password before a longer-running demo.

The React frontend is compiled into the same Docker image as FastAPI and is
served at `/`. The frontend calls the API at the same origin, so there is no
separate frontend server or browser port. The app publishes only
`127.0.0.1:${API_PORT:-8000}:8000`, so open it from the Docker host at
`http://localhost:8000`. Postgres has no host port and remains on the private
database network. The worker has outbound provider access on a separate network
from the private database network.

Do not use `docker compose down -v` unless permanent deletion of database and artifact volumes is intentional.

## API contract

- `POST /api/analyses` with `{ "latitude": 13.08, "longitude": 80.27, "radius_km": 2 }` returns `202`.
- `GET /api/analyses/{uuid}` returns progress and optional basin context.
- `POST /api/analyses/{uuid}/requeue` requeues only a `waiting_for_data` job.
- `GET /api/basins/context?latitude=13.08&longitude=80.27` returns available, unavailable, or outside-coverage context.
- `GET /api/datasets/coverage` returns registered imported dataset coverage, provenance, missing required datasets, and limitations.
- `GET /health/live` and `GET /health/ready` provide health status.

Before HydroBASINS/HydroRIVERS are imported, context APIs return an honest unavailable result. Before FABDEM tiles are mounted, terrain results return an honest unavailable result. Once FABDEM coverage exists for the selected circle, the worker can complete an analysis with a deterministic, explainable terrain susceptibility score. This score is relative terrain susceptibility, not flood probability, flood depth, or an emergency warning.

## Database migrations

For a brand-new Postgres volume, files in `apps/api/migrations/` run in filename order. Existing volumes do not automatically receive new init scripts. For an existing development volume, the intended idempotent local command is `docker compose --profile tools run --rm migrate`. Run it before importing data. A version-ledger migration system remains future production work.

If you already ran the demo before the terrain milestone was added, run:

```sh
sudo docker compose --profile tools run --rm migrate
```

## Dataset import

Read `docs/data-sources.md`. The importer accepts user-downloaded, extracted HydroBASINS and HydroRIVERS shapefiles mounted under `data/imports/`; it never accepts a path from the public API. A typical later command is:

```sh
docker compose --profile tools run --rm \
  -e BASINS_FILE=/imports/<hydrobasins-level-8>.shp \
  -e RIVERS_FILE=/imports/<hydrorivers>.shp \
  -e BASIN_LEVEL=8 \
  -e DATASET_VERSION=<download-version> \
  -e COVERAGE=<region-name> \
  -e BASINS_SOURCE_URL=<official-download-url> \
  -e RIVERS_SOURCE_URL=<official-download-url> \
  importer
```

Keep every shapefile sidecar (`.dbf`, `.prj`, `.shx`) beside its `.shp`. Import one matching regional pair at a time. The tool upserts features and records version, coverage, URLs, licence note, checksum, count, and import time.

For terrain susceptibility, download only the FABDEM GeoTIFF tile or tiles covering the demo area and place them here:

```text
data/imports/fabdem/
```

The worker reads `*.tif` and `*.tiff` from that directory through the Docker mount at `/imports/fabdem`. After adding tiles, rebuild or restart the worker:

```sh
sudo docker compose up --build
```

Then create a new analysis or click **Check imported data again** on a waiting one.

To export a dataset evidence report from the local database for your README,
PPT, or viva, run:

```sh
docker compose --profile tools run --rm --entrypoint /bin/sh importer /tools/export_dataset_report.sh
```

The report lists only registered imports. It is proof of imported local
coverage, not proof of worldwide coverage.

## Verification commands

```sh
cd apps/api && python -m pytest tests
docker compose config
```

Focused terrain, worker, and weather tests pass locally (9 tests). The
TypeScript/Vite production build passes and the committed frontend lockfile
has a clean npm audit. The full API collection still requires a test
environment with the pinned SQLAlchemy/PostGIS dependencies. Docker daemon
access is not available to Codex itself, but the local user-run demo has
successfully completed analyses using imported HydroSHEDS data and FABDEM
tiles.
