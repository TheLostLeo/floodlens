"""FastAPI application for the FloodLens local terrain viewer."""

from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from api.terrain_service import terrain_at_point


PROJECT_ROOT = Path(__file__).resolve().parents[2]
WEB_DIRECTORY = PROJECT_ROOT / "web"

app = FastAPI(title="FloodLens API", version="0.1.0")
app.mount("/static", StaticFiles(directory=WEB_DIRECTORY), name="static")


@app.get("/", include_in_schema=False)
def home() -> FileResponse:
    return FileResponse(WEB_DIRECTORY / "index.html")


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "service": "FloodLens"}


@app.get("/api/terrain/point")
def point_terrain(
    longitude: float = Query(ge=-180, le=180),
    latitude: float = Query(ge=-90, le=90),
) -> dict:
    return terrain_at_point(longitude, latitude)


@app.get("/api/selection")
def selection(
    west: float = Query(ge=-180, le=180),
    south: float = Query(ge=-90, le=90),
    east: float = Query(ge=-180, le=180),
    north: float = Query(ge=-90, le=90),
) -> dict:
    if west >= east or south >= north:
        raise HTTPException(status_code=400, detail="Selection bounds are invalid.")
    return {
        "bounds": {"west": west, "south": south, "east": east, "north": north},
        "terrain": terrain_at_point((west + east) / 2, (south + north) / 2),
    }
