# FloodLens research ML pipeline

This directory is deliberately **not** part of the resident-facing Docker
application. It is a reproducible research workspace for a flood-mapping
experiment. No model in this directory is an official warning, a flood-depth
predictor, or automatically shown in FloodLens.

## Research question

Can a model map water observed during documented flood events from Sentinel-1
SAR imagery, and does adding an antecedent historical-rainfall sequence improve
an event-held-out experiment?

There are two comparable experiments:

1. `train_baseline.py` — an explainable tabular gradient-boosting baseline
   using per-chip Sentinel-1 summaries and antecedent CHIRPS rainfall totals.
2. `train_lstm.py` — a small LSTM that encodes a 60-day rainfall sequence and
   combines it with the same static Sentinel-1 summaries.

The labels are observed water/no-water in a documented flood-event benchmark.
They are **not** property-flood labels. The included JRC permanent-water layer
is retained for later, verified separation of permanent water; it is not
silently assumed to mean temporary flood water.

## Data sources

| Input | Purpose | Local destination |
| --- | --- | --- |
| Sen1Floods11 v1.1 hand-labelled subset | Sentinel-1 VV/VH chips and water/no-water quality-control labels | `data/research/sen1floods11/` |
| Sen1Floods11 event metadata | Event dates and geometry | `data/research/sen1floods11/v1.1/Sen1Floods11_Metadata.geojson` |
| CHIRPS v2 daily | 60-day antecedent precipitation sequence at each event centroid | `data/research/chirps/chirps_event_sequences.csv` |

The Sen1Floods11 project documents two SAR bands, hand-labelled values `-1`,
`0`, and `1`, WGS84 10 m chips, and event dates in its metadata. CHIRPS is a
daily precipitation product; its values are millimetres per day. Record source
and licence information in your report before public distribution.

## What you will run

All commands are from the repository root. These commands do not touch Docker,
PostGIS, or the resident application.

### 1. Create an isolated Python environment

```bash
python -m venv .venv-research
source .venv-research/bin/activate
python -m pip install --upgrade pip
python -m pip install -r research/requirements.txt
python -m pip install --index-url https://download.pytorch.org/whl/cpu 'torch==2.14.0+cpu'
```

The CPU-only PyTorch build is intentional for the first local run. It avoids
downloading several gigabytes of CUDA libraries and the LSTM still trains
correctly on a normal laptop.

### 2. Download the labelled subset in parallel

```bash
bash research/scripts/download_sen1floods11.sh
```

The script downloads only `S1Hand`, `LabelHand`, `JRCWaterHand`, and the event
metadata. It prefers `gcloud` or `gsutil` if installed; otherwise it uses the
available Arch `aria2c` command with eight parallel, resumable HTTP connections.
It does not download Sentinel-2 imagery or checkpoints.

### 3. Download daily rainfall sequences

```bash
python research/scripts/download_chirps.py --days 60 --workers 4
```

This streams one pixel from each original CHIRPS daily Cloud-Optimized GeoTIFF
for every event day. It does not download all global CHIRPS rasters. Failed or
incomplete event sequences are recorded and excluded later; they are never
filled with invented rainfall.

### 4. Build the reproducible dataset manifest and split

```bash
python research/scripts/build_manifest.py
python research/scripts/create_event_split.py --seed 42 --test-events 2 --validation-events 2
python research/scripts/build_feature_table.py --days 60
```

The split is by **event**, not random chips. Events with incomplete historical
rainfall are excluded before the split; every included chip from a held-out
flood event remains completely unseen during training.

### 5. Train and evaluate the baseline first

```bash
python research/scripts/train_baseline.py --seed 42
```

### 6. Train the rainfall LSTM only after the baseline completes

```bash
python research/scripts/train_lstm.py --seed 42 --epochs 40
```

Both commands write timestamped metrics, held-out predictions, configuration,
and errors under `research/artifacts/`. Do not copy a number into a presentation
until the relevant artifact reports a completed test run.

### Optional source checks

```bash
PYTHONPATH=research/src pytest research/tests -q
```

## Evaluation rules

- Primary split: held-out flood events, never a random chip split.
- Primary metrics: F1, precision, recall, PR-AUC, ROC-AUC, confusion matrix,
  and (for mapping) positive-pixel IoU when a pixel model is later added.
- Select a classification threshold from validation events only, then freeze it
  before evaluating held-out test events.
- Report the number of independent train/validation/test events beside every
  metric. Hundreds of chips from one event are not hundreds of independent
  floods.
- Compare the LSTM to the baseline; do not call the LSTM better merely because
  it is more complex.
- Treat the small set of benchmark events as an exploratory study. It is not a
  sufficient basis for a resident warning system.

## Next research upgrade

The first pipeline is a small, CPU-friendly tabular/LSTM comparison so it can
run on your PC. After it has a saved event-held-out evaluation, add a U-Net
Sentinel-1 segmentation experiment for pixel-level flood mapping. That is a
different task from rainfall forecasting and should be reported separately.

## Historical-event segmentation viewer

The repository includes two pixel-level observed-water experiments and an
offline viewer for held-out events:

The viewer is also served by the combined FloodLens application at
`http://localhost:8000/research/`. It displays whole-chip gradient/LSTM results
beside Extra Trees/U-Net pixel masks, while keeping both tasks and their
thresholds distinct.

- Extra Trees is a classical per-pixel baseline using VV, VH, their
  difference, and normalized pixel position.
- A three-scale two-band U-Net adds spatial context through convolutional
  layers, batch normalization, masked BCE plus Dice loss, and rotation/flip
  augmentation.

Both models preserve the frozen event split. Thresholds are selected on
validation events; Ghana and Pakistan remain test-only. They map observed
water in the Sen1Floods11 labels, which may include permanent water. They do
not forecast a future flood.

```powershell
.venv-segmentation\Scripts\python.exe research/scripts/train_segmentation_v2.py
.venv-segmentation\Scripts\python.exe research/scripts/export_research_viewer.py
cd research/viewer
python -m http.server 8090
```

Open `http://localhost:8090` to compare radar input, verified label, predicted
mask, and error overlays for every held-out chip. The current experiment trains
on augmented 128 × 128 native-resolution crops and reconstructs each 512 × 512
test chip with overlapping tiled inference. The viewer compares both models,
sorts chips by failure type, synchronizes zoom/pan, and records the active run
plus experiment history. Generated weights and prediction arrays stay under
ignored `research/artifacts/`; `segmentation-current.json` selects the exported
run without overwriting earlier experiments.

## Latest completed run

The real-data run, frozen split, held-out metrics, and limitations are recorded
in [results.md](results.md). Keep its research boundary when presenting the
numbers.
