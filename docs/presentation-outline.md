# PPT outline: FloodLens

Use 10–12 slides. Keep the live awareness demo separate from the research-only
ML benchmark.

## Slide 1 — Title

**FloodLens: Transparent Neighbourhood Flood Awareness**

- Student project
- Local Docker demonstration
- Subtitle: terrain, rainfall, and river-basin context

## Slide 2 — Problem

- Residents need understandable local flood context.
- Satellite visual imagery alone can confuse buildings with terrain.
- A map of a nearby river does not prove a home is hydraulically connected.

## Slide 3 — Aim and boundaries

- Aim: provide relative local terrain and hydrological context.
- Not: official warning, evacuation system, flood depth, or flood guarantee.
- The selected 1/2/5 km circle is not a watershed.

## Slide 4 — Data sources

- FABDEM: 30 m bare-earth elevation.
- HydroBASINS + HydroRIVERS: basin topology and mapped rivers.
- Open-Meteo: 48-hour hourly rainfall forecast.
- OpenStreetMap: basemap only.

## Slide 5 — Architecture

Use the diagram from [architecture.md](architecture.md):

```text
Browser -> React/FastAPI app -> PostGIS
                             <- worker -> FABDEM + Open-Meteo
Operator -> HydroBASINS/HydroRIVERS importer -> PostGIS
```

Mention Docker isolation: browser port is loopback-only; PostGIS is private.

## Slide 6 — Pipeline

1. Select point and radius.
2. Create UUID job.
3. Worker checks weather, basin context, and terrain.
4. Store results and show cards/overlays.
5. Show unavailable coverage honestly.

## Slide 7 — Terrain methodology

- 55% low relative position, 25% flatness, 20% low relief.
- Output is 0–100 relative terrain susceptibility.
- It is explainable, deterministic, and not an ML probability.

## Slide 8 — Live demo screenshot

Insert your completed browser screenshot.

Call out:

- selected local circle;
- terrain score;
- rainfall context;
- basin/upstream context;
- nearby mapped river;
- disclaimer text.

## Slide 9 — Current numerical evidence

- 28,907 HydroBASINS polygons and 1,428,959 HydroRIVERS features imported for
  the Asia local demo.
- Example FABDEM run: score 56/100, 97% coverage, 84,222 sampled cells.
- 9 focused tests passed; frontend production build passed; npm audit: 0.

## Slide 10 — Honest evaluation statement

- The resident terrain score has no F1/accuracy claim; it is not a probability.
- A separate real-label research benchmark is evaluated by whole held-out
  events, not random chips.
- Initial research result: validation-threshold baseline F1 0.468 and
  rainfall-LSTM F1 0.615 on 76 chips from two unseen events; this is
  exploratory, not app accuracy.

## Slide 11 — ML research next steps

- Add more independent labelled flood events, especially India/deployment
  geography.
- Repeat event- and geography-held-out folds.
- Verify permanent-water treatment and add terrain/basin/soil-moisture data.
- Report F1, precision, recall, PR-AUC, calibration, and failure cases per
  geography before considering any resident-facing model.

## Slide 12 — Conclusion

- Working local, data-backed awareness demonstrator.
- Explicit uncertainty is a feature, not a weakness.
- Clear path from explainable baseline to evaluated ML research.

## Likely teacher questions

| Question | Short answer |
| --- | --- |
| “Is this an AI flood predictor?” | “The live app is not: it is an explainable deterministic baseline. A separate early ML benchmark exists, but it is not deployed or a warning system.” |
| “What does 56 mean?” | “Relative terrain susceptibility, not 56% probability of flooding.” |
| “What is the LSTM F1?” | “0.615 in an exploratory two-event held-out research test, with the threshold selected on validation events; it is not the accuracy of the resident app.” |
| “Why FABDEM?” | “It is bare-earth terrain, so buildings are less likely to become false terrain barriers.” |
| “Can this cover the world?” | “The architecture supports regional imports, but coverage is only as complete as the imported datasets and tiles.” |
