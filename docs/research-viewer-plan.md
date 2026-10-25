# Historical-event research viewer — 2026-10-18

## Design
User requested a held-out event viewer and stronger ML/deep-learning models,
and explicitly authorized local package installation and training on existing data.
Build an isolated research export, not a resident prediction provider. Preserve
the existing event split. Compare a pixel-level Extra Trees model with a compact
two-channel U-Net. Both predict observed water, including permanent water; neither
forecasts floods. Reinforcement learning has no suitable action/reward task here.

The first bounded run used a disclosed reduced grid. The follow-up keeps native
512 × 512 imagery, trains on 128 × 128 crops, and reconstructs full chips with
overlapping tiled inference. Check raster alignment and ignore nodata. Fit only
training events; select checkpoints/thresholds on validation. Save configuration,
model weights, per-chip and aggregate confusion counts, event metrics, source
references and timing. No superiority claim without measured evidence. Existing
chip classifiers are not converted into pixel masks.

## Implementation plan
- [x] Add tested portable manifest loading, raster validation, masked metrics,
  train-only normalization, and pixel features in research/src/floodlens_research.
- [x] Add a seeded Extra Trees / U-Net trainer with validation-only selection,
  bounded CPU defaults, artifacts and held-out predictions.
- [x] Add an export tool and standalone responsive research viewer with event,
  chip and model selection, four panels, legend, errors, metrics and provenance.
- [x] Run tests, train both models on existing data, export actual held-out results,
  verify the generated page and update research documentation and task records.
- [x] Add a native-resolution follow-up with augmented crops, masked BCE plus
  Dice loss, overlapping inference, immutable experiment artifacts, failure
  sorting, synchronized zoom/pan, overlay opacity and experiment history.

## Verification focus
No event leakage; no label-derived input validity; ignore invalid labels in loss
and metrics; reject misaligned rasters; explain resolution; no blank fabricated
predictions; no external assets or resident API changes; preserve dirty worktree.
