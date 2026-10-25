# FloodLens Final Project Report

## Transparent neighbourhood flood awareness and historical-event ML research

**Project status:** Complete local academic, portfolio, and research demonstrator  
**Final verified date:** 19 October 2026  
**Resident application:** `http://localhost:8000/`  
**Historical Event Lab:** `http://localhost:8000/research/`

## 1. Executive summary

FloodLens is a local web application that helps a resident understand flood-related context around a selected neighbourhood. The user chooses a location and a 1 km, 2 km, or 5 km assessment circle. The system combines bare-earth terrain, forecast rainfall, basin context, and nearby mapped-river context in a guided result page.

The project also includes a separate Historical Event Lab. This research viewer uses real labelled historical flood-event imagery to compare classical machine learning and deep learning models. It shows the Sentinel-1 radar image, verified observed-water label, predicted mask, false-water pixels, and missed-water pixels for held-out events.

FloodLens does not provide an official flood warning, evacuation advice, water-depth estimate, or property-level flood probability. The resident result remains an explainable awareness tool. Research ML results remain outside the resident assessment because the evaluation covers only two independent held-out events and labels may include permanent water.

## 2. Problem addressed

Flood information is often distributed across weather services, elevation maps, river maps, and satellite products. Each source can be misinterpreted when presented alone:

- A raw elevation surface can treat buildings or trees as terrain barriers.
- A river near a property does not prove that water can reach that property.
- A numerical score can be mistaken for an official probability.
- A dataset may cover one region while the interface appears global.
- A high ML score may hide failure on a new geography or a degenerate decision rule.

FloodLens addresses these problems by combining multiple sources, exposing provenance, and returning explicit unavailable or outside-coverage states instead of fabricated values.

## 3. Final project outcome

The completed project contains five major deliverables:

1. **Resident web application** with a guided location, assessment-area, and result workflow.
2. **Spatial analysis backend** built with FastAPI, PostgreSQL, PostGIS, and a background worker.
3. **Verified local data pipeline** using imported HydroBASINS/HydroRIVERS records, mounted FABDEM tiles, and Open-Meteo rainfall.
4. **Historical Event Lab** for held-out classification, water-mask comparison, and model failure analysis.
5. **Reproducible research pipeline** with real labels, event-held-out splits, saved metrics, predictions, model artifacts, and documented rejected experiments.

The final system demonstrates how a practical resident interface and a transparent ML research environment can coexist without turning exploratory predictions into public warnings.

## 4. Resident user experience

### Step 1: Choose a neighbourhood

The user can select a city shortcut, click on the map, or expand the exact-coordinate controls. The interface records the selected latitude and longitude while keeping technical details out of the primary flow.

### Step 2: Choose the assessment area

The user selects a 1 km, 2 km, or 5 km circle. The application clearly states that this circle is the area checked around the point. It is not a watershed or flood boundary.

### Step 3: Read the result

The result begins with scannable cards:

- **Land context:** relative terrain susceptibility and terrain-data quality.
- **Forecast rain:** rainfall provider, forecast window, and accumulated precipitation.
- **River context:** basin membership, upstream context, and nearest mapped-river distance.

Advanced sections expose the analysis identifier, dataset status, source versions, timing, technical JSON, scientific limitations, comparison snapshots, and print output.

## 5. System architecture

```text
Resident browser
    |
    v
React + TypeScript + Leaflet
    |
    | POST analysis / GET status
    v
FastAPI application
    |
    v
PostgreSQL + PostGIS <---- HydroBASINS / HydroRIVERS importer
    ^
    |
Background worker ----> FABDEM GeoTIFF tiles
    |
    +------------------> Open-Meteo forecast API

FastAPI also serves /research/ as a static Historical Event Lab.
Research training remains an offline operator workflow.
```

Docker Compose runs the application, worker, and PostGIS database. The browser accesses the app through localhost. PostgreSQL remains private to the Docker network.

The API creates UUID analysis jobs. The worker claims jobs transactionally using database locking so multiple workers cannot process the same job. The frontend polls until the status becomes complete, waiting for data, outside coverage, or failed.

## 6. Data sources

| Source | Project use | Main limitation |
| --- | --- | --- |
| FABDEM v1.2 | 30 m bare-earth elevation and local terrain factors | Does not model drains, walls, culverts, sewers, or hydraulic flow |
| HydroBASINS level 8 | Containing basin and upstream-area context | Basin membership does not prove property connectivity |
| HydroRIVERS | Nearby mapped river and distance | Generalised geometry and incomplete urban drainage representation |
| Open-Meteo | 48-hour hourly precipitation forecast | Forecast context, not an official alert |
| OpenStreetMap | Map background and location selection | Basemap only; it supplies no flood label |
| Sen1Floods11 | Historical Sentinel-1 SAR and hand-labelled observed water | Labels may contain permanent water |
| CHIRPS v2 | Historical 60-day rainfall sequences for research | Used only in offline research |

