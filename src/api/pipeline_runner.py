"""
Full pipeline runner.

Runs the complete FloodLens pipeline for a single job in a background
thread, updating the job store at each step so the UI can poll progress.

Pipeline steps
--------------
 5%  Fetch DEM (OpenTopography API)
15%  Reproject DEM to UTM metres
25%  Calculate slope
35%  Breach depressions
45%  Calculate flow direction
55%  Calculate flow accumulation
65%  Extract drainage paths
72%  Fetch OSM water bodies
85%  Score flood risk
95%  Export heatmap PNG
100% Done
"""

from __future__ import annotations

import json
import traceback
from pathlib import Path

from api.job_store import store
from terrain.fetch_dem import fetch_dem, buffer_bounds
from terrain.reproject import reproject_dem_to_utm
from terrain.slope import calculate_slope_degrees
from hydrology.breach_depressions import breach_dem_depressions
from hydrology.flow_direction import calculate_flow_direction
from hydrology.flow_accumulation import calculate_flow_accumulation
from hydrology.extract_streams import extract_drainage_paths
from water_bodies.fetch_water_bodies import download_water_bodies
from risk.flood_risk_score import calculate_flood_risk
from risk.heatmap_exporter import export_heatmap


PROJECT_ROOT = Path(__file__).resolve().parents[2]
JOBS_DATA_DIR = PROJECT_ROOT / "data" / "jobs"


def _step(job_id: str, progress: int, label: str) -> None:
    store.update(job_id, status="running", progress=progress, step=label)
    print(f"[job {job_id[:8]}] {progress:3d}%  {label}")


def run_pipeline(job_id: str) -> None:
    """
    Execute the full pipeline for `job_id`.

    Called in a ThreadPoolExecutor from the FastAPI route. All exceptions
    are caught and stored so the UI receives a clean error message.
    """
    job = store.get(job_id)
    if job is None:
        return

    bounds = job.bounds
    south = bounds["south"]
    north = bounds["north"]
    west = bounds["west"]
    east = bounds["east"]

    job_dir = JOBS_DATA_DIR / job_id
    raw_dir = job_dir / "raw"
    proc_dir = job_dir / "processed"
    out_dir = job_dir / "output"

    for d in (raw_dir, proc_dir, out_dir):
        d.mkdir(parents=True, exist_ok=True)

    try:
        # ------------------------------------------------------------------
        # Step 1 — Fetch DEM
        # ------------------------------------------------------------------
        _step(job_id, 5, "Fetching elevation data (DEM)…")

        buffered = buffer_bounds(south, north, west, east, buffer_km=5.0)
        dem_raw_path = raw_dir / "dem_raw.tif"

        width_deg  = buffered["east"] - buffered["west"]
        height_deg = buffered["north"] - buffered["south"]
        print(
            f"[job {job_id[:8]}] DEM bounding box: "
            f"{width_deg:.2f}° × {height_deg:.2f}° "
            f"(≈ {width_deg * 111:.0f} km × {height_deg * 111:.0f} km)"
        )

        try:
            fetch_dem(
                south=buffered["south"],
                north=buffered["north"],
                west=buffered["west"],
                east=buffered["east"],
                output_path=dem_raw_path,
            )
        except Exception as dem_exc:
            raise RuntimeError(
                f"DEM download failed: {dem_exc}. "
                "Check your OPENTOPOGRAPHY_API_KEY in .env and your internet connection."
            ) from dem_exc

        # ------------------------------------------------------------------
        # Step 2 — Reproject to UTM
        # ------------------------------------------------------------------
        _step(job_id, 15, "Reprojecting to metric coordinates…")

        dem_utm_path = proc_dir / "dem_utm.tif"
        reproject_dem_to_utm(str(dem_raw_path), str(dem_utm_path))

        # ------------------------------------------------------------------
        # Step 3 — Slope
        # ------------------------------------------------------------------
        _step(job_id, 25, "Calculating terrain slope…")

        slope_path = proc_dir / "slope.tif"
        calculate_slope_degrees(dem_utm_path, slope_path)

        # ------------------------------------------------------------------
        # Step 4 — Breach depressions
        # ------------------------------------------------------------------
        _step(job_id, 35, "Correcting terrain depressions…")

        breached_path = proc_dir / "dem_breached.tif"
        breach_dem_depressions(dem_utm_path, breached_path)

        # ------------------------------------------------------------------
        # Step 5 — Flow direction
        # ------------------------------------------------------------------
        _step(job_id, 45, "Computing flow direction…")

        flow_dir_path = proc_dir / "flow_direction.tif"
        calculate_flow_direction(breached_path, flow_dir_path)

        # ------------------------------------------------------------------
        # Step 6 — Flow accumulation
        # ------------------------------------------------------------------
        _step(job_id, 55, "Computing flow accumulation…")

        flow_acc_path = proc_dir / "flow_accumulation.tif"
        calculate_flow_accumulation(flow_dir_path, flow_acc_path)

        # ------------------------------------------------------------------
        # Step 7 — Extract drainage paths
        # ------------------------------------------------------------------
        _step(job_id, 65, "Extracting drainage paths…")

        drainage_path = proc_dir / "drainage_paths.tif"
        extract_drainage_paths(flow_acc_path, drainage_path, threshold=1000)

        # ------------------------------------------------------------------
        # Step 8 — OSM water bodies (best-effort; non-fatal if none found)
        # ------------------------------------------------------------------
        _step(job_id, 72, "Fetching water bodies from OpenStreetMap…")

        water_bodies_path = raw_dir / "water_bodies.geojson"
        try:
            download_water_bodies(
                south=south, north=north, west=west, east=east,
                output_path=water_bodies_path,
            )
        except RuntimeError as exc:
            # No features found is acceptable — continue without water bodies.
            print(f"[job {job_id[:8]}] Water bodies: {exc} — continuing without.")
            water_bodies_path = None

        # ------------------------------------------------------------------
        # Step 9 — Score flood risk
        # ------------------------------------------------------------------
        _step(job_id, 85, "Scoring flood risk…")

        risk_path = proc_dir / "flood_risk.tif"
        calculate_flood_risk(
            dem_utm_path=dem_utm_path,
            slope_path=slope_path,
            flow_accumulation_path=flow_acc_path,
            drainage_paths_path=drainage_path,
            output_path=risk_path,
        )

        # ------------------------------------------------------------------
        # Step 10 — Export heatmap
        # ------------------------------------------------------------------
        _step(job_id, 95, "Rendering flood-risk heatmap…")

        heatmap_png = out_dir / "heatmap.png"
        bounds_json = out_dir / "bounds.json"
        export_heatmap(risk_path, heatmap_png, bounds_json)

        # Read back the bounds so we can include them in the result.
        final_bounds = json.loads(bounds_json.read_text())

        # ------------------------------------------------------------------
        # Done
        # ------------------------------------------------------------------
        store.mark_done(
            job_id,
            result={
                "heatmap_url": f"/api/outputs/{job_id}/heatmap.png",
                "bounds": final_bounds,
            },
        )
        print(f"[job {job_id[:8]}] Pipeline complete.")

    except Exception:
        error_text = traceback.format_exc()
        print(f"[job {job_id[:8]}] FAILED:\n{error_text}")
        store.mark_error(job_id, error=error_text.strip().splitlines()[-1])
