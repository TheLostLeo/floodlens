import "leaflet/dist/leaflet.css";
import "./styles.css";
import L from "leaflet";
import markerIcon2x from "leaflet/dist/images/marker-icon-2x.png";
import markerIcon from "leaflet/dist/images/marker-icon.png";
import markerShadow from "leaflet/dist/images/marker-shadow.png";
import { createRoot } from "react-dom/client";
import { useEffect, useState } from "react";
import { Circle, GeoJSON, MapContainer, Marker, TileLayer, useMapEvents } from "react-leaflet";

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
type Analysis = { id: string; latitude: number; longitude: number; radius_km: number; status: string; progress: number; message: string; error_code?: string; basin_context?: BasinContext; terrain_assessment?: TerrainAssessment; rainfall_context?: RainfallContext };
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

function App() {
  const [point, setPoint] = useState<Point | null>(null);
  const [radius, setRadius] = useState(2);
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [error, setError] = useState("");

  function choosePoint(nextPoint: Point) {
    setPoint(nextPoint);
    setAnalysis(null);
    setError("");
  }

  useEffect(() => {
    if (!analysis || ["waiting_for_data", "complete", "failed"].includes(analysis.status)) return;
    const timer = window.setInterval(async () => {
      try {
        const response = await fetch(`${apiBase}/api/analyses/${analysis.id}`);
        if (response.ok) setAnalysis(await response.json());
      } catch { setError("Unable to reach the FloodLens API."); }
    }, 1500);
    return () => window.clearInterval(timer);
  }, [analysis]);

  async function startAnalysis() {
    if (!point) return;
    setError("");
    try {
      const response = await fetch(`${apiBase}/api/analyses`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ latitude: point.lat, longitude: point.lng, radius_km: radius }) });
      if (!response.ok) throw new Error("request rejected");
      setAnalysis(await response.json());
    } catch { setError("Could not create an analysis. Check that the local API is running."); }
  }

  async function requeueAnalysis() {
    if (!analysis) return;
    setError("");
    try {
      const response = await fetch(`${apiBase}/api/analyses/${analysis.id}/requeue`, { method: "POST" });
      if (!response.ok) throw new Error("requeue rejected");
      setAnalysis(await response.json());
    } catch { setError("This analysis could not be requeued. It may no longer be waiting for data."); }
  }

  const basin = analysis?.basin_context;
  const terrain = analysis?.terrain_assessment;
  const rainfall = analysis?.rainfall_context;

  return <main>
    <section className="panel"><h1>FloodLens</h1><p className="tagline">Neighbourhood flood-awareness, not an official warning service.</p>
      <h2>1. Choose a location</h2><p>Click the map to place your neighbourhood pin. The circle is a local assessment area, not a watershed.</p>
      <h2>2. Choose local radius</h2><div className="radii">{[1, 2, 5].map(value => <button className={radius === value ? "selected" : ""} onClick={() => setRadius(value)} key={value}>{value} km</button>)}</div>
      <button className="analyse" disabled={!point} onClick={startAnalysis}>Analyse this area</button>
      {error && <p className="error">{error}</p>}
      {analysis && <section className="result"><h2>Analysis status</h2><strong>{analysis.status.replaceAll("_", " ")}</strong><progress value={analysis.progress} max="100" /> <span>{analysis.progress}%</span><p>{analysis.message}</p>
        {terrain?.status === "available" ? <div className="score-card"><b>Local terrain susceptibility</b><div className="score-row"><span>{terrain.score}</span><small>{terrain.label}</small></div>
          {terrain.metrics ? <dl>
            <div><dt>Point elevation</dt><dd>{terrain.metrics.point_elevation_m} m</dd></div>
            <div><dt>Local relief</dt><dd>{terrain.metrics.local_relief_m} m</dd></div>
            <div><dt>Median slope</dt><dd>{terrain.metrics.median_slope_percent}%</dd></div>
          </dl> : null}
          {terrain.factors?.map(factor => <p className="factor" key={factor.name}><b>{factor.name}: {factor.score}</b><br />{factor.explanation}</p>)}
          {terrain.quality_flags?.length ? <p className="warning">Quality notes: {terrain.quality_flags.join("; ")}</p> : null}
          <p>{terrain.limitations[0]}</p>
        </div> : <div className="pending"><b>{terrain?.status === "outside_coverage" ? "Terrain: outside mounted coverage" : "Terrain: unavailable"}</b><br />{terrain?.message ?? "FABDEM local ground-terrain tiles have not been imported, so no local susceptibility result is shown."}</div>}
        {rainfall?.status === "available" ? <div className="rain-card"><b>Forecast rainfall pressure</b><dl>
          <div><dt>Pressure</dt><dd>{rainfall.pressure_level}</dd></div>
          <div><dt>Total forecast rain</dt><dd>{rainfall.forecast_total_mm} mm</dd></div>
          <div><dt>Max hourly rain</dt><dd>{rainfall.max_hourly_mm} mm</dd></div>
          <div><dt>Wet hours</dt><dd>{rainfall.wet_hours} of {rainfall.forecast_hours}</dd></div>
        </dl><p>{rainfall.limitations[0]}</p></div> : rainfall ? <div className="pending"><b>Rainfall: unavailable</b><br />{rainfall.message}</div> : null}
        {!basin || basin.status === "unavailable" ? <div className="pending"><b>River-basin context: pending dataset import</b><br />{basin?.message ?? "HydroBASINS/HydroRIVERS have not been imported, so no basin claim is shown."}</div> : null}
        {basin?.status === "outside_coverage" ? <div className="pending"><b>River-basin context: outside imported coverage</b><br />{basin.message}</div> : null}
        {basin?.status === "available" ? <div className="basin-card"><b>Global river-basin context</b><dl>
          <div><dt>HydroBASINS level</dt><dd>{basin.basin_level}</dd></div>
          <div><dt>Containing sub-basin</dt><dd>{basin.local_area_km2?.toLocaleString()} km²</dd></div>
          <div><dt>Upstream context</dt><dd>{basin.upstream_area_km2?.toLocaleString()} km² across {basin.upstream_subbasin_count} sub-basins</dd></div>
          <div><dt>Nearby mapped river</dt><dd>{basin.nearby_river ? `${basin.nearby_river.distance_km} km away` : "None found in this sub-basin"}</dd></div>
        </dl><p>This is catchment context, not proof that the selected home is connected to or will flood from that river.</p></div> : null}
        {analysis.status === "waiting_for_data" ? <button className="requeue" onClick={requeueAnalysis}>Check imported data again</button> : null}
      </section>}
      <p className="limits">Current foundation demo: results are valid only after required datasets are imported. Never use this page for emergency decisions.</p>
    </section>
    <MapContainer center={[20, 0]} zoom={2} minZoom={2} className="map"><TileLayer attribution="© OpenStreetMap contributors" url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" /><PinSelector point={point} setPoint={choosePoint} />{basin?.upstream_geometry ? <GeoJSON key={`upstream-${basin.basin_id}`} data={basin.upstream_geometry as never} style={{ color: "#2e64a2", weight: 2, fillOpacity: 0.08 }} /> : null}{basin?.containing_geometry ? <GeoJSON key={`local-${basin.basin_id}`} data={basin.containing_geometry as never} style={{ color: "#7b3fa1", weight: 3, fillOpacity: 0.12 }} /> : null}{basin?.nearby_river?.geometry ? <GeoJSON key={`river-${basin.basin_id}`} data={basin.nearby_river.geometry as never} style={{ color: "#147fb1", weight: 4 }} /> : null}{point && <Circle center={point} radius={radius * 1000} pathOptions={{ color: "#1d8a78" }} />}</MapContainer>
  </main>;
}
export default App;

createRoot(document.getElementById("root") as HTMLElement).render(<App />);
