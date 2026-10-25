#!/bin/sh
set -eu

: "${POSTGRES_DB:?POSTGRES_DB is required}"
: "${POSTGRES_USER:?POSTGRES_USER is required}"
: "${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is required}"
: "${BASINS_FILE:?BASINS_FILE must point to a mounted .shp file under /imports}"
: "${RIVERS_FILE:?RIVERS_FILE must point to a mounted .shp file under /imports}"
: "${BASIN_LEVEL:?BASIN_LEVEL must be an integer from 1 through 12}"
: "${DATASET_VERSION:?DATASET_VERSION is required}"
: "${COVERAGE:?COVERAGE identifies the imported region, such as asia or global}"
: "${BASINS_SOURCE_URL:?BASINS_SOURCE_URL is required for provenance}"
: "${RIVERS_SOURCE_URL:?RIVERS_SOURCE_URL is required for provenance}"

case "$BASINS_FILE" in /imports/*.shp) ;; *) echo "BASINS_FILE must be under /imports" >&2; exit 2 ;; esac
case "$RIVERS_FILE" in /imports/*.shp) ;; *) echo "RIVERS_FILE must be under /imports" >&2; exit 2 ;; esac
case "$BASIN_LEVEL" in 1|2|3|4|5|6|7|8|9|10|11|12) ;; *) echo "BASIN_LEVEL must be 1-12" >&2; exit 2 ;; esac
[ -f "$BASINS_FILE" ] || { echo "Missing basin shapefile: $BASINS_FILE" >&2; exit 2; }
[ -f "$RIVERS_FILE" ] || { echo "Missing river shapefile: $RIVERS_FILE" >&2; exit 2; }
command -v shp2pgsql >/dev/null 2>&1 || {
  echo "shp2pgsql is not installed in the importer image. Rebuild the importer service." >&2
  exit 2
}

export PGPASSWORD="$POSTGRES_PASSWORD"
PSQL="psql -v ON_ERROR_STOP=1 -h db -U $POSTGRES_USER -d $POSTGRES_DB"
BASINS_SHA256=$(sha256sum "$BASINS_FILE" | awk '{print $1}')
RIVERS_SHA256=$(sha256sum "$RIVERS_FILE" | awk '{print $1}')

$PSQL -c "
  DROP TABLE IF EXISTS staging_hydrobasins;
  DROP TABLE IF EXISTS staging_hydrorivers;
  DROP SEQUENCE IF EXISTS staging_hydrobasins_gid_seq CASCADE;
  DROP SEQUENCE IF EXISTS staging_hydrorivers_gid_seq CASCADE;
"
shp2pgsql -D -s 4326 -W UTF-8 "$BASINS_FILE" staging_hydrobasins | $PSQL
shp2pgsql -D -s 4326 -W UTF-8 "$RIVERS_FILE" staging_hydrorivers | $PSQL

$PSQL \
  -v basin_level="$BASIN_LEVEL" \
  -v dataset_version="$DATASET_VERSION" \
  -v coverage="$COVERAGE" \
  -v basins_source_url="$BASINS_SOURCE_URL" \
  -v rivers_source_url="$RIVERS_SOURCE_URL" \
  -v basins_sha256="$BASINS_SHA256" \
  -v rivers_sha256="$RIVERS_SHA256" <<'SQL'
BEGIN;

INSERT INTO basins (
  hybas_id, source_version, coverage, level, next_down, main_bas, pfaf_id, sub_area_km2,
  upstream_area_km2, basin_order, endorheic, coastal, geom
)
SELECT
  hybas_id::bigint,
  :'dataset_version',
  :'coverage',
  :'basin_level'::smallint,
  NULLIF(next_down::bigint, 0),
  NULLIF(main_bas::bigint, 0),
  NULLIF(pfaf_id::bigint, 0),
  GREATEST(sub_area::double precision, 0),
  GREATEST(up_area::double precision, 0),
  "order"::smallint,
  COALESCE(endo::integer, 0) = 1,
  COALESCE(coast::integer, 0) = 1,
  ST_Multi(ST_Force2D(ST_Transform(geom, 4326)))::geometry(MultiPolygon, 4326)
FROM staging_hydrobasins
ON CONFLICT (hybas_id) DO UPDATE SET
  source_version = EXCLUDED.source_version,
  coverage = EXCLUDED.coverage,
  level = EXCLUDED.level,
  next_down = EXCLUDED.next_down,
  main_bas = EXCLUDED.main_bas,
  pfaf_id = EXCLUDED.pfaf_id,
  sub_area_km2 = EXCLUDED.sub_area_km2,
  upstream_area_km2 = EXCLUDED.upstream_area_km2,
  basin_order = EXCLUDED.basin_order,
  endorheic = EXCLUDED.endorheic,
  coastal = EXCLUDED.coastal,
  geom = EXCLUDED.geom;

INSERT INTO rivers (
  hyriv_id, source_version, coverage, next_down, main_riv, hybas_l12, length_km,
  upstream_area_km2, discharge_cms, strahler_order, geom
)
SELECT
  hyriv_id::bigint,
  :'dataset_version',
  :'coverage',
  NULLIF(next_down::bigint, 0),
  NULLIF(main_riv::bigint, 0),
  NULLIF(hybas_l12::bigint, 0),
  GREATEST(length_km::double precision, 0),
  GREATEST(upland_skm::double precision, 0),
  dis_av_cms::double precision,
  ord_stra::smallint,
  ST_Multi(ST_Force2D(ST_Transform(geom, 4326)))::geometry(MultiLineString, 4326)
FROM staging_hydrorivers
ON CONFLICT (hyriv_id) DO UPDATE SET
  source_version = EXCLUDED.source_version,
  coverage = EXCLUDED.coverage,
  next_down = EXCLUDED.next_down,
  main_riv = EXCLUDED.main_riv,
  hybas_l12 = EXCLUDED.hybas_l12,
  length_km = EXCLUDED.length_km,
  upstream_area_km2 = EXCLUDED.upstream_area_km2,
  discharge_cms = EXCLUDED.discharge_cms,
  strahler_order = EXCLUDED.strahler_order,
  geom = EXCLUDED.geom;

INSERT INTO dataset_imports (
  dataset_name, version, level, coverage, source_url, licence,
  sha256, feature_count, status, detail
) VALUES
  ('hydrobasins', :'dataset_version', :'basin_level'::smallint, :'coverage',
   :'basins_source_url', 'HydroSHEDS licence; verify current terms at source',
   :'basins_sha256', (SELECT COUNT(*) FROM staging_hydrobasins), 'ready',
   'Imported by tools/import_hydrosheds.sh'),
  ('hydrorivers', :'dataset_version', 0, :'coverage',
   :'rivers_source_url', 'HydroSHEDS licence; verify current terms at source',
   :'rivers_sha256', (SELECT COUNT(*) FROM staging_hydrorivers), 'ready',
   'Imported by tools/import_hydrosheds.sh')
ON CONFLICT (dataset_name, version, level, coverage) DO UPDATE SET
  source_url = EXCLUDED.source_url,
  licence = EXCLUDED.licence,
  sha256 = EXCLUDED.sha256,
  feature_count = EXCLUDED.feature_count,
  status = EXCLUDED.status,
  detail = EXCLUDED.detail,
  imported_at = NOW();

DROP TABLE staging_hydrobasins;
DROP TABLE staging_hydrorivers;
COMMIT;
SQL

echo "HydroBASINS level $BASIN_LEVEL and HydroRIVERS imported for $COVERAGE."
