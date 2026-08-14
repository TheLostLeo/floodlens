"""FastAPI application for the FloodLens flood-risk analysis platform."""

from __future__ import annotations

import concurrent.futures
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, field_validator

from api.geocoder import geocode_place, GeocoderError
from api.job_store import store
from api.pipeline_runner import run_pipeline, JOBS_DATA_DIR


PROJECT_ROOT = Path(__file__).resolve().parents[2]
WEB_DIRECTORY = PROJECT_ROOT / "web"

app = FastAPI(title="FloodLens API", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=WEB_DIRECTORY), name="static")

# Thread pool — allow up to 3 concurrent pipeline runs.
_executor = concurrent.futures.ThreadPoolExecutor(max_workers=3)


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------

class AnalyseRequest(BaseModel):
    """
    Start a flood-risk analysis for a named place.

    Exactly one of `place_name` (resolved via Nominatim) or an explicit
    bounding box (`south`, `north`, `west`, `east`) must be provided.
    """
    place_name: str | None = None
    south: float | None = None
    north: float | None = None
    west: float | None = None
    east: float | None = None

    @field_validator("place_name")
    @classmethod
    def strip_place_name(cls, v: str | None) -> str | None:
        return v.strip() if v else v


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/", include_in_schema=False)
def home() -> FileResponse:
    return FileResponse(WEB_DIRECTORY / "index.html")


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "service": "FloodLens", "version": "0.2.0"}


@app.post("/api/analyse", status_code=202)
def start_analysis(req: AnalyseRequest) -> dict:
    """
    Accept a region (place name or explicit bbox) and start the pipeline.

    Returns immediately with the job_id. The client polls /api/jobs/{job_id}
    for progress.
    """
    # --- Resolve region ---
    if req.place_name:
        try:
            geo = geocode_place(req.place_name)
        except GeocoderError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

        bounds = {
            "south": geo["south"],
            "north": geo["north"],
            "west": geo["west"],
            "east": geo["east"],
        }
        display_name = geo.get("display_name", req.place_name)

    elif all(v is not None for v in (req.south, req.north, req.west, req.east)):
        if req.south >= req.north or req.west >= req.east:
            raise HTTPException(
                status_code=422,
                detail="Bounding box is invalid: south/west must be less than north/east.",
            )
        bounds = {
            "south": float(req.south),
            "north": float(req.north),
            "west": float(req.west),
            "east": float(req.east),
        }
        display_name = (
            f"{req.south:.3f}°N, {req.west:.3f}°E → "
            f"{req.north:.3f}°N, {req.east:.3f}°E"
        )
    else:
        raise HTTPException(
            status_code=422,
            detail="Provide either 'place_name' or all four bbox fields (south, north, west, east).",
        )

    # --- Create job and dispatch to thread pool ---
    job = store.create(place_name=display_name, bounds=bounds)
    _executor.submit(run_pipeline, job.job_id)

    return {
        "job_id": job.job_id,
        "place_name": display_name,
        "bounds": bounds,
        "status": "queued",
    }


@app.get("/api/jobs/{job_id}")
def job_status(job_id: str) -> dict:
    """Poll the status and progress of a pipeline job."""
    job = store.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")
    return store.as_dict(job)


@app.get("/api/outputs/{job_id}/{filename}", include_in_schema=False)
def serve_output(job_id: str, filename: str) -> FileResponse:
    """Serve a generated output file (e.g. heatmap.png) for a completed job."""
    job = store.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")

    file_path = JOBS_DATA_DIR / job_id / "output" / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"Output file '{filename}' not found.")

    return FileResponse(file_path)
