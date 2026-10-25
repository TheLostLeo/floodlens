#!/bin/sh
set -eu

: "${POSTGRES_DB:?POSTGRES_DB is required}"
: "${POSTGRES_USER:?POSTGRES_USER is required}"
: "${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is required}"

export PGPASSWORD="$POSTGRES_PASSWORD"
PSQL="psql -v ON_ERROR_STOP=1 -h db -U $POSTGRES_USER -d $POSTGRES_DB"

$PSQL <<'SQL'
\pset format unaligned
\pset tuples_only on
SELECT jsonb_pretty(jsonb_build_object(
  'generated_at', NOW(),
  'scope', 'registered imported datasets only; not global coverage',
  'datasets', COALESCE(jsonb_agg(jsonb_build_object(
    'dataset_name', dataset_name,
    'version', version,
    'level', level,
    'coverage', coverage,
    'source_url', source_url,
    'licence', licence,
    'sha256', sha256,
    'feature_count', feature_count,
    'status', status,
    'detail', detail,
    'imported_at', imported_at
  ) ORDER BY dataset_name, coverage, level), '[]'::jsonb),
  'limitations', jsonb_build_array(
    'Imported coverage is regional unless every required region has been imported and verified.',
    'Basin and river context does not prove property-level flood connectivity.',
    'FABDEM tiles must overlap the selected local assessment circle before terrain scoring is available.'
  )
))
FROM dataset_imports;
SQL
