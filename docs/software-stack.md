# Software stack and deployment

## Application stack

| Layer | Technology | Version in source | Role |
| --- | --- | --- | --- |
| UI | React | 18.3.1 | Interactive resident interface |
| UI language | TypeScript | 5.7.2 | Type-safe frontend code |
| Map | Leaflet + React-Leaflet | 1.9.4 + 4.2.1 | Map, marker, local-radius circle, overlays |
| UI build | Vite | 8.3.0 | Builds static frontend assets |
| UI test tool | Vitest | 5.0.1 | Frontend test framework reserved for expansion |
| API | FastAPI | 0.115.6 | JSON API and static file server |
| API runtime | Uvicorn | 0.34.0 | ASGI server |
| Validation | Pydantic | 2.10.3 | Coordinate/radius validation and response schemas |
| Database access | SQLAlchemy + Psycopg | 2.0.36 + 3.2.3 | SQL execution and PostgreSQL connection |
| Spatial database | PostgreSQL/PostGIS | postgis/postgis:16-3.4 | Jobs, geometry, vectors, provenance |
| Terrain processing | Rasterio + NumPy | 1.4.3 + 2.2.1 | GeoTIFF read, sampling, slope calculations |
| Weather HTTP client | HTTPX | 0.28.1 | Open-Meteo request |
| Test framework | pytest | 8.3.4 | Python logic tests |
| Container build | Docker Compose | Compose file in repository root | Local multi-service run |
| Node base image | Node | 22.12.0 | Frontend build stage |
| Python base image | Python | 3.12.8 | API and worker runtime |

## Docker services

| Service | Purpose | Browser exposed? | Network access |
| --- | --- | --- | --- |
| `app` | Serves compiled React files and FastAPI API | Yes, loopback only on port 8000 by default | `web`, private `data` |
| `worker` | Processes analysis jobs | No | private `data`, outbound `egress` |
| `db` | PostgreSQL + PostGIS data store | No | private `data` |
| `migrate` | Applies SQL migrations to an existing DB | No; operator tool | private `data` |
| `importer` | Imports HydroBASINS/HydroRIVERS shapefiles | No; operator tool | private `data` |

The public host mapping is `127.0.0.1:8000:8000`, so use
`http://127.0.0.1:8000/` on the same computer. `0.0.0.0` is a binding address,
not the preferred browser address.

## Reproducibility and security

- The frontend uses `package-lock.json` and `npm ci` inside the Docker build.
- The latest verified lockfile audit had **0 known npm vulnerabilities**.
- `.env`, `node_modules`, downloaded data, and local build cache are ignored
  by Git.
- The database port is not published to the host.
- The worker alone receives outbound internet access for Open-Meteo.
- Rasterio needs `libexpat1`; both API and worker images install it.

## Local run

```sh
cd /storage/projects/floodlens
sudo docker compose up --build
```

Open `http://127.0.0.1:8000/`. Do not use `docker compose down -v` unless you
intend to delete the named database volume and its imported data.
