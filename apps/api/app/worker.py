import logging
import os
import time
from .domain import AnalysisStatus
from .terrain import evaluate_terrain, unavailable_result
from .weather import WeatherUnavailable, fetch_open_meteo, summarize_rainfall

logging.basicConfig(level=logging.INFO, format='{"time":"%(asctime)s","level":"%(levelname)s","message":"%(message)s"}')
logger = logging.getLogger(__name__)


def claim_next() -> dict | None:
    from .repository import claim_next as repository_claim_next
    return repository_claim_next()


def save_weather(*args) -> None:
    from .repository import save_weather as repository_save_weather
    repository_save_weather(*args)


def save_rainfall_context(*args) -> None:
    from .repository import save_rainfall_context as repository_save_rainfall_context
    repository_save_rainfall_context(*args)


def get_basin_context(*args) -> dict:
    from .basins import get_basin_context as basins_get_basin_context
    return basins_get_basin_context(*args)


def save_basin_context(*args) -> None:
    from .repository import save_basin_context as repository_save_basin_context
    repository_save_basin_context(*args)


def save_terrain_assessment(*args) -> None:
    from .repository import save_terrain_assessment as repository_save_terrain_assessment
    repository_save_terrain_assessment(*args)


def transition(*args) -> bool:
    from .repository import transition as repository_transition
    return repository_transition(*args)


def process_one() -> bool:
    job = claim_next()
    if job is None:
        return False
    analysis_id = job["id"]
    try:
        weather_error = None
        rainfall = None
        try:
            weather = fetch_open_meteo(job["latitude"], job["longitude"])
            save_weather(analysis_id, "open-meteo", "available", weather, None)
            rainfall = summarize_rainfall(weather)
            save_rainfall_context(analysis_id, rainfall)
        except WeatherUnavailable as error:
            weather_error = str(error)
            save_weather(analysis_id, "open-meteo", "unavailable", None, weather_error)
            rainfall = summarize_rainfall(None)
            save_rainfall_context(analysis_id, rainfall)

        context = get_basin_context(job["latitude"], job["longitude"])
        save_basin_context(analysis_id, context)
        try:
            terrain = evaluate_terrain(
                job["latitude"],
                job["longitude"],
                job["radius_km"],
                os.getenv("TERRAIN_DIR", "/imports/fabdem"),
                os.getenv("TERRAIN_DATASET_VERSION", "FABDEM user-mounted local tiles"),
                float(os.getenv("TERRAIN_RESOLUTION_M", "30")),
            )
        except Exception:
            logger.exception("terrain evaluation failed", extra={"analysis_id": str(analysis_id)})
            terrain = unavailable_result(
                "Terrain evaluation failed. Check the mounted FABDEM files and rebuild the worker.",
                missing_datasets=["fabdem"],
            )
        save_terrain_assessment(analysis_id, terrain)

        if terrain["status"] == "available":
            message = "Terrain susceptibility is ready with rainfall and basin context where available."
            if context["status"] != "available":
                message = "Terrain susceptibility is ready; river-basin context is still unavailable for this point."
            error_code = "weather_unavailable" if weather_error else None
            transition(
                analysis_id,
                AnalysisStatus.RUNNING,
                AnalysisStatus.COMPLETE,
                100,
                message,
                error_code,
            )
            return True

        terrain_note = terrain.get("message", "Local FABDEM terrain is unavailable.")
        weather_note = "Rainfall forecast is unavailable." if weather_error else "Rainfall forecast is ready."
        if context["status"] == "available":
            message = f"Basin context is ready. {weather_note} {terrain_note}"
            progress = 80
            error_code = "terrain_unavailable"
        elif context["status"] == "outside_coverage":
            message = f"The point is outside imported basin coverage. {weather_note} {terrain_note}"
            progress = 65
            error_code = "terrain_unavailable"
        else:
            message = f"{weather_note} HydroBASINS and HydroRIVERS are unavailable. {terrain_note}"
            progress = 45 if weather_error else 55
            error_code = "weather_unavailable" if weather_error else "spatial_data_unavailable"
        transition(
            analysis_id,
            AnalysisStatus.RUNNING,
            AnalysisStatus.WAITING_FOR_DATA,
            progress,
            message,
            error_code,
        )
    except Exception:
        logger.exception("analysis worker failed", extra={"analysis_id": str(analysis_id)})
        transition(analysis_id, AnalysisStatus.RUNNING, AnalysisStatus.FAILED, 100, "Analysis worker failed.", "worker_error")
    return True


if __name__ == "__main__":
    while True:
        if not process_one():
            time.sleep(2)
