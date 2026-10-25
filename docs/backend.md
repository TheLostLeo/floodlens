# Backend, worker, database, and tooling

## FastAPI endpoints

| Method | Endpoint | Input | Result |
| --- | --- | --- |
| `GET` | `/health/live` | None | Process liveness |
| `GET` | `/health/ready` | None | Database readiness; 503 if unavailable |
| `POST` | `/api/analyses` | Latitude, longitude, radius 1/2/5 | Creates UUID job, returns 202 |
| `GET` | `/api/analyses/{id}` | UUID | Job state plus stored context |
| `POST` | `/api/analyses/{id}/requeue` | UUID | Requeues only waiting-for-data jobs |
| `GET` | `/api/basins/context` | Latitude, longitude | Direct basin/river context |
| `GET` | `/api/datasets/coverage` | None | Registered dataset coverage, provenance, missing required datasets, and limitations |

Input validation rejects non-finite coordinates, latitude outside -90 to 90,
longitude outside -180 to 180, and radii other than 1, 2, or 5 km.

## Worker design

The background worker repeatedly attempts to claim one queued job. The SQL
claim uses `FOR UPDATE SKIP LOCKED`, which prevents two concurrent workers
from processing the same row. Each source output is stored separately as JSON
context so incomplete information can be displayed honestly.

The worker's normal order is:

1. fetch and save weather provenance;
2. calculate rainfall pressure;
3. calculate basin/river context from PostGIS;
4. calculate terrain score from mounted FABDEM tiles;
5. save contexts and transition the job.

An individual terrain problem no longer crashes the whole worker job. It is
stored as unavailable/outside coverage and the job enters `waiting_for_data`.

## Database design

| Table/group | Purpose |
| --- | --- |
| `analyses` | UUID job, coordinates, radius, status, progress, message, timestamps |
| `weather_provenance` | Provider response status, time metadata, raw response/detail |
| `dataset_imports` | Version, region, source URL, checksum, count, readiness state |
| `basins` | Imported HydroBASINS polygons and topology attributes |
| `rivers` | Imported HydroRIVERS line features and attributes |
| `analysis_basin_context` | Basin/river result JSON per job |
| `analysis_terrain_context` | Terrain result JSON per job |
| `analysis_rainfall_context` | Rainfall result JSON per job |

The database is PostGIS-enabled. Geometry is stored in EPSG:4326; distance to
the nearby river uses `geography` calculations before converting to kilometres.

## Data import safeguards

- The importer accepts only `.shp` paths mounted beneath `/imports`.
- It verifies required environment variables and shapefile existence.
- It uses `shp2pgsql` staging tables, then normalizes source attributes.
- It records SHA-256 checksums, source URLs, version, coverage, feature count,
  and import time in `dataset_imports`.
- It does not expose importer functionality through the public API.

## Operational commands

```sh
# Start local app, worker, and database
sudo docker compose up --build

# Apply migrations to an existing Docker database volume
sudo docker compose --profile tools run --rm migrate

# Export registered dataset provenance as JSON evidence
sudo docker compose --profile tools run --rm --entrypoint /bin/sh importer /tools/export_dataset_report.sh

# Stop containers but preserve database data
sudo docker compose down
```

Avoid `docker compose down -v` unless permanently deleting imported data is
intentional.
