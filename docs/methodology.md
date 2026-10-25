# Methodology and scientific integrity

## Research question

**Can openly available terrain, forecast rainfall, and river-basin data be
combined into a transparent neighbourhood-scale flood-awareness tool while
showing uncertainty and missing coverage honestly?**

The current answer is a deterministic baseline, not trained machine learning.

## Current deterministic terrain method

For a selected 1, 2, or 5 km circle, the worker samples real FABDEM bare-earth
elevation cells. It calculates:

- selected-point elevation;
- 10th and 90th percentile local elevation (`p10`, `p90`);
- local relief = `p90 - p10`;
- median slope percentage; and
- data coverage ratio within the selected circle.

The relative terrain score is:

```text
score = 100 × (0.55 × low_position + 0.25 × flatness + 0.20 × low_relief)
```

Where:

```text
low_position = 1 - clamp((point_elevation - p10) / max(p90 - p10, 0.1), 0, 1)
flatness     = 1 - clamp(median_slope_percent / 5, 0, 1)
low_relief   = 1 - clamp(local_relief_m / 25, 0, 1)
```

The weights are an explainable design choice: 55% relative low position, 25%
flatness, and 20% low relief. They are **not learned weights** and should not
be described as trained AI.

| Score band | Display label |
| --- | --- |
| 0–33 | Lower relative terrain susceptibility |
| 34–66 | Moderate relative terrain susceptibility |
| 67–100 | Higher relative terrain susceptibility |

The score is not a probability. For example, 56/100 does not mean “56% chance
of flooding.”

## Rainfall method

The worker requests hourly precipitation for the next two days (48 hours) from
Open-Meteo in GMT. It calculates total forecast precipitation, maximum hourly
precipitation, and wet-hour count.

| Rainfall pressure | Rule |
| --- | --- |
| None | Total rain = 0 mm |
| Low | Total rain > 0 mm and below moderate thresholds |
| Moderate | Total >= 20 mm **or** maximum hourly >= 10 mm |
| High | Total >= 50 mm **or** maximum hourly >= 20 mm |

Rainfall pressure is context only. It does not account for tide, drains, soil
moisture, reservoir operation, blocked channels, or response authorities.

## Basin and river method

1. Confirm that provenance records say the regional HydroBASINS and
   HydroRIVERS imports are ready.
2. Use PostGIS to find the highest available basin level containing the point.
3. Follow `NEXT_DOWN` links in reverse to identify upstream sub-basins.
4. Sum upstream sub-basin area and simplify geometry for display.
5. Find the nearest mapped river segment intersecting the containing sub-basin.

The service intentionally never says “this river will flood this home.” Urban
drains, culverts, embankments, roads, walls, and local flow paths are not fully
represented by global datasets.

## Why FABDEM is used

FABDEM is a bare-earth elevation product. It is appropriate for the current
terrain baseline because buildings and vegetation have been reduced. A raw
digital surface model such as Copernicus GLO-30 would treat buildings and trees
as terrain barriers and can create false local flow patterns.

## Research ML methodology

The first research-only ML benchmark is now complete with real, time-stamped
Sen1Floods11 flood-event labels and historical CHIRPS rainfall. It compares an
explainable gradient-boosting classifier with a rainfall-sequence LSTM. This
does not validate or alter the deterministic resident terrain baseline.

The initial models use per-chip Sentinel-1 VV/VH summaries and either
antecedent rainfall totals or the full 60-day daily-rainfall sequence. Local
terrain, basin, soil-moisture, and streamflow predictors remain future work and
must have source provenance before use.

Candidate features include terrain position, slope, local relief, upstream
area, river distance/context, forecast or observed rainfall, season, and
land-cover/urban features where lawful and available.

The dataset must be split by **event or geography**, not random pixels. Random
splits leak nearby observations into training and test sets and give unrealistically
high scores. The completed exploratory benchmark holds out Ghana and Pakistan
entirely; its small two-event test requires expansion before any model choice.
See [the research results](../research/results.md) for the measured values.
