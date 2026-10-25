# Completed work, roadmap, and risks

## Completed in the local demonstrator

| Area | Completed work |
| --- | --- |
| Product definition | Resident-facing awareness scope and explicit safety limits |
| Map UI | Location marker, 1/2/5 km circle, result panel, basin overlays; waterways from OpenStreetMap base map |
| API | Analysis creation, status polling, validation, guarded requeue, health checks |
| Database | PostGIS schema, jobs, context tables, provenance records, spatial queries |
| Worker | Concurrent-safe job claim, weather, basin, river, and terrain evaluation |
| Data | HydroBASINS Asia, HydroRIVERS Asia, FABDEM Chennai-area tiles imported/mounted locally |
| Terrain | Real FABDEM deterministic relative-susceptibility baseline |
| Weather | Open-Meteo 48-hour rainfall-pressure context |
| Security/reproducibility | Loopback-only app port, private database network, lockfile, clean npm audit |
| Integrity | Explicit missing/outside-coverage states; no synthetic resident data |
| Verification | Focused tests, frontend build, browser demonstration, local Docker integration |

## Near-term engineering work

1. Improve responsive UI layout and add a compact “data coverage” badge.
2. Add end-to-end API tests against a temporary PostGIS database.
3. Add database migration version tracking instead of replaying all SQL files.
4. Add import report/export with licence, checksum, date, and feature count.
5. Add structured worker logging, retry policy, and health/queue monitoring.
6. Cache map/source requests responsibly and document map-provider attribution.
7. Support more operator-imported regions while always showing actual coverage.

## Research and ML phase

The first research benchmark is complete: it uses real Sen1Floods11 labels,
historical CHIRPS rainfall, frozen whole-event splits, a gradient-boosting
baseline, and a rainfall LSTM. Its exploratory held-out results are recorded
in [the research results](../research/results.md); neither model is connected
to the resident app.

The next research phase is:

1. Add many more independent historical flood events, prioritising India and
   the intended deployment geography.
2. Verify permanent-water treatment before changing the observed-water target.
3. Add provenance-backed terrain, basin, soil-moisture, and streamflow features.
4. Repeat event- and geography-held-out folds, then report calibration and
   failure cases in addition to discrimination metrics.
5. Consider a separate pixel-level Sentinel-1 segmentation experiment only
   after the event-level protocol is mature.

## Key risks and mitigations

| Risk | Why it matters | Mitigation |
| --- | --- | --- |
| Treating the score as a probability | Could mislead residents | Clear labels and limitations; never present research F1 as resident-app accuracy |
| Partial dataset coverage | “Worldwide” data is not locally complete | Provenance gate and outside-coverage response |
| Urban drainage missing from global maps | Local flood mechanisms can differ | Explain limits; later add validated local datasets |
| Forecast failure | Weather services can be unavailable | Store unavailable state; never fabricate fallback |
| Spatial leakage in ML | Random splits inflate scores | Hold out events or regions |
| Licence restrictions | Some data is not unrestricted commercially | Record sources/licences; review before deployment |
| Large datasets | Docker builds become slow and oversized | Keep imports mounted and excluded from build context |

## Definition of success for the next ML expansion

The next milestone is successful only when it expands the independent-event
coverage, retains frozen event/region-held-out evaluation, documents each new
feature's provenance, and reports performance variation and failure cases. A
high F1 alone is not success if the test locations leak into training or the
model cannot explain its output.