The current resident demo has imported Asia HydroBASINS and HydroRIVERS data plus mounted Chennai-area FABDEM tiles. This represents partial regional coverage rather than worldwide readiness.

## 7. Terrain methodology

The worker samples FABDEM cells inside the selected circle and derives relative elevation position, slope or flatness, local relief, valid-cell coverage, and quality flags.

```text
terrain score = 55% low relative elevation position
              + 25% flatness
              + 20% low local relief
```

| Score | Resident wording |
| ---: | --- |
| 0–33 | Lower relative terrain susceptibility |
| 34–66 | Moderate relative terrain susceptibility |
| 67–100 | Higher relative terrain susceptibility |

The score is deterministic and explainable. A score of 65 means the terrain factors place the selected area in the moderate band. It does not mean a 65% probability of flooding.

## 8. Verified resident demonstration

A live 2 km Chennai analysis completed with all primary sources available:

| Result | Verified value |
| --- | ---: |
| Relative terrain susceptibility | 65 / 100 |
| Valid terrain-cell coverage | 0.97 |
| 48-hour forecast rainfall total | 18.6 mm |
| Nearest mapped HydroRIVERS segment | 0.26 km |
| HydroBASINS polygons imported | 28,907 |
| HydroRIVERS features imported | 1,428,959 |

The output included terrain, rainfall, containing-basin, upstream-basin, and nearby-river context. Locations outside the mounted FABDEM tiles return an explicit outside-coverage state.

## 9. Research question

The research work asks two related questions:

1. **Whole-chip classification:** Does a historical 512 × 512 chip contain at least 5% labelled observed water?
2. **Pixel segmentation:** Which valid pixels match the verified observed-water mask?

The classification task compares a spatial gradient baseline with a rainfall-sequence LSTM. The segmentation task compares an Extra Trees pixel baseline with a three-scale, two-band U-Net.

## 10. Leakage-resistant evaluation

All chips belonging to one documented flood event remain in one split. This prevents nearby portions of the same event from appearing in both training and testing.

For the final seed `20261019`:

| Split | Events | Chips | Purpose |
| --- | --- | ---: | --- |
| Train | Six complete-rainfall events | 242 | Fit model weights |
| Validation | USA and Sri Lanka | 87 | Select checkpoints and thresholds |
| Test | Bolivia and Paraguay | 81 | Frozen held-out evaluation |

Spain is excluded because its historical rainfall sequence is incomplete. Missing values are not imputed. Test events do not select a checkpoint or threshold.

## 11. Models

### Spatial gradient baseline

The accepted whole-chip baseline uses leakage-free Sentinel-1 VV/VH distribution summaries, percentiles, spread, cross-polarisation features, gradient texture, and log-transformed rainfall totals. A gradient-boosting classifier learns non-linear interactions between these features.

### Rainfall LSTM

The LSTM encodes the full 60-day rainfall sequence and combines it with SAR information. Its final validation-selected threshold transferred poorly to the held-out events. The viewer retains this result because the failure is scientifically informative.

### Extra Trees segmentation

The classical segmentation baseline classifies pixels using radar values and local spatial information. It provides a strong non-neural reference for the U-Net.

### Three-scale U-Net

The U-Net trains on two radar bands with augmented 128 × 128 crops. It uses masked binary cross-entropy plus Dice loss and reconstructs 512 × 512 chips through overlapping tiled inference.

## 12. Final held-out model results

| Model | Task | F1 | IoU or PR-AUC | Additional evidence |
| --- | --- | ---: | ---: | --- |
| Spatial gradient baseline v2 | Whole-chip classification | **0.667** | PR-AUC **0.871** | Precision 0.864; ROC-AUC 0.909 |
| Rainfall LSTM | Whole-chip classification | 0.293 | PR-AUC 0.762 | Validation threshold transferred poorly |
| Extra Trees | Pixel segmentation | 0.647 | IoU 0.478 | Classical pixel baseline |
| Three-scale U-Net | Pixel segmentation | **0.725** | IoU **0.569** | Bolivia IoU 0.580; Paraguay IoU 0.566 |

Classification and segmentation are different tasks, so their F1 values should not be treated as a single ranking. The results cover two held-out events and remain exploratory.

## 13. Rejected LSTM v2 experiment

