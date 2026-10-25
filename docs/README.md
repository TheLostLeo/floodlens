# FloodLens project handbook

This folder is the presentation and engineering reference for FloodLens. It is
written so that a teacher, teammate, future developer, or coding assistant can
understand the current system without relying on chat history.

## Start here

| Need | Read |
| --- | --- |
| One-minute project summary and presentation facts | [this file](README.md) |
| System components, networks, and trust boundaries | [architecture.md](architecture.md) |
| End-to-end request/data flow | [pipeline.md](pipeline.md) |
| Software, versions, and local deployment | [software-stack.md](software-stack.md) |
| Scientific methodology and limitations | [methodology.md](methodology.md) |
| User interface behaviour | [frontend.md](frontend.md) |
| API, worker, database, and import tooling | [backend.md](backend.md) |
| Honest numerical metrics, including the separate research ML benchmark | [metrics.md](metrics.md) |
| Completed work, roadmap, and risks | [roadmap.md](roadmap.md) |
| 80-90% completion phase checklist | [phase-80-90-completion.md](phase-80-90-completion.md) |
| Suggested slide-by-slide PPT outline | [presentation-outline.md](presentation-outline.md) |
| Dataset provenance and import rules | [data-sources.md](data-sources.md) |
| CV-ready implementation and dataset expansion plan | [cv-project-plan.md](cv-project-plan.md) |
| Complete PPT/report reference: methods, metrics, limitations, future work | [PRESENTATION-README.md](PRESENTATION-README.md) |

## Project in one minute

FloodLens is a **neighbourhood flood-awareness demonstrator**. A resident
clicks a map and selects a **1 km, 2 km, or 5 km local circle**. The system
combines:

1. **FABDEM** bare-earth elevation tiles for a deterministic local terrain
   susceptibility baseline;
2. **Open-Meteo** 48-hour precipitation forecast for rainfall context; and
3. **HydroBASINS/HydroRIVERS** for containing basin, upstream-basin, and
   nearby mapped-river context.

It does **not** claim an official warning, evacuation advice, flood depth,
flood probability, or proof that a home will flood. The selected circle is not
a watershed. A nearby river or shared basin is context only, not proof of
property-level hydraulic connectivity.

## Current local-demo status

The local Docker demo has been run successfully with Asia HydroSHEDS data and
FABDEM tiles for the Chennai-area demonstration. The browser view has produced
a completed analysis with terrain, rainfall, basin, and nearby-river context.

The local import log reported:

| Imported dataset | Coverage | Features imported |
| --- | --- | ---: |
| HydroBASINS Standard | Asia, level 8 | 28,907 basin polygons |
| HydroRIVERS | Asia | 1,428,959 river features |

These counts document the local demonstration import, not worldwide coverage
or ML training labels.

## Current measured engineering facts

| Item | Current value | Meaning |
| --- | ---: | --- |
| Supported local radii | 1, 2, 5 km | Validated input choices |
| Terrain score range | 0–100 | Relative, deterministic terrain index; **not probability** |
| Rainfall forecast horizon | 48 hours | Open-Meteo hourly precipitation request |
| Focused automated tests | 9 passed | Terrain, worker, and weather logic in the local test environment |
| Frontend production build | Passed | TypeScript + Vite bundle completed |
| Frontend npm audit | 0 vulnerabilities | At the locked dependency versions |
| Confirmed terrain example | 56/100 | Chennai-area, 5 km sample; see [metrics.md](metrics.md) |

## Important metric statement for a PPT

FloodLens does not claim F1, precision, recall, accuracy, ROC-AUC, or
calibration for its resident terrain score. It remains an explainable rule-based
baseline, so presenting a research score as app accuracy would be scientifically
wrong.

A separate real-label research benchmark now exists with an event-held-out
baseline and rainfall-LSTM comparison. It is explicitly exploratory because it
contains only two held-out flood events. See [research/results.md](../research/results.md),
[metrics.md](metrics.md), and [roadmap.md](roadmap.md).

## Safe terminology

Use these phrases:

- “relative local terrain susceptibility”
- “forecast rainfall context”
- “river-basin context”
- “neighbourhood-scale awareness”
- “deterministic explainable baseline”

Avoid these phrases:

- “predicts floods”
- “flood probability”
- “will flood”
- “official alert”
- “flood depth”
- “AI model accuracy” for the resident application

The separate research benchmark has exploratory held-out metrics, but they
must not be presented as resident-app accuracy or a local flood probability.
