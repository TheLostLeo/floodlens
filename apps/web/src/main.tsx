import "leaflet/dist/leaflet.css";
import "./styles.css";
import L from "leaflet";
import markerIcon2x from "leaflet/dist/images/marker-icon-2x.png";
import markerIcon from "leaflet/dist/images/marker-icon.png";
import markerShadow from "leaflet/dist/images/marker-shadow.png";
import { createRoot } from "react-dom/client";
import { useEffect, useRef, useState } from "react";
import { Circle, GeoJSON, MapContainer, Marker, TileLayer, useMap, useMapEvents } from "react-leaflet";

import { addComparison, inDemoRegion, terrainSummary } from "./assessment";

type Point = { lat: number; lng: number };
type BasinContext = {
  status: "available" | "unavailable" | "outside_coverage";
  message: string;
  basin_id?: number;
  basin_level?: number;
  local_area_km2?: number;
  upstream_area_km2?: number;
  upstream_subbasin_count?: number;
  containing_geometry?: object;
  upstream_geometry?: object;
  nearby_river?: { distance_km?: number; strahler_order?: number; relationship: string; connection_status: string; geometry?: object };
  missing_datasets?: string[];
  limitations: string[];
};
type TerrainAssessment = {
  status: "available" | "unavailable" | "outside_coverage";
  message: string;
  score?: number;
  label?: string;
  factors?: { name: string; score: number; explanation: string }[];
  metrics?: Record<string, number | string[]>;
  provenance?: Record<string, string | number | string[]>;
  quality_flags?: string[];
  missing_datasets?: string[];
  limitations: string[];
};
type RainfallContext = {
  status: "available" | "unavailable";
  message: string;
  pressure_level?: string;
  forecast_total_mm?: number;
  max_hourly_mm?: number;
  wet_hours?: number;
  forecast_hours?: number;
  provenance?: Record<string, string | number | null>;
  limitations: string[];
};
type DatasetCoverage = {
  status: "ready" | "partial" | "unavailable";
  message: string;
  datasets: {
    dataset_name: string;
    version: string;
    level?: number | null;
    coverage: string;
    feature_count: number;
    status: string;
    imported_at: string;
  }[];
  missing_required: string[];
  limitations: string[];
};
type Analysis = { created_at: string; updated_at: string; id: string; latitude: number; longitude: number; radius_km: number; status: string; progress: number; message: string; error_code?: string; basin_context?: BasinContext; terrain_assessment?: TerrainAssessment; rainfall_context?: RainfallContext };
const apiBase = "";

L.Icon.Default.mergeOptions({
  iconRetinaUrl: markerIcon2x,
  iconUrl: markerIcon,
  shadowUrl: markerShadow,
});

const pinIcon = L.icon({
  iconRetinaUrl: markerIcon2x,
  iconUrl: markerIcon,
  shadowUrl: markerShadow,
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
});

function PinSelector({ point, setPoint }: { point: Point | null; setPoint: (point: Point) => void }) {
  useMapEvents({ click(event) { setPoint(event.latlng); } });
  return point ? <Marker position={point} icon={pinIcon} /> : null;
}

