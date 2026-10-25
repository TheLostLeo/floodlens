# Metrics, numerical evidence, and ML evaluation plan

## What is measured today

The resident-facing product is a rule-based terrain baseline. It has no local
validated flood-outcome model, so research F1 and ROC-AUC values must never be
shown as the accuracy of its terrain score. A separate real-label research
benchmark is recorded below. The following are real current engineering facts.

| Category | Metric | Value | Interpretation |
| --- | --- | ---: | --- |
| Input | Allowed local radii | 1, 2, 5 km | Fixed validated options |
| Terrain algorithm | Score range | 0–100 | Relative susceptibility index, not probability |
| Terrain algorithm | Weights | 55% / 25% / 20% | Low position / flatness / low relief |
| Terrain labels | Lower/moderate/higher bands | 0–33 / 34–66 / 67–100 | Display categories only |
| Weather | Forecast horizon | 48 hours | Hourly Open-Meteo precipitation |
| Weather | High-pressure trigger | >=50 mm total or >=20 mm/hour | Contextual rule, not alert threshold |
| Integration data | Asia basins imported | 28,907 | Local import log count |
| Integration data | Asia rivers imported | 1,428,959 | Local import log count |
| Tests | Focused Python tests | 9 passed | Terrain, worker, weather logic |
| Build | TypeScript/Vite production build | Passed | Bundle compilation check |
| Supply chain | npm audit | 0 vulnerabilities | Locked frontend dependencies |

## Reproducible terrain demonstration result

A direct local calculation at latitude **12.84261968003193**, longitude
**80.15449047088624**, radius **5 km**, using the mounted
`N12E080_FABDEM_V1-2.tif` tile produced:

| Output | Value |
| --- | ---: |
| Terrain score | 56 / 100 |
| Display label | Moderate relative terrain susceptibility |
| Point elevation | 18.55 m |
| Local 10th–90th percentile relief | 25.15 m |
| Median slope | 0.72% |
| Valid terrain cells | 84,222 |
| Terrain coverage ratio | 0.97 (97%) |

This is a functionality check using real terrain data. It is **not** a flood
prediction accuracy measurement.

## Metrics deliberately not reported for the resident product

| ML metric | Current value | Why |
| --- | --- | --- |
| Accuracy | Not available | The resident product has no trained local flood classifier |
| Precision | Not available | No resident-facing predicted flood class |
| Recall | Not available | No resident-facing predicted flood class |
| F1 score | Not available | Research F1 does not validate the resident terrain score |
| ROC-AUC / PR-AUC | Not available | Research probabilities are not resident predictions |
| Brier score / calibration | Not available | Current score is not a probability |
| Flood-depth RMSE | Not available | The project does not predict flood depth |

The correct viva answer is: “We do not fabricate app accuracy. The resident
system is an explainable baseline; the separate research benchmark reports
event-held-out metrics with explicit limitations.”

## Future ML evaluation protocol

1. Obtain legally usable historical flood extent labels with event date and
   location.
2. Sample positive and negative locations while avoiding spatial duplicates.
3. Join predictors available before or during each event: terrain, basin,
   observed/forecast rainfall, season, and optional urban features.
4. Split by **whole event** or **geographic region**. Never randomly split
   neighbouring pixels between train and test.
5. Train a deterministic baseline and an explainable gradient-boosted
   classifier.
6. Select classification threshold on validation data only.
7. Report held-out precision, recall, F1, PR-AUC, ROC-AUC, confusion matrix,
   calibration/Brier score, coverage, and uncertainty by region/event.
8. Report failure cases, not only the best score.

## Formulas for later PPT use

```text
precision = TP / (TP + FP)
recall    = TP / (TP + FN)
F1        = 2 × precision × recall / (precision + recall)
accuracy  = (TP + TN) / (TP + TN + FP + FN)
```

Use these formulas in the methodology slide. Attribute completed numbers only
to the research benchmark and include its event-held-out limitation.
## Completed research benchmark (2026-09-22)

FloodLens now has a **research-only** real-label benchmark. It remains separate
from the resident-facing terrain/rainfall/basin awareness output.

- Dataset: 440 validated Sen1Floods11 v1.1 hand-labelled chips from 11
  documented events; 410 chips from 10 events were eligible after the
  historical-rainfall completeness check.
- Evaluation: entire events were held out. Ghana and Pakistan (76 chips) were
  not used for fitting; this is an exploratory two-event test, not a general
  performance claim.
- Thresholds were selected from validation events only before testing. Baseline
  held-out F1: **0.468** at threshold 0.30; rainfall-LSTM held-out F1:
  **0.615** at threshold 0.61.
- The LSTM did not dominate every metric (baseline PR-AUC 0.664 / ROC-AUC 0.787
  versus LSTM PR-AUC 0.658 / ROC-AUC 0.746), so neither is declared superior.

See [research/results.md](../research/results.md) for the exact feature set,
confusion matrices, split, artifacts, and limitations. These values must never
be presented as the accuracy of the resident web application, a flood
probability, an official warning, or a property-level prediction.
