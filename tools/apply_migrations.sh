#!/bin/sh
set -eu

: "${POSTGRES_DB:?POSTGRES_DB is required}"
: "${POSTGRES_USER:?POSTGRES_USER is required}"
: "${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is required}"

export PGPASSWORD="$POSTGRES_PASSWORD"
for migration in /migrations/*.sql; do
  echo "Applying $migration"
  psql -v ON_ERROR_STOP=1 -h db -U "$POSTGRES_USER" -d "$POSTGRES_DB" -f "$migration"
done
