# FloodLens

Resident-facing worldwide flood-awareness application through Milestone 5. FloodLens separates a small neighbourhood assessment area from its larger river-basin context. It is **not** an official alert service, evacuation tool, exact flood-depth predictor, or proof that a property will flood.

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

## Local configuration

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

## Verification commands

```sh
cd apps/api && python -m pytest tests
docker compose config
```

Python source compilation succeeds. The complete tests currently require the
pinned API dependencies, including SQLAlchemy and Rasterio. The preserved
legacy virtual environment can run the dependency-light domain, schema,
weather, terrain-scoring, and worker tests. Docker Compose is unavailable in
the current Codex execution environment, and frontend dependencies have not
been installed locally.

The first successful Docker build will install the pinned frontend and backend
dependencies. It should also be followed by generating and retaining
`apps/web/package-lock.json`; then change the root Dockerfile from `npm
install` to `npm ci` and verify the complete stack.
