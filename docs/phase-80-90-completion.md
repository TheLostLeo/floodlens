# FloodLens 80-90% Completion Phase

This phase turns the working local demonstrator into a defensible project
submission/demo package. It should improve confidence, presentation quality,
and handoff clarity without changing the scientific boundary of the product.

FloodLens remains a neighbourhood-scale awareness tool. This phase must not
turn the deterministic terrain score or the research ML benchmark into an
official warning, flood probability, depth estimate, or property-level claim.

## Current baseline

- The authoritative app lives at the repository root under `apps/`, `tools/`,
  `compose.yaml`, `docs/`, and `research/`.
- The local demonstrator has reached Milestone 5 behavior with real FABDEM,
  HydroBASINS, HydroRIVERS, and Open-Meteo when the operator supplies coverage.
- Research ML is isolated under `research/` and has exploratory real-label,
  event-held-out metrics. It is not connected to the resident-facing API.
- The older `.codex/` notes that refer to `floodlens_next/` are historical and
  should not override current source or `.agent/` state.

## Phase goals

1. Make the current demo easy to run, explain, and defend.
2. Add enough verification evidence that the project is credible as a local
   demonstrator, not just a source tree.
3. Close the highest-value engineering gaps that do not require new datasets,
   system installs, migrations against user data, or public deployment.
4. Preserve all safety wording around partial coverage, unavailable data, and
   research-only ML.

## Work lanes

| Lane | Outcome | Acceptance check |
| --- | --- | --- |
| Demo script | A repeatable Chennai/local demo path with exact inputs and expected UI states | A presenter can run the same location/radius and explain every card shown |
| Verification pack | A short record of tests, build commands, Docker/browser checks, and known blockers | Every claim in the PPT has either a command result, source file, or documented local run |
| UI hardening | Clearer coverage/provenance status and mobile-safe result layout | Missing data, outside coverage, complete, and failed states stay readable on narrow screens |
| Backend confidence | More API/database integration coverage where practical | Create, poll, requeue, and unavailable/outside-coverage behavior are tested against realistic persistence |
| Import evidence | Operator import reports for HydroBASINS/HydroRIVERS/FABDEM coverage | Feature counts, coverage region, source versions, checksums, and dates are documented |
| Research boundary | Presentation wording keeps ML exploratory and isolated | No resident-app screen or claim uses research F1 as live risk accuracy |

## Recommended sequence

1. Freeze the demo claim set:
   - exact demo location and radius;
   - imported region and FABDEM tile coverage;
   - source versions and local run date;
   - screenshots or notes for complete, waiting, and outside-coverage states.
2. Add/refresh automated evidence:
   - app-focused Python tests;
   - research unit tests;
   - TypeScript compile and Vite production build;
   - Docker Compose config and local browser smoke test when the user can run
     Docker.
3. Add the final UX polish:
   - a compact data coverage/provenance badge;
   - clearer copy for `waiting_for_data` and `outside_coverage`;
   - mobile layout checks for result cards and map controls.
4. Add API/database confidence:
   - disposable PostGIS integration test plan or implementation;
   - migration/version tracking note if implementation is deferred.
5. Finalize presentation materials:
   - turn `docs/presentation-outline.md` into the final slide deck;
   - keep `docs/PRESENTATION-README.md` as the source of truth for claims;
   - include the limitations slide before ML results.

## Verification snapshot from phase start

Run on 2026-10-08 in `/storage/projects/floodlens`:

| Check | Result |
| --- | --- |
| `env PYTHONPATH=apps/api .venv/bin/python -m pytest apps/api/tests/test_domain.py apps/api/tests/test_schemas.py apps/api/tests/test_weather.py apps/api/tests/test_terrain.py apps/api/tests/test_worker.py` | 15 passed, 3 Rasterio pending-deprecation warnings |
| `env PYTHONPATH=research/src .venv-research/bin/python -m pytest research/tests` | 4 passed |
| `node node_modules/typescript/bin/tsc -b` from `apps/web` | passed |
| `node node_modules/vite/bin/vite.js build` from `apps/web` | passed; built `dist/` in 304 ms |

The plain `python -m pytest` command did not work because the system Python has
no `pytest`. The plain `npm run build` command did not work because the local
`node_modules/.bin/tsc` shim was not executable in this checkout. The direct
`node` commands above avoid changing local file permissions.

## Out of scope for this phase unless separately authorized

- Downloading new datasets.
- Installing system packages.
- Running migrations against user data.
- Connecting research ML to the resident API.
- Public deployment, publishing, committing, pushing, or deleting data.

