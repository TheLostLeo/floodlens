# FloodLens interface

This documents the current resident interface in `apps/web/src/main.tsx` and
`apps/web/src/styles.css`, alongside the product commitments in `PRODUCT.md`.
The user selected a calm civic-service appearance with expandable technical
evidence. No image composition has been approved. Browser visual QA was
unavailable; the conventions below are verified from source, not screenshots.

## Visual language

Warm off-white canvas (`#f4f6f3`), white surfaces, dark green ink (`#203b39`),
muted text (`#536763`), green actions (`#126656`), and fine borders (`#d5dfd9`).
Panels use 12px corners without decorative shadows. Buttons use 7px corners,
inputs 6px, and notices 8px. Error text/background are `#8d2626`/`#fff1ee`;
warning text/background are `#785008`/`#fff5df`. States always have text.

The font stack is `system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI",
sans-serif`, keeping the local demonstration free of a font-download dependency.
Body text is 15px with 1.6 line height. The lead heading scales from 26px to
38px; section headings are 20px and subsection headings 17px. Supporting
labels and metadata use 12–14px. Coordinates and metrics use tabular numerals.
The machine-readable token inventory is `.impeccable/design.json`.

## Composition and interaction

A white masthead identifies the local demo and region. A brief introduction
leads to a location panel beside the map: city shortcut, explicit coordinates,
1/2/5 km radius, primary assessment action, and expandable coverage information.
City shortcuts locate the map and do not establish dataset coverage.

The map shows a green assessment circle. Optional layers include a blue
generalised river segment, purple dashed containing basin, and brown dashed upstream basins; all start hidden. Basin geometry is unfilled;
the assessment circle has 0.04 fill opacity. Layer toggles and explanatory text
keep the assessment area distinct from drainage context and flood extent.
Terrain is described in results, not rendered as a flood overlay.

The empty state names the three data sources. Results proceed through terrain,
forecast rainfall, and river/basin context, followed by a plain-language limit
notice. Sources, forecast period, terrain version, and quality flags remain
outside the advanced disclosure. Advanced details contain the index, factors,
limitations, analysis identifier, and provenance. Two in-session snapshots can
be compared; a third replaces the oldest. Different radii receive a warning.

Queued/running analyses show progress; complete, partial (`waiting_for_data`),
and failed states have explicit labels. Missing/outside-coverage results remain
unavailable. Connection, coordinate-validation, and map-tile errors have visible
messages; coverage connectivity failure is not treated as missing data. The
partial state offers a recheck. Controls use labels and fieldsets, pressed state
for radius selection, a 3px blue focus outline, and normally 44px minimum control
height. Native disclosures and live result/error announcements are implemented;
keyboard and assistive-technology behavior has not been browser-verified.

## Responsive and print conventions

The content container is at most 1368px wide with 24px horizontal padding. The
workspace uses a 320px location column and a flexible map with a 24px gap.
At 850px and below this becomes 280px/16px, with stacked map headings. At 640px
and below the location panel and map stack, comparison becomes one column,
actions span the width, and page padding becomes 16px. Map heights are 420px
normally, 450px at the intermediate breakpoint, and 340px on mobile. Main
assessment readings use two columns from 1100px; basin context spans both.

Printing selects either the current assessment or saved comparison. It hides
map/input controls, introductory UI, actions, and advanced disclosures; it keeps
readable findings, visible source/quality information, and limitations. Print
uses 11pt body text, borderless assessment containers, and page breaks before
comparison entries. Actual browser pagination and PDF appearance remain unverified.

## Product boundaries

FloodLens provides neighbourhood-scale awareness, not official warnings,
evacuation guidance, live waterlogging, exact depth, property safety, or flood
probability. A terrain index is not a probability. Basin membership and nearby
rivers do not prove hydraulic connectivity to a home. Coverage is limited to
imported real datasets and mounted terrain tiles; no synthetic resident-facing
fallback or research-model accuracy claim belongs in this interface.
