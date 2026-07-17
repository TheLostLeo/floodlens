# Phase 1 — Terrain Data Foundation

## Goal

Phase 1 prepares reliable terrain data for FloodLens.

Floodwater moves downhill and collects in low-lying drainage paths. Before FloodLens can estimate flood susceptibility, it needs an elevation dataset that is valid, correctly projected, and measured in metres.

## Step 1 — Download the raw elevation data

A Digital Elevation Model (DEM) was downloaded from OpenTopography.

Dataset used:

```text
SRTM GL1, approximately 30 metre resolution
```

The downloaded archive was extracted and the raw DEM was saved as:

```text
data/raw/dem/study_area_dem.tif
```

This file is not modified. It remains the original source dataset.

## Step 2 — Inspect the raw DEM in QGIS

The raw DEM was opened in QGIS to confirm that it contains terrain data.

Raw DEM properties:

| Property | Value |
|---|---|
| File format | GeoTIFF |
| CRS | EPSG:4326 — WGS 84 |
| Width | 6,328 pixels |
| Height | 7,898 pixels |
| Pixel size | Approximately 30 m, represented in degrees |
| NoData value | -32768 |
| Exact elevation range | -42 m to 1,147 m |

QGIS is used for visual validation. Python performs the backend calculations.

## Step 3 — Inspect the DEM with Python

A Python module was created:

```text
src/terrain/dem_reader.py
```

A script was also created:

```text
scripts/inspect_dem.py
```

The inspection code confirms:

- the DEM file exists;
- it has one raster band;
- it has a coordinate reference system;
- it has valid elevation pixels;
- its NoData values are excluded from statistics;
- its dimensions, bounds, pixel size, and elevation values are known.

This prevents FloodLens from performing calculations on an invalid input file.

## Step 4 — Reproject the DEM into metres

The raw DEM uses `EPSG:4326`, which stores location using latitude and longitude degrees.

Degrees are not suitable for slope calculations because the distance represented by one degree changes by location. FloodLens therefore reprojects the DEM into:

```text
EPSG:32644 — WGS 84 / UTM Zone 44N
```

UTM coordinates use metres, allowing terrain calculations to use real horizontal distances.

The processed DEM was created at:

```text
data/processed/study_area_dem_utm44n.tif
```

Processed DEM properties:

| Property | Value |
|---|---|
| CRS | EPSG:32644 |
| Units | metres |
| Pixel size | 30 m × 30 m |
| Width | 6,391 pixels |
| Height | 8,120 pixels |
| NoData value | -32768 |
| Elevation range | -41 m to 1,147 m |

## Step 5 — Calculate slope

The next terrain product is slope.

Slope measures how steep the ground is at every DEM pixel. It is important because water generally moves faster down steeper terrain and can collect in flatter, low-lying locations.

FloodLens will create:

```text
src/terrain/slope.py
```

It will read:

```text
data/processed/study_area_dem_utm44n.tif
```

It will produce:

```text
data/processed/slope_degrees.tif
```

### How slope is calculated

For each terrain pixel, FloodLens compares its elevation with the surrounding pixels.

It calculates:

- horizontal elevation change: `dz/dx`
- vertical elevation change: `dz/dy`
- total terrain gradient:

```text
gradient = √((dz/dx)² + (dz/dy)²)
```

Then it converts the gradient into an angle:

```text
slope in degrees = arctan(gradient) × 180 / π
```

Expected slope values:

| Slope | Meaning |
|---|---|
| 0° | completely flat |
| 0°–5° | nearly flat terrain |
| 5°–15° | gentle slope |
| 15°–30° | steep slope |
| above 30° | very steep terrain |
| 90° | vertical surface |

The slope output will preserve the same map location, dimensions, CRS, and NoData areas as the UTM DEM.

## Phase 1 completion criteria

Phase 1 is complete when these files exist and are verified in QGIS:

```text
data/raw/dem/study_area_dem.tif
data/processed/study_area_dem_utm44n.tif
data/processed/slope_degrees.tif
```

The next phase will prepare hydrology layers: depression filling, flow direction, and flow accumulation.