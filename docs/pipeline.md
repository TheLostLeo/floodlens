# End-to-end pipeline

## Resident analysis pipeline

```text
Resident selects map point + 1/2/5 km radius
        |
        v
React + Leaflet frontend
        | POST /api/analyses (coordinates and radius only)
        v
FastAPI validates input and creates UUID job in PostGIS
        |
        v
PostgreSQL/PostGIS analyses table: queued, 0%
        |
        v
Worker atomically claims one job with FOR UPDATE SKIP LOCKED
        |
        +--> Open-Meteo: 48-hour hourly precipitation
        |       -> total rain, maximum hourly rain, wet hours, pressure level
        |
        +--> PostGIS: HydroBASINS + HydroRIVERS
        |       -> containing sub-basin, upstream area, nearby mapped river
        |
        +--> mounted FABDEM GeoTIFF files
                -> elevation, local relief, slope, coverage, terrain score
        |
        v
Worker writes structured JSON context and final job state
        |
        v
Frontend polls GET /api/analyses/{uuid} every 1.5 seconds
        |
        v
Resident sees completed context or explicit unavailable/outside-coverage state
```

## Job state machine

```text
queued -> running -> complete
                  -> waiting_for_data -> queued (operator adds data; resident requeues)
                  -> failed
```

- `queued`: API accepted a valid request.
- `running`: worker claimed the job and is checking sources.
- `complete`: local terrain is available. Basin or weather limitations still
  appear transparently in the result.
- `waiting_for_data`: a required spatial source is missing or outside imported
  coverage; it is resumable with the guarded requeue endpoint.
- `failed`: an unexpected worker failure occurred; it is terminal.

## Data preparation pipeline

```text
User downloads official regional datasets
        |
        +--> HydroBASINS + HydroRIVERS shapefiles
        |       -> importer validates mounted paths
        |       -> shp2pgsql staging tables
        |       -> normalized PostGIS basins/rivers tables
        |       -> dataset_imports provenance record with checksum/count/version
        |
        +--> FABDEM GeoTIFF tiles
                -> stored locally under data/imports/fabdem/
                -> mounted read-only into worker at /imports/fabdem
```

The public API never accepts local file paths. Dataset import is an operator
action, not something a resident can trigger from the browser.

## What happens when information is missing

| Condition | Behaviour |
| --- | --- |
| Open-Meteo unavailable | Rainfall is shown as unavailable; no made-up rainfall is used. |
| No HydroBASINS/HydroRIVERS import | Basin context is unavailable. |
| Selected point outside imported basin region | Basin context is outside coverage. |
| No FABDEM tile | Terrain remains unavailable and the job waits for data. |
| Point outside mounted FABDEM tile | Terrain is outside coverage and no terrain score is produced. |

This is deliberate data-integrity behaviour. Missing data is more honest than
an attractive but fabricated map result.
