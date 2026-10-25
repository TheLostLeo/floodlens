# Research run 001 — real-label benchmark results

## Unified final-project run — 2026-10-19

The resident site now links to the Historical Event Lab at `/research/`. The
lab joins whole-chip rainfall/SAR classification with pixel-level observed-water
segmentation for the same frozen held-out events. Seed `20261019` assigns
Bolivia and Paraguay to test (81 chips), USA and Sri Lanka to validation, and
six other complete-rainfall events to training. Spain remains excluded because
its historical rainfall sequence is incomplete. No test event selected a
checkpoint or threshold.

| Model | Task | Held-out F1 | Held-out IoU / PR-AUC | Threshold |
| --- | --- | ---: | ---: | ---: |
| Gradient baseline | Whole-chip classification | 0.525 | PR-AUC 0.704 | 0.47 |
| Rainfall LSTM | Whole-chip classification | 0.293 | PR-AUC 0.762 | 0.78 |
| Extra Trees | Pixel water segmentation | 0.647 | IoU 0.478 | 0.80 |
| Three-scale U-Net | Pixel water segmentation | **0.725** | **IoU 0.569** | 0.50 |

The U-Net is the strongest model for the pixel-mapping task on this fresh split:
IoU is 0.580 for Bolivia and 0.566 for Paraguay. The rainfall LSTM ranks chips
reasonably (PR-AUC 0.762) but its validation-selected threshold transfers poorly,
so its F1 is substantially below the gradient baseline. The lab displays that
failure rather than treating the LSTM as a resident flood probability.

Artifacts: `baseline-20261019T071929Z`, `lstm-20261019T071933Z`, and
`segmentation-v2-20261019T072812Z`. These remain exploratory results from two
held-out events and do not establish resident-app accuracy.

### Classification improvement follow-up

A spatial-summary gradient candidate added leakage-free VV/VH distribution,
cross-polarisation and gradient-texture features plus log-transformed rainfall.
With its threshold selected only on validation events, it improved held-out F1
from 0.525 to **0.667**, precision to **0.864**, PR-AUC to **0.871**, and
ROC-AUC to **0.909**. Artifact: `baseline-v2-20261019T075942Z`; this is the
baseline selected by `classification-current.json` for the lab.

An event-balanced LSTM candidate used log-transformed rainfall, derived peak/
wet-day features and leave-one-event-out development predictions. Its apparent
F1 rose to 0.603, but the selected threshold predicted every held-out chip as
positive (zero true negatives). It was rejected and is not selected for the
lab. Artifact: `lstm-v2-20261019T075653Z`. This failure shows why F1 alone is
not sufficient evidence of a useful model.

**Run date:** 2026-09-22 Asia/Kolkata  
**Status:** completed research experiment; not connected to the resident-facing
FloodLens output.

## Question tested

Can observed water/no-water chips from documented flood events be classified
from two Sentinel-1 SAR summaries and 60 days of antecedent CHIRPS daily
rainfall, when entire flood events—not randomly selected chips—are held out?

This is flood-event mapping research. It is not a property-flood prediction,
depth prediction, official alert, or a validation of the resident terrain score.

## Data actually used

| Item | Result |
| --- | ---: |
| Downloaded Sen1Floods11 v1.1 S1 / label / JRC reference files | 446 paired files per layer |
| Usable labelled chips after validation | 440 |
| Excluded chips | 6 |
| Initial independent documented events | 11 |
| Events with complete 60-day CHIRPS sequence | 10 |
| Chips used by the rainfall experiments | 410 |
| Positive observed-water chips | 169 of 440 before rainfall exclusion |

Five excluded chips had no valid `0`/`1` hand-label pixels; one had no finite
Sentinel-1 values over valid labels. The Spain event was excluded from the
rainfall experiments because one historical CHIRPS source pixel was invalid.
No values were imputed.

The target is `has_observed_water`: a chip contains at least 5% labelled water
during a documented flood event. It is **not** claimed to be purely temporary
floodwater. The downloaded JRC reference is retained for future audit because
its exact use for separating permanent water must be verified before changing
the target.

## Frozen evaluation design

| Split | Independent events | Chips |
| --- | --- | ---: |
| Train | Bolivia, Sri Lanka, India, Cambodia, Nigeria, Somalia | 199 |
| Validation | USA, Paraguay | 135 |
| Test — unseen throughout model fitting | Ghana, Pakistan | 76 |

All chips belonging to an event stay in one split. This prevents the common
mistake of training on neighbouring parts of the same flood event and then
claiming a high random-split accuracy.

## Models and held-out test results

| Metric on the same 76 unseen chips | Gradient-boosting baseline | Rainfall LSTM |
| --- | ---: | ---: |
| Validation-selected threshold | 0.30 | 0.61 |
| F1 | 0.468 | 0.615 |
| Precision | 0.355 | 0.800 |
| Recall | 0.688 | 0.500 |
| PR-AUC | 0.664 | 0.658 |
| ROC-AUC | 0.787 | 0.746 |
| False positives | 20 | 2 |
| False negatives | 5 | 8 |

