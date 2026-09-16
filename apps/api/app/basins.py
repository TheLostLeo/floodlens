import json
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Connection

from .db import engine

REQUIRED_DATASETS = ("hydrobasins", "hydrorivers")
DISPLAY_SIMPLIFICATION_DEGREES = 0.002


def _json(value: Any) -> dict | None:
    if value is None or isinstance(value, dict):
        return value
    return json.loads(value)


def _provenance(connection: Connection) -> tuple[dict[str, dict], list[str]]:
    rows = connection.execute(text("""
      SELECT DISTINCT ON (dataset_name)
        dataset_name, version, level, coverage, source_url, licence, sha256,
        feature_count, imported_at
      FROM dataset_imports
      WHERE dataset_name IN ('hydrobasins', 'hydrorivers') AND status = 'ready'
      ORDER BY dataset_name, imported_at DESC
    """)).mappings().all()
    available = {}
    for row in rows:
        item = dict(row)
        if item.get("imported_at") is not None:
            item["imported_at"] = item["imported_at"].isoformat()
        available[row["dataset_name"]] = item
    missing = [name for name in REQUIRED_DATASETS if name not in available]
    return available, missing


def get_basin_context(latitude: float, longitude: float, connection: Connection | None = None) -> dict:
    if connection is None:
        with engine.connect() as owned_connection:
            return get_basin_context(latitude, longitude, owned_connection)

    provenance, missing = _provenance(connection)
    limitations = [
        "Basin membership and a nearby river do not prove that the selected property will flood.",
        "Global river and basin data cannot represent every urban drain, culvert, levee, or channel change.",
        "Displayed boundaries are simplified; calculations use stored source geometry.",
    ]
    if missing:
        return {
            "status": "unavailable",
            "message": "HydroBASINS and HydroRIVERS must be imported before basin context is available.",
            "missing_datasets": missing,
            "limitations": limitations,
        }

    point_params = {"latitude": latitude, "longitude": longitude}
    basin = connection.execute(text("""
      WITH point AS (
        SELECT ST_SetSRID(ST_Point(:longitude, :latitude), 4326) AS geom
      )
      SELECT b.hybas_id, b.source_version, b.coverage, b.level, b.pfaf_id, b.sub_area_km2,
             ST_AsGeoJSON(
               ST_SimplifyPreserveTopology(b.geom, :tolerance), 6
             )::jsonb AS geometry
      FROM basins b, point p
      WHERE ST_Covers(b.geom, p.geom)
      ORDER BY b.level DESC, b.sub_area_km2 ASC
      LIMIT 1
    """), {**point_params, "tolerance": DISPLAY_SIMPLIFICATION_DEGREES}).mappings().one_or_none()

    if basin is None:
        return {
            "status": "outside_coverage",
            "message": "The selected point is outside the imported basin coverage.",
            "provenance": provenance,
            "missing_datasets": [],
            "limitations": limitations,
        }

    upstream = connection.execute(text("""
      WITH RECURSIVE upstream(hybas_id, path) AS (
        SELECT CAST(:hybas_id AS bigint), ARRAY[CAST(:hybas_id AS bigint)]
        UNION ALL
        SELECT candidate.hybas_id, upstream.path || candidate.hybas_id
        FROM basins candidate
        JOIN upstream ON candidate.next_down = upstream.hybas_id
        WHERE candidate.level = :level
          AND candidate.coverage = :coverage
          AND NOT candidate.hybas_id = ANY(upstream.path)
      )
      SELECT COUNT(*) AS subbasin_count,
             COALESCE(SUM(b.sub_area_km2), 0) AS area_km2,
             ST_AsGeoJSON(
               ST_SimplifyPreserveTopology(
                 ST_UnaryUnion(ST_Collect(b.geom)), :tolerance
               ), 6
             )::jsonb AS geometry
      FROM upstream
      JOIN basins b USING (hybas_id)
    """), {
        "hybas_id": basin["hybas_id"],
        "level": basin["level"],
        "coverage": basin["coverage"],
        "tolerance": DISPLAY_SIMPLIFICATION_DEGREES,
    }).mappings().one()

    river = connection.execute(text("""
      WITH point AS (
        SELECT ST_SetSRID(ST_Point(:longitude, :latitude), 4326) AS geom
      ), selected_basin AS (
        SELECT geom FROM basins WHERE hybas_id = :hybas_id
      )
      SELECT r.hyriv_id, r.main_riv, r.length_km, r.upstream_area_km2,
             r.discharge_cms, r.strahler_order,
             ROUND((ST_Distance(r.geom::geography, p.geom::geography) / 1000.0)::numeric, 2)::double precision AS distance_km,
             ST_AsGeoJSON(ST_Simplify(r.geom, :tolerance), 6)::jsonb AS geometry
      FROM rivers r, point p, selected_basin b
      WHERE r.coverage = :coverage
        AND ST_Intersects(r.geom, b.geom)
      ORDER BY r.geom <-> p.geom
      LIMIT 1
    """), {
        **point_params,
        "hybas_id": basin["hybas_id"],
        "coverage": basin["coverage"],
        "tolerance": DISPLAY_SIMPLIFICATION_DEGREES,
    }).mappings().one_or_none()

    nearby_river = None
    if river is not None:
        river_values = dict(river)
        river_values["geometry"] = _json(river_values["geometry"])
        nearby_river = {
            **river_values,
            "relationship": "nearest mapped river segment intersecting the containing sub-basin",
            "connection_status": "context_only_not_property_flood_connectivity",
        }

    return {
        "status": "available",
        "message": "Global basin and nearby river context is available.",
        "basin_id": basin["hybas_id"],
        "basin_level": basin["level"],
        "coverage": basin["coverage"],
        "pfaf_id": basin["pfaf_id"],
        "local_area_km2": basin["sub_area_km2"],
        "upstream_area_km2": upstream["area_km2"],
        "upstream_subbasin_count": upstream["subbasin_count"],
        "containing_geometry": _json(basin["geometry"]),
        "upstream_geometry": _json(upstream["geometry"]),
        "nearby_river": nearby_river,
        "provenance": provenance,
        "missing_datasets": [],
        "limitations": limitations,
    }
