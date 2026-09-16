# Architecture through Milestone 5

```text
Browser at http://localhost:8000
  -> app container (React static build + FastAPI, one origin)
       -> db (PostgreSQL/PostGIS, private data network only)
       <- worker (private data + outbound egress networks)
            -> Open-Meteo
            -> user-mounted FABDEM GeoTIFF tiles

Operator-only importer (private data network)
  -> user-mounted HydroBASINS/HydroRIVERS shapefiles
  -> normalized PostGIS tables + dataset provenance
```

The API persists server-generated UUID analysis jobs. Workers claim a queued row with `FOR UPDATE SKIP LOCKED`, so concurrent workers cannot claim the same row. `waiting_for_data` is a resumable state through a guarded requeue operation; `complete` and `failed` are terminal.

## Basin context

For a point, the service:

1. requires ready HydroBASINS and HydroRIVERS provenance records;
2. finds the finest imported basin polygon covering the point;
3. follows fixed-level `NEXT_DOWN` topology in reverse to collect upstream sub-basins, with a visited path to prevent cycles;
4. unions and simplifies upstream geometry for browser display;
5. finds the nearest mapped river segment intersecting the containing sub-basin;
6. stores the structured context against the analysis.

The nearby river result is deliberately labelled contextual. Basin membership and geographic proximity do not prove property-level hydraulic connectivity or flooding.

## Terrain and rainfall results

Milestone 4 reads user-mounted FABDEM GeoTIFF tiles from `/imports/fabdem`
inside the worker. The worker clips a bounded 1, 2, or 5 km neighbourhood
circle, computes point elevation, local relief, median slope, quality flags,
and a deterministic relative terrain susceptibility score. If tiles are
missing or outside coverage, the result remains unavailable or outside
coverage; no synthetic terrain or fallback score is emitted.

Milestone 5 summarizes Open-Meteo forecast precipitation into rainfall
pressure. Rainfall pressure is context only and is not an official warning.
The final resident view displays terrain susceptibility, rainfall pressure,
basin context, provenance, limitations, and dataset-pending instructions.

## Storage boundaries

- PostGIS: jobs, dataset provenance, basin/river vectors, structured context,
  terrain result JSON, and rainfall result JSON.
- Named artifact volume: reserved for future DEM clips and derived rasters.
- Browser: simplified display geometry and API calls served from the same
  application origin.
- Root legacy prototype has been removed and cannot supply resident results.

## Remaining milestones

Real historical-event ML follows only after the deterministic workflow is
validated against real labels with event- or geography-held-out evaluation.