The baseline uses mean Sentinel-1 VV/VH plus 1, 3, 7, 14, 30, and 60-day
antecedent CHIRPS rainfall totals. The LSTM encodes the complete 60-day rainfall
sequence and combines it with the same mean VV/VH inputs.

Each threshold was selected on validation events only by maximising validation
F1, then fixed before the test events were scored. The LSTM has higher F1 and
far fewer false positives, but more false negatives and lower PR-AUC/ROC-AUC.
With only **two independent held-out events**, it is not scientifically valid
to call it the better model. The correct PPT claim is: *“A real-label,
event-held-out baseline and LSTM comparison is implemented; the preliminary
LSTM F1 is 0.615, and it needs more independent events.”*

## Reproducibility evidence

The run generated ignored local artifacts so the repository does not store the
large data or model binaries:

- `research/artifacts/baseline-20260922T000627Z/metrics.json`
- `research/artifacts/baseline-20260922T000627Z/predictions.csv`
- `research/artifacts/lstm-20260922T000631Z/metrics.json`
- `research/artifacts/lstm-20260922T000631Z/predictions.csv`
- `data/research/derived/event_split.json`
- `data/research/derived/feature_report.json`

The research unit tests passed (`4 passed`) and `pip check` reported no broken
requirements. The model run was CPU-only with PyTorch 2.14.0+cpu.

## What may be said in the project presentation

- “We used real labelled historical flood-event imagery, not synthetic labels.”
- “We held out entire events, so the test set contains floods unseen during
  training.”
- “The preliminary held-out LSTM F1 was 0.615 over 76 chips from two events;
  the threshold was selected from validation events only.”
- “This is an early research benchmark, not a resident warning or flood
  probability.”

## Next required work before any resident-facing ML use

1. Add substantially more independent flood events, ideally from India and the
   eventual deployment geography.
2. Verify and apply permanent-water masking for the target definition.
3. Add local terrain, basin, soil-moisture, and streamflow features with
   provenance; keep historical features separate from live forecasts.
4. Repeat event- and geography-held-out evaluation across several folds,
   including calibration and failure-case review.
5. Keep the trained models out of the resident API until those tests are
   complete and the claim is reviewed.

## Pixel-level segmentation run — 2026-10-18

A separate CPU experiment now compares observed-water masks at a disclosed
64 × 64 research resolution. It preserves the same frozen event split and
exports only Ghana and Pakistan test predictions to the historical-event
viewer. Thresholds were selected on validation events.

| Model | Threshold | Test precision | Test recall | Test F1 | Test IoU |
| --- | ---: | ---: | ---: | ---: | ---: |
| Extra Trees pixel baseline | 0.80 | 0.518 | 0.443 | 0.478 | 0.314 |
| Compact two-band U-Net | 0.65 | 0.523 | 0.453 | 0.485 | 0.321 |

The U-Net is slightly higher on these aggregate held-out metrics, but the
difference is small and performance differs materially by event. Its IoU is
0.394 on Ghana and 0.255 on Pakistan. This is evidence that more independent
events, permanent-water separation, stronger architecture comparison, and
geography-held-out folds are still required. It is not resident-app accuracy.

The static viewer under `research/viewer/` shows radar input, reference label,
prediction, false-water pixels, and missed-water pixels for all 76 test chips.
Reproducible metrics and weights are written to the ignored
`research/artifacts/segmentation-latest/` directory.

## Native-resolution segmentation run — 2026-10-18

The follow-up run keeps the 512 × 512 source grid. It trains a three-scale
two-band U-Net on augmented 128 × 128 crops with masked BCE plus Dice loss and
reconstructs test chips from overlapping tiles. The checkpoint and threshold
were selected on validation-event center crops. Extra Trees remains the
classical comparison and is evaluated on the same valid test pixels.

| Model | Threshold | Test precision | Test recall | Test F1 | Test IoU |
| --- | ---: | ---: | ---: | ---: | ---: |
| Extra Trees pixel baseline | 0.80 | 0.472 | 0.436 | 0.453 | 0.293 |
| Three-scale two-band U-Net | 0.60 | 0.524 | 0.465 | 0.493 | 0.327 |

The U-Net reached IoU 0.392 on Ghana and 0.270 on Pakistan. This modestly
improves the earlier reduced-grid U-Net result while exposing substantial
missed water and geographic variation. The viewer now keeps both predictions
side by side at native resolution, supports synchronized zoom and pan, adjusts
overlay opacity, and can rank chips by missed water, false water, or worst IoU.

Artifact: `research/artifacts/segmentation-v2-20261018T163852Z/`. The pointer
`research/artifacts/segmentation-current.json` selects it for export.

This is an exploratory iteration, not a clean final benchmark: the follow-up
architecture and training duration were chosen after inspecting the earlier
Ghana/Pakistan result. A future performance claim requires a newly untouched
event/geography holdout or nested cross-validation. The result remains observed
water segmentation research and is not connected to the resident application.
