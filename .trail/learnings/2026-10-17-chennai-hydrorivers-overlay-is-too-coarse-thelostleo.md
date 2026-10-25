---
title: Chennai HydroRIVERS overlay is too coarse for a street map
author: TheLostLeo
date: 2026-10-17
branch: main
touches:
  - ".dockerignore"
  - AGENTS.md
  - README.md
  - apps/api/app/main.py
  - apps/api/app/repository.py
  - apps/api/app/schemas.py
  - apps/api/app/worker.py
  - apps/api/tests/test_schemas.py
  - apps/api/tests/test_worker.py
  - apps/web/index.html
---

## Decided
The resident map omits HydroRIVERS line geometry at street scale. It keeps approximate regional river distance in assessment text and uses OpenStreetMap base tiles for visible waterways.
## Tried and ruled out
The screenshot line matches live API segment 41347786 near central Chennai. Display simplification reduces the source from 15 to 12 vertices over 14.92 km, so removing simplification alone cannot make it a street-accurate line.
## Watch out
A future explicit waterway overlay needs higher-resolution validated source geometry and coverage checks. Do not present HydroRIVERS proximity as property-level connectivity or street waterlogging.
