# Frontend details

## Purpose

The frontend is a resident-facing, single-page React application served from
the same container and origin as FastAPI. It has no separate public frontend
server and no separate browser port.

## Main interaction flow

1. User clicks the OpenStreetMap basemap to select a point.
2. Leaflet places a blue marker using Vite-bundled marker assets.
3. User selects a local 1 km, 2 km, or 5 km radius.
4. The map shows a teal circle representing the selected local area.
5. User presses **Analyse this area**.
6. The UI creates an analysis job and polls it every **1.5 seconds** until it
   reaches `waiting_for_data`, `complete`, or `failed`.
7. Result cards show terrain, rainfall, and basin context where available.

## UI elements

| Element | Behaviour | Integrity rule |
| --- | --- | --- |
| Location marker | Shows the selected coordinates visually | It does not imply an address-level result. |
| Radius circle | 1/2/5 km local assessment area | It is explicitly not a watershed. |
| Status/progress | Shows queued/running/waiting/complete/failed progress | Progress is job state, not prediction confidence. |
| Terrain card | Score, label, elevation, relief, slope, factor explanation | Rendered only with mounted FABDEM coverage. |
| Rainfall card | Pressure, total, max hourly rain, wet hours | Not an official weather or flood alert. |
| Basin card | Basin level, upstream area, nearby river distance | Context only; no claimed hydraulic connectivity. |
| Map overlays | Basin polygon and upstream geometry | Display boundaries are simplified for browser performance. Local waterways come from the OpenStreetMap base map; HydroRIVERS remains approximate regional context in assessment text. |
| Requeue button | Available only for `waiting_for_data` | Lets the user check again after an operator imports data. |

## Responsive behaviour

- Desktop: fixed left information panel (320–420 px) and full-height map.
- Screens below 750 px wide: panel becomes the upper 48% of the viewport;
  map occupies the lower 52%.
- The UI uses readable cards, explicit limitations, and no colour-only status
  communication.

## API integration

All calls use same-origin relative paths, so `apiBase` is empty:

| Action | Request |
| --- | --- |
| Start analysis | `POST /api/analyses` |
| Read state/result | `GET /api/analyses/{id}` |
| Retry after import | `POST /api/analyses/{id}/requeue` |

The current frontend accepts no data-file paths, no database credentials, and
no model tuning parameters from residents.

## Known presentation improvement

For a PPT screenshot, use browser zoom 100% and a desktop-width window. The
application works at smaller widths, but a full-screen map can make the left
panel appear tiny in a screenshot taken at low browser zoom.
