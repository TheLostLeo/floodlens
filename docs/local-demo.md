# India-focused resident demo

This demo uses the existing deterministic terrain assessment, Open-Meteo rainfall and HydroSHEDS context. It is not a newly trained India flood model. Navigation is centred on India; rectangular map bounds also include neighbouring countries. Dataset coverage remains partial.

## Start with existing data

From the repository root, on a machine with Docker access and the existing `.env` configuration:

```sh
docker compose up -d --build app worker
docker compose ps
curl --fail http://localhost:8000/health/ready
```

If the Docker socket rejects your user, rerun the Docker commands with `sudo` in your own terminal and enter your password there. Open http://localhost:8000. These commands reuse the existing database volume; do not run `down -v`. No importer or migration is part of this UI change. If the database is new, follow the existing README setup instructions; source presence is not proof of imported data.

## Five-minute walkthrough

1. Select Chennai. The shortcut is a map position, not a claim of full data coverage.
2. Use 13.0827, 80.2707 with a 2 km radius. Assess and read the three plain-language sections.
3. Turn the containing/upstream basin outlines on and off. Explain that dashed outlines are context, never flood extent. Local waterways come from the OpenStreetMap base map; the HydroRIVERS dataset supplies approximate regional river context in the assessment text.
4. Expand advanced details to explain the deterministic index, source dates and limitations.
5. Keep the result for comparison. Assess 13.0500, 80.2200 with the same radius and keep it too.
6. Compare the two snapshots, including their timestamps and unavailable states. These do not rank property safety.
7. Once both snapshots are saved, print the comparison or save it as PDF. Quality warnings and provenance summaries are included. Snapshots last only for the current browser session; reloading clears them.

## Evidence from 2026-10-17

Direct terrain evaluations against the existing local FABDEM files succeeded for both Chennai coordinates at 2 km radius. Both reported 0.97 coverage ratio using N13E080_FABDEM_V1-2.tif; indices were 65 and 66. A 2 km check at Visakhapatnam (17.6868, 83.2185) returned available with 0.99 coverage ratio and index 42. Mumbai, Bengaluru and Kolkata returned outside_coverage for terrain at 2 km with the current mounted tiles; their city shortcuts remain available for exploring explicit missing-data states. The direct terrain checks verify the mounted tiles independently of Docker; the live Docker results below verify the complete pipeline for two Chennai points. The local folder contains 24 terrain tiles; that is not India-wide coverage.

## Verification and remaining limitations

- Five resident-summary and comparison tests, TypeScript compilation, Vite production build, Docker Compose configuration, and `git diff --check` passed. A local Vite preview served HTML, JavaScript and CSS with HTTP 200; that preview did not exercise the API.
- The user ran `sudo docker compose up -d --build app worker`; both images built, the app and worker started, and Docker reported the database healthy. The missing buildx plugin caused a classic-builder fallback, not a build failure.
- On 2026-10-17, the live Docker app returned `ok` for both health endpoints, served the React HTML by GET, and returned Asia HydroBASINS/HydroRIVERS imports as ready. The registry reported FABDEM missing because mounted tiles are not registered there; successful terrain results below confirm the tiles are usable at those points.
- Two live Chennai analyses at (13.0827, 80.2707) and (13.05, 80.22), both 2 km, reached `complete` with terrain, rainfall and basin context available. Terrain scores were 65 and 66 with 0.97 sampled-cell coverage. A Mumbai analysis reached `waiting_for_data`: basin and rainfall were available, while terrain was explicitly `outside_coverage`.
- The live Docker containers were built before the final source copy fix for outside-coverage and weather-unavailable job messages and the FABDEM registry hint. Rebuild `app` and `worker` once more before presenting the latest UI/copy. The root `.dockerignore` now excludes the local research virtual environment, which had inflated the classic-builder context; this build-context reduction is source-verified but has not yet been measured in Docker.
- Full API test collection is blocked by missing SQLAlchemy in the existing host virtual environment. Nineteen dependency-light tests pass, including the terrain/forecast message cases. Disposable PostGIS integration tests remain future work.
- Browser automation was unavailable: desktop/mobile appearance, keyboard flow and actual print/PDF rendering need manual verification.
- The user's screenshot showed the HydroRIVERS line crossing central Chennai streets. The live Chennai analysis returned segment 41347786: 14.92 km long, 0.26 km from the point, with 12 displayed vertices. Its raw source shape has 15 vertices; the API applies 0.002-degree simplification. The line is too coarse for a street map, so the neighbourhood UI no longer draws it. HydroRIVERS still supplies approximate regional distance context; the OpenStreetMap base map supplies visible local waterways. No source-data geometry correction is claimed. Rebuild the app image to see this UI change.
- No elevation raster overlay is introduced. Terrain remains a sampled assessment, explicitly labelled as such.
- No datasets or dependencies were downloaded, no migrations/importers were run, and no changes were committed or pushed.
