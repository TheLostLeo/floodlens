from uuid import UUID, uuid4
from sqlalchemy import text
from .db import engine
from .domain import AnalysisStatus, can_transition
from .schemas import AnalysisCreate


def create_analysis(payload: AnalysisCreate) -> dict:
    analysis_id = uuid4()
    with engine.begin() as connection:
        row = connection.execute(text("""
          INSERT INTO analyses (id, latitude, longitude, radius_km, status, progress, message)
          VALUES (:id, :lat, :lon, :radius, 'queued', 0, 'Analysis queued')
          RETURNING *
        """), {"id": analysis_id, "lat": payload.latitude, "lon": payload.longitude, "radius": payload.radius_km}).mappings().one()
    return dict(row)


def get_analysis(analysis_id: UUID) -> dict | None:
    with engine.connect() as connection:
        row = connection.execute(text("""
          SELECT a.*,
                 c.context AS basin_context,
                 t.context AS terrain_assessment,
                 r.context AS rainfall_context
          FROM analyses a
          LEFT JOIN analysis_basin_context c ON c.analysis_id = a.id
          LEFT JOIN analysis_terrain_context t ON t.analysis_id = a.id
          LEFT JOIN analysis_rainfall_context r ON r.analysis_id = a.id
          WHERE a.id = :id
        """), {"id": analysis_id}).mappings().one_or_none()
    return dict(row) if row else None


def list_dataset_coverage() -> dict:
    with engine.connect() as connection:
        rows = connection.execute(text("""
          SELECT DISTINCT ON (dataset_name, coverage, level)
            dataset_name, version, level, coverage, source_url, licence, sha256,
            feature_count, status, detail, imported_at
          FROM dataset_imports
          ORDER BY dataset_name, coverage, level, imported_at DESC
        """)).mappings().all()

    datasets = []
    ready_names = set()
    for row in rows:
        item = dict(row)
        if item.get("imported_at") is not None:
            item["imported_at"] = item["imported_at"].isoformat()
        if item["status"] == "ready":
            ready_names.add(item["dataset_name"])
        datasets.append(item)

    required_live = ("hydrobasins", "hydrorivers", "fabdem")
    missing_required = [name for name in required_live if name not in ready_names]
    if missing_required:
        status = "partial" if ready_names else "unavailable"
        message = "Some required resident-facing datasets are not imported or registered."
    else:
        status = "ready"
        message = "Required resident-facing datasets are registered as ready for their imported coverage."

    return {
        "status": status,
        "message": message,
        "datasets": datasets,
        "missing_required": missing_required,
        "limitations": [
            "Ready datasets only cover the regions listed here; they do not imply global coverage.",
            "FABDEM coverage is tile-based and must overlap the selected 1/2/5 km circle.",
            "HydroBASINS and HydroRIVERS give basin and river context, not property-level flood connectivity.",
        ],
    }


def claim_next() -> dict | None:
    with engine.begin() as connection:
        row = connection.execute(text("""
          WITH candidate AS (
            SELECT id FROM analyses WHERE status = 'queued' ORDER BY created_at FOR UPDATE SKIP LOCKED LIMIT 1
          )
          UPDATE analyses SET status = 'running', progress = 10, message = 'Checking weather and dataset availability', updated_at = NOW()
          WHERE id IN (SELECT id FROM candidate) RETURNING *
        """)).mappings().one_or_none()
    return dict(row) if row else None


def transition(analysis_id: UUID, current: AnalysisStatus, target: AnalysisStatus, progress: int, message: str, error_code: str | None = None) -> bool:
    if not can_transition(current, target):
        raise ValueError(f"invalid state transition {current} -> {target}")
    with engine.begin() as connection:
        result = connection.execute(text("""
          UPDATE analyses SET status = :target, progress = :progress, message = :message, error_code = :error_code, updated_at = NOW()
          WHERE id = :id AND status = :current
        """), {"id": analysis_id, "current": current.value, "target": target.value, "progress": progress, "message": message, "error_code": error_code})
    return result.rowcount == 1


def requeue_analysis(analysis_id: UUID) -> dict | None:
    with engine.begin() as connection:
        row = connection.execute(text("""
          UPDATE analyses
          SET status = 'queued', progress = 0, message = 'Analysis requeued after data availability changed',
              error_code = NULL, updated_at = NOW()
          WHERE id = :id AND status = 'waiting_for_data'
          RETURNING *
        """), {"id": analysis_id}).mappings().one_or_none()
    return dict(row) if row else None


def save_weather(analysis_id: UUID, provider: str, status: str, response: dict | None, detail: str | None) -> None:
    hourly_times = (response or {}).get("hourly", {}).get("time", [])
    timezone = (response or {}).get("timezone")
    forecast_start = f"{hourly_times[0]}+00:00" if hourly_times and timezone == "GMT" else None
    forecast_end = f"{hourly_times[-1]}+00:00" if hourly_times and timezone == "GMT" else None
    with engine.begin() as connection:
        connection.execute(text("""
          INSERT INTO weather_provenance (
            id, analysis_id, provider, status, response, detail,
            forecast_start, forecast_end, provider_timezone
          ) VALUES (
            :id, :analysis_id, :provider, :status, CAST(:response AS jsonb), :detail,
            :forecast_start, :forecast_end, :provider_timezone
          )
        """), {
            "id": uuid4(),
            "analysis_id": analysis_id,
            "provider": provider,
            "status": status,
            "response": __import__('json').dumps(response) if response else None,
            "detail": detail,
            "forecast_start": forecast_start,
            "forecast_end": forecast_end,
            "provider_timezone": timezone,
        })


def save_basin_context(analysis_id: UUID, context: dict) -> None:
    with engine.begin() as connection:
        connection.execute(text("""
          INSERT INTO analysis_basin_context (analysis_id, context)
          VALUES (:analysis_id, CAST(:context AS jsonb))
          ON CONFLICT (analysis_id) DO UPDATE
          SET context = EXCLUDED.context, updated_at = NOW()
        """), {
            "analysis_id": analysis_id,
            "context": __import__('json').dumps(context),
        })


def save_terrain_assessment(analysis_id: UUID, context: dict) -> None:
    with engine.begin() as connection:
        connection.execute(text("""
          INSERT INTO analysis_terrain_context (analysis_id, context)
          VALUES (:analysis_id, CAST(:context AS jsonb))
          ON CONFLICT (analysis_id) DO UPDATE
          SET context = EXCLUDED.context, updated_at = NOW()
        """), {
            "analysis_id": analysis_id,
            "context": __import__('json').dumps(context),
        })


def save_rainfall_context(analysis_id: UUID, context: dict) -> None:
    with engine.begin() as connection:
        connection.execute(text("""
          INSERT INTO analysis_rainfall_context (analysis_id, context)
          VALUES (:analysis_id, CAST(:context AS jsonb))
          ON CONFLICT (analysis_id) DO UPDATE
          SET context = EXCLUDED.context, updated_at = NOW()
        """), {
            "analysis_id": analysis_id,
            "context": __import__('json').dumps(context),
        })