An event-balanced LSTM v2 candidate added log-transformed rainfall, derived peak and wet-day features, and leave-one-event-out development predictions. It reached an apparent F1 of 0.603, but it predicted all 81 held-out chips as positive. This produced zero true negatives and 46 false positives.

The candidate was rejected even though its F1 exceeded the original LSTM. This experiment shows why model selection must examine the confusion matrix, precision, recall, PR-AUC, ROC-AUC, per-event behaviour, and threshold stability instead of relying on F1 alone.

## 14. Historical Event Lab

The research viewer lets a user:

- choose a held-out event and image chip;
- compare radar input with the verified observed-water label;
- compare Extra Trees and U-Net masks;
- view false-water and missed-water overlays;
- rank chips by missed water, false water, or IoU;
- synchronize zoom and pan across image panels;
- change overlay opacity;
- inspect classification probabilities and thresholds;
- review immutable run details and experiment history.

The viewer makes model failure visible rather than reducing the experiment to a single headline score.

## 15. Web integration

The Docker image copies the static viewer into the application image. FastAPI mounts it at `/research/`, and the resident header links to the lab. The integration provides one coherent project while preserving a strict calculation boundary:

- Resident results use the deterministic terrain, weather, and HydroSHEDS pipeline.
- Research predictions appear only in the historical-event viewer.
- Training remains offline.
- No research model score becomes a resident warning or flood probability.

## 16. Verification completed

The completed work has been checked through source tests, builds, artifact validation, and browser use. The final verification history includes:

- 20 Python research tests passed after the classifier improvements.
- Three research-viewer JavaScript tests passed.
- Five frontend tests passed.
- TypeScript compilation and the Vite production build passed.
- Docker app, worker, and database ran successfully.
- The resident Chennai analysis completed with real mounted/imported data.
- The `/research/` viewer loaded all 81 held-out chips and switched events and models without console errors.
- Presentation package, layout, font, import, and editable-chart checks passed.

Some full API integration tests still require a disposable PostGIS test environment. Current source presence alone is not treated as proof of those unrun checks.

## 17. Limitations

- The system does not perform street-level hydraulic simulation.
- FABDEM does not model drainage capacity, blocked culverts, levees, walls, or sewer surcharge.
- HydroRIVERS geometry can be sparse or generalised in urban areas.
- A nearby river and shared basin do not prove property-level connectivity.
- Resident coverage depends on imported regions and mounted terrain tiles.
- Historical labels may include permanent water.
- The final ML evaluation contains only Bolivia and Paraguay as independent test events.
- The research models have not been calibrated or validated for operational warnings.

## 18. How to run the project

### Requirements

- Docker Desktop or Docker Engine with Compose
- Project data already downloaded and imported for the intended demo region
- FABDEM tiles mounted under the configured data path

### Start the application

```bash
docker compose up --build
```

Open:

- Resident application: `http://localhost:8000/`
- Historical Event Lab: `http://localhost:8000/research/`
- Liveness check: `http://localhost:8000/health/live`
- Readiness check: `http://localhost:8000/health/ready`

If an assessment reports outside coverage, select a location covered by the mounted terrain tiles or import the required real dataset. Do not add synthetic resident-facing fallback values.

## 19. Repository structure

```text
apps/
  api/                 FastAPI routes, schemas, repository, and worker
  web/                 React, TypeScript, Leaflet, and frontend tests
research/
  scripts/             Training and export entry points
  src/                 Feature, classification, LSTM, segmentation, and export code
  tests/               Research tests
  viewer/              Historical Event Lab static frontend and exported images
tools/                  HydroSHEDS importer and dataset-report utilities
docs/                   Architecture, methodology, metrics, pipeline, and demo guides
data/                   Local datasets and derived research data
deliverables/           Final presentation files
```

## 20. Recommended next work

1. Add more independent labelled flood events, especially India and likely deployment geographies.
2. Verify permanent-water masking and define a temporary-flood target.
3. Repeat event-held-out and geography-held-out evaluation across several folds.
4. Add calibration analysis and event-specific error reporting.
5. Validate the resident terrain interpretation against local historical reports and hydrological evidence.
6. Add disposable PostGIS end-to-end API tests.
7. Keep ML outside resident-facing decisions until independent validation supports a reviewed integration.

## 21. Conclusion

FloodLens is complete as a local academic, portfolio, and research demonstration. The resident application turns real terrain, rainfall, river, and basin data into a clear local assessment. The Historical Event Lab adds real-label classification and pixel-level deep learning evaluation with visible errors and held-out metrics.

The strongest final result is not a claim that the system can predict whether a home will flood. The strongest result is a complete, transparent pipeline that distinguishes verified data from unavailable data, deterministic awareness from experimental ML, and measured performance from unsupported real-world claims.
