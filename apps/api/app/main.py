import logging
from pathlib import Path
from uuid import UUID
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from . import repository
from .basins import get_basin_context
from .db import healthcheck
from .config import settings
from .schemas import AnalysisCreate, AnalysisResponse, BasinContextResponse

logging.basicConfig(level=logging.INFO, format='{"time":"%(asctime)s","level":"%(levelname)s","message":"%(message)s"}')
app = FastAPI(title="FloodLens Next API", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=[settings.web_origin], allow_methods=["GET", "POST"], allow_headers=["Content-Type"])


@app.get("/health/live")
def live() -> dict:
    return {"status": "ok"}


@app.get("/health/ready")
def ready() -> dict:
    try:
        healthcheck()
    except Exception as error:
        raise HTTPException(status_code=503, detail="database unavailable") from error
    return {"status": "ok"}


@app.post("/api/analyses", status_code=202, response_model=AnalysisResponse)
def create(payload: AnalysisCreate) -> dict:
    return repository.create_analysis(payload)


@app.get("/api/analyses/{analysis_id}", response_model=AnalysisResponse)
def get(analysis_id: UUID) -> dict:
    analysis = repository.get_analysis(analysis_id)
    if analysis is None:
        raise HTTPException(status_code=404, detail="analysis not found")
    return analysis


@app.post("/api/analyses/{analysis_id}/requeue", response_model=AnalysisResponse)
def requeue(analysis_id: UUID) -> dict:
    existing = repository.get_analysis(analysis_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="analysis not found")
    if existing["status"] == "queued":
        return existing
    analysis = repository.requeue_analysis(analysis_id)
    if analysis is None:
        raced = repository.get_analysis(analysis_id)
        if raced is not None and raced["status"] == "queued":
            return raced
        raise HTTPException(status_code=409, detail="only waiting_for_data analyses can be requeued")
    analysis["basin_context"] = existing.get("basin_context")
    return analysis


@app.get("/api/basins/context", response_model=BasinContextResponse)
def basin_context(
    latitude: float = Query(ge=-90, le=90),
    longitude: float = Query(ge=-180, le=180),
) -> dict:
    return get_basin_context(latitude, longitude)


STATIC_DIR = Path(__file__).resolve().parents[1] / "static"
ASSETS_DIR = STATIC_DIR / "assets"

if ASSETS_DIR.exists():
    app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="frontend-assets")


@app.get("/", include_in_schema=False)
def serve_frontend() -> FileResponse:
    index_file = STATIC_DIR / "index.html"
    if not index_file.exists():
        raise HTTPException(status_code=404, detail="frontend build is unavailable")
    return FileResponse(index_file)