const places = [
  { name: 'Chennai', lat: 13.0827, lng: 80.2707 },
  { name: 'Visakhapatnam', lat: 17.6868, lng: 83.2185 },
  { name: 'Mumbai', lat: 19.076, lng: 72.8777 },
  { name: 'Kolkata', lat: 22.5726, lng: 88.3639 },
  { name: 'Bengaluru', lat: 12.9716, lng: 77.5946 },
];
const terminal = (status: string) => ['complete', 'waiting_for_data', 'failed'].includes(status);
const statusLabel = (status: string) => ({ complete: 'Assessment ready', waiting_for_data: 'Partial assessment', failed: 'Assessment failed', queued: 'Waiting to start', running: 'Checking your neighbourhood' }[status] ?? status);
function printReport(scope: 'assessment' | 'comparison') {
  document.documentElement.dataset.print = scope;
  window.addEventListener('afterprint', () => { delete document.documentElement.dataset.print; }, { once: true });
  window.print();
}
const dateLabel = (value?: string) => value ? new Date(value).toLocaleString('en-IN') : 'Time unavailable';

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${apiBase}${path}`, { ...options, signal: AbortSignal.timeout(20000) });
  if (!response.ok) throw new Error(`Request failed (${response.status}). Check the local service and retry.`);
  return response.json();
}

function MapFocus({ point }: { point: Point | null }) {
  const map = useMap();
  useEffect(() => { if (point) map.setView(point, 12); }, [point, map]);
  return null;
}

function Assessment({ analysis }: { analysis: Analysis }) {
  const terrain = analysis.terrain_assessment;
  const rain = analysis.rainfall_context;
  const basin = analysis.basin_context;
  const summaryCards = [
    { label: 'Land', value: terrain?.status === 'available' ? `${terrain.score ?? '—'}/100` : 'Unavailable', detail: terrain?.status === 'available' ? (terrain.label ?? 'Relative terrain susceptibility') : 'Terrain coverage was not available here.' },
    { label: 'Forecast rain', value: rain?.status === 'available' ? `${rain.forecast_total_mm ?? '—'} mm` : 'Unavailable', detail: rain?.status === 'available' ? `${rain.pressure_level ?? 'Unknown'} rainfall pressure over ${rain.forecast_hours ?? 'the available'} hours` : 'The forecast service did not return rainfall.' },
    { label: 'River context', value: basin?.status === 'available' ? (basin.nearby_river?.distance_km != null ? `${basin.nearby_river.distance_km} km` : 'Basin found') : 'Unavailable', detail: basin?.status === 'available' ? (basin.nearby_river ? 'Approximate distance to a regional mapped river segment' : 'Containing basin found; no nearby segment returned') : 'Mapped basin context was not available here.' },
  ];
  return <article className="assessment">
    <div className="section-heading"><div><p className="eyebrow">Step 3 · Read the result</p><h2>Your neighbourhood assessment</h2></div><span className="badge">{statusLabel(analysis.status)}</span></div>
    <p className="metadata">{analysis.latitude.toFixed(5)}, {analysis.longitude.toFixed(5)} · {analysis.radius_km} km radius<br />Updated {dateLabel(analysis.updated_at)}</p>
    {!terminal(analysis.status) ? <div className="progress-panel" role="status"><progress aria-label="Assessment progress" max="100" value={analysis.progress} /><p>{analysis.message}</p><span>Checking terrain, forecast rainfall and mapped basin context.</span></div> : <>
      <div className="summary-grid" aria-label="Assessment at a glance">{summaryCards.map(card => <section className="summary-card" key={card.label}><span>{card.label}</span><strong>{card.value}</strong><p>{card.detail}</p></section>)}</div>
      <div className="result-guide"><b>How to read this</b><p>Look at all three signals together. They provide neighbourhood context and do not predict whether a street or home will flood.</p></div>
      <section className="reading"><h3>What the land tells us</h3><p>{terrainSummary(terrain)}</p>
        {terrain?.status !== 'available' && <p className="muted">{terrain?.message ?? 'No terrain result was returned.'}</p>}
        {terrain?.metrics && <dl className="metrics"><div><dt>Ground elevation at the pin</dt><dd>{terrain.metrics.point_elevation_m ?? 'Unknown'} m</dd></div><div><dt>Typical surrounding slope</dt><dd>{terrain.metrics.median_slope_percent ?? 'Unknown'}%</dd></div></dl>}
      </section>
      <section className="reading"><h3>Rain in the forecast</h3>{rain?.status === 'available' ? <><p><b>{rain.forecast_total_mm} mm</b> across {rain.forecast_hours} forecast hours. The rainfall indicator is <b>{rain.pressure_level}</b>.</p><p className="muted">This describes forecast rain, not the chance of flooding. Local drainage, tides and blocked channels also matter.</p></> : <p>{rain?.message ?? 'Rainfall information is not available. Try a new assessment when the weather service is reachable.'}</p>}</section>
      <section className="reading"><h3>Rivers and the surrounding basin</h3>{basin?.status === 'available' ? <><p>{basin.nearby_river ? `A regional mapped river segment is approximately ${basin.nearby_river.distance_km ?? 'an unknown distance'} km from the pin.` : 'No river segment was found in the containing basin.'} The containing basin covers {basin.local_area_km2?.toLocaleString() ?? 'an unknown number of'} km².</p><p className="muted">A basin is an area draining towards a common outlet. The regional river line is too coarse to locate street-level channels; a nearby river does not establish a connection to your home.</p></> : <p>{basin?.message ?? 'River and basin information is not available here.'}</p>}</section>
      <div className="notice"><b>Use this as a starting point</b><p>Discuss the local drainage context with your community and consult official information for decisions. This assessment cannot tell you whether a street or home will flood.</p></div>
    </>}
    {terrain?.quality_flags?.map(flag => <p className="warning report-quality" key={flag}>Data quality: {flag}</p>)}
    <p className="report-sources">Sources: FABDEM terrain · Open-Meteo forecast · HydroBASINS / HydroRIVERS context. Availability is described above.<br />Forecast period: {String(rain?.provenance?.forecast_start ?? 'unavailable')} to {String(rain?.provenance?.forecast_end ?? 'unavailable')} ({String(rain?.provenance?.timezone ?? 'timezone unavailable')}).<br />Terrain version: {String(terrain?.provenance?.version ?? 'unavailable')}.</p>
    <details className="advanced"><summary>Advanced details &amp; sources</summary>
      <p>Analysis ID: <code>{analysis.id}</code></p><p>{analysis.message}</p>
      {terrain?.status === 'available' && <p>Terrain index: {terrain.score}/100 · {terrain.label}. This index is not a probability.</p>}
      {terrain?.factors?.map(factor => <p key={factor.name}><b>{factor.name} ({factor.score}/100)</b><br />{factor.explanation}</p>)}

      {[...(terrain?.limitations ?? []), ...(rain?.limitations ?? []), ...(basin?.limitations ?? [])].map((limit, i) => <p key={i}>{limit}</p>)}
      <pre>{JSON.stringify({ terrain: terrain?.provenance, rainfall: rain?.provenance, basin: basin ? { basin_id: basin.basin_id, basin_level: basin.basin_level, upstream_area_km2: basin.upstream_area_km2, upstream_subbasin_count: basin.upstream_subbasin_count, missing_datasets: basin.missing_datasets } : null }, null, 2)}</pre>
    </details>
  </article>;
}

function App() {
  const [point, setPoint] = useState<Point | null>(null);
  const [radius, setRadius] = useState(2);
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [coverage, setCoverage] = useState<DatasetCoverage | null>(null);
  const [coverageError, setCoverageError] = useState(false);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [saved, setSaved] = useState<Analysis[]>([]);
  const [latitude, setLatitude] = useState('');
  const [longitude, setLongitude] = useState('');
  const [layers, setLayers] = useState({ basin: false, upstream: false });
  const [tileError, setTileError] = useState(false);
  const generation = useRef(0);

  function choosePoint(next: Point) {
    if (!inDemoRegion(next.lat, next.lng)) { setError('Choose a point within the India and neighbouring subcontinent demo region.'); return; }
    generation.current += 1;
    setPoint(next); setLatitude(next.lat.toFixed(5)); setLongitude(next.lng.toFixed(5)); setAnalysis(null); setError(''); setBusy(false);
  }
  function changeRadius(value: number) {
    generation.current += 1;
    setRadius(value); setAnalysis(null); setError(''); setBusy(false);
  }
  async function loadCoverage() {
    setCoverageError(false);
    try { setCoverage(await request<DatasetCoverage>('/api/datasets/coverage')); }
    catch { setCoverageError(true); }
  }
  useEffect(() => { void loadCoverage(); }, []);

  useEffect(() => {
    if (!analysis || terminal(analysis.status)) return;
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout>;
    const current = generation.current;
    async function poll() {
      try {
        const next = await request<Analysis>(`/api/analyses/${analysis!.id}`);
        if (cancelled || current !== generation.current) return;
        setAnalysis(next); setError('');
      } catch {
        if (cancelled || current !== generation.current) return;
        setError('Connection interrupted. Retrying automatically; check that the Docker app and worker are running.');
        timer = setTimeout(poll, 4000);
      }
    }
    timer = setTimeout(poll, 1500);
    return () => { cancelled = true; clearTimeout(timer); };
  }, [analysis]);

  async function runAnalysis(requeue = false) {
    if (!point || busy) return;
    const current = generation.current;
    setBusy(true); setError('');
    try {
      const next = await request<Analysis>(requeue && analysis ? `/api/analyses/${analysis.id}/requeue` : '/api/analyses', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        ...(requeue ? {} : { body: JSON.stringify({ latitude: point.lat, longitude: point.lng, radius_km: radius }) }),
      });
      if (current === generation.current) setAnalysis(next);
    } catch (failure) {
      if (current === generation.current) setError(failure instanceof Error ? failure.message : 'Unable to reach the local service. Try again.');
    } finally { if (current === generation.current) setBusy(false); }
  }
  const basin = analysis?.basin_context;
  const active = busy || !!(analysis && !terminal(analysis.status));
  const canSave = analysis && ['complete', 'waiting_for_data'].includes(analysis.status);
  const selectedPlace = places.find(place => point && Math.abs(place.lat - point.lat) < 0.00001 && Math.abs(place.lng - point.lng) < 0.00001)?.name ?? '';
  const readyDatasetCount = coverage?.datasets.filter(dataset => dataset.status === 'ready').length ?? 0;
  const coverageLabel = coverageError ? 'Data check unavailable' : coverage ? `${readyDatasetCount} mapped datasets ready` : 'Checking data';

  return <>
    <header className="masthead"><a href="#main" className="brand">FloodLens<span>Neighbourhood awareness</span></a><div className="header-note"><a className="research-link" href="/research/">Historical Event Lab</a><span>India &amp; subcontinent</span><span className="badge">Local demo</span></div></header>
    <main id="main">
      <div className="intro"><div><p className="eyebrow">Neighbourhood flood awareness</p><h1>Understand the water around you.</h1><p>Choose a place and get a plain-language view of terrain, forecast rainfall and nearby river context.</p></div><div className="scope-note"><b>For awareness and discussion</b><span>This is not an official flood warning or a prediction for a home.</span></div></div>
      <div className="workspace">
        <section className="location-panel" aria-labelledby="location-heading">
          <div className="step-heading"><span>1</span><div><p>Location</p><h2 id="location-heading">Choose your neighbourhood</h2></div></div>
          <label htmlFor="city">Start with a city</label><select id="city" value={selectedPlace} onChange={event => { const place = places.find(item => item.name === event.target.value); if (place) choosePoint(place); }}><option value="" disabled>Select a city</option><optgroup label="Terrain previously checked at 2 km">{places.slice(0, 2).map(place => <option key={place.name}>{place.name}</option>)}</optgroup><optgroup label="Coverage checked when assessed">{places.slice(2).map(place => <option key={place.name}>{place.name}</option>)}</optgroup></select>
          <p className="hint">You can also click anywhere on the map to move the pin.</p>
          <details className="manual-location"><summary>Use exact coordinates</summary><form onSubmit={event => { event.preventDefault(); if (!latitude.trim() || !longitude.trim()) { setError('Enter both coordinates.'); return; } choosePoint({ lat: Number(latitude), lng: Number(longitude) }); }}>
            <div className="coordinate-fields"><label>Latitude<input required type="number" step="any" min="6" max="38" value={latitude} onChange={event => setLatitude(event.target.value)} placeholder="13.0827" /></label><label>Longitude<input required type="number" step="any" min="68" max="98" value={longitude} onChange={event => setLongitude(event.target.value)} placeholder="80.2707" /></label></div><button type="submit" className="secondary-small">Move pin to coordinates</button>
          </form></details>
          <div className="step-divider" />
          <div className="step-heading"><span>2</span><div><p>Assessment area</p><h2>Choose how far to look</h2></div></div>
          <fieldset><legend className="sr-only">Assessment radius</legend><div className="radius-options">{[{ value: 1, label: 'Nearby' }, { value: 2, label: 'Neighbourhood' }, { value: 5, label: 'Wider area' }].map(option => <button type="button" aria-pressed={radius === option.value} className={radius === option.value ? 'selected' : ''} onClick={() => changeRadius(option.value)} key={option.value}><strong>{option.value} km</strong><span>{option.label}</span></button>)}</div></fieldset>
          <p className="circle-note">The green circle is the area checked around your pin. It is not a watershed or flood boundary.</p>
          <button className="primary" disabled={!point || active} onClick={() => void runAnalysis()}>{active ? 'Building your assessment…' : point ? 'View neighbourhood assessment' : 'Choose a location to continue'}</button>
          {error && <p className="error" role="alert">{error}</p>}
          <details className="coverage"><summary><span className={`availability-dot ${coverageError ? 'error-dot' : ''}`} />{coverageLabel}</summary>
            <p>{coverageError ? 'Could not check registered datasets. This is not evidence of missing or available coverage.' : coverage?.message ?? 'Contacting the local service.'}</p>
            <button onClick={() => void loadCoverage()}>Refresh availability</button>
            {coverage?.missing_required.includes('fabdem') && <p className="hint">FABDEM tiles are mounted separately from this import registry. Assess a point to check whether terrain is available there.</p>}
            {coverage?.datasets.map((dataset, i) => <p key={i}><b>{dataset.dataset_name}</b> · {dataset.status}<br />{dataset.coverage} · {dataset.version}</p>)}
            {coverage?.limitations.map(limit => <p key={limit}>{limit}</p>)}
          </details>
        </section>
        <section className="map-panel" aria-label="Neighbourhood map">
          <div className="map-heading"><div><p className="eyebrow">Map</p><h2>{point ? 'Pin selected' : 'Click the map to choose a place'}</h2></div><span>{point ? `${point.lat.toFixed(4)}, ${point.lng.toFixed(4)}` : 'No pin selected'}</span></div>
          <MapContainer center={[22.5, 80]} zoom={5} minZoom={4} maxBounds={[[4, 65], [40, 101]]} className="map">
            <TileLayer attribution="© OpenStreetMap contributors" url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" eventHandlers={{ tileerror: () => setTileError(true) }} />
            <MapFocus point={point} /><PinSelector point={point} setPoint={choosePoint} />
            {layers.upstream && basin?.upstream_geometry ? <GeoJSON key={`upstream-${analysis?.id}`} data={basin.upstream_geometry as never} style={{ color: '#90613e', weight: 2, dashArray: '6 5', fillOpacity: 0 }} /> : null}
            {layers.basin && basin?.containing_geometry ? <GeoJSON key={`basin-${analysis?.id}`} data={basin.containing_geometry as never} style={{ color: '#785a9b', weight: 2, dashArray: '6 5', fillOpacity: 0 }} /> : null}
            {point && <Circle center={point} radius={radius * 1000} pathOptions={{ color: '#126656', weight: 2, fillOpacity: 0.04 }} />}
          </MapContainer>
          {tileError && <p className="error" role="status">Some map tiles could not load. Check internet access; coordinates remain usable.</p>}
          <fieldset className="layer-controls"><legend>Show after assessment</legend>{(['basin', 'upstream'] as const).map(layer => <label key={layer}><input type="checkbox" disabled={!basin} checked={layers[layer]} onChange={event => setLayers({ ...layers, [layer]: event.target.checked })} /><span className={`line-key ${layer}`} />{({ basin: 'Containing basin', upstream: 'Upstream basins' })[layer]}</label>)}</fieldset>
          <details className="map-explainer"><summary>What does this map show?</summary><p>Green circle: the selected assessment area. Dashed outlines: basin context, never flood extent. Base-map waterways come from OpenStreetMap. Regional river context appears in the result and is not a street-level channel map.</p></details>
        </section>
      </div>
      <section className="results-area" aria-live="polite">
        {analysis ? <><Assessment analysis={analysis} /><div className="actions">{canSave && <button onClick={() => setSaved(previous => addComparison(previous, analysis))}>Keep for comparison ({saved.length}/2)</button>}{terminal(analysis.status) && <button onClick={() => printReport('assessment')}>Print assessment / Save PDF</button>}{analysis.status === 'waiting_for_data' && <button disabled={busy} onClick={() => void runAnalysis(true)}>Recheck imported data</button>}</div></> : <div className="empty-state"><p className="eyebrow">What you will get</p><h2>One local picture from three useful signals</h2><p>After you choose a location, FloodLens explains what is available and clearly marks anything outside local data coverage.</p><div className="source-strip"><span><b>1</b> Terrain shape</span><span><b>2</b> Forecast rainfall</span><span><b>3</b> River and basin context</span></div></div>}
      </section>
      {saved.length > 0 && <section className="comparison"><div className="section-heading"><h2>Compare neighbourhoods</h2><button onClick={() => setSaved([])}>Clear comparison</button></div><p>Saved snapshots from this session. Keep another assessment to compare. Keeping a third replaces the oldest. These results do not rank property safety.</p>
        {saved.length === 2 && (saved[0].radius_km !== saved[1].radius_km) && <p className="warning">These assessments use different radii. Use matching radii for a more consistent comparison.</p>}
        <div className="comparison-grid">{saved.map((item, i) => <div key={item.id}><h3>Location {i + 1}</h3><Assessment analysis={item} /></div>)}</div>{saved.length === 2 && <button onClick={() => printReport('comparison')}>Print comparison / Save PDF</button>}
      </section>}
      <footer>FloodLens · Community awareness project. Coverage depends on imported datasets; India-wide coverage is not guaranteed. Assessments do not establish live waterlogging or predict flooding at a home.</footer>
    </main>
  </>;
}

createRoot(document.getElementById('root')!).render(<App />);
