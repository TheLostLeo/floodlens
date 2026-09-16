CREATE TABLE IF NOT EXISTS dataset_imports (
  id BIGSERIAL PRIMARY KEY,
  dataset_name TEXT NOT NULL CHECK (dataset_name IN ('hydrobasins', 'hydrorivers', 'fabdem', 'merit_hydro')),
  version TEXT NOT NULL,
  level SMALLINT,
  coverage TEXT NOT NULL,
  source_url TEXT NOT NULL,
  licence TEXT NOT NULL,
  sha256 TEXT NOT NULL CHECK (sha256 ~ '^[0-9a-f]{64}$'),
  feature_count BIGINT NOT NULL DEFAULT 0 CHECK (feature_count >= 0),
  status TEXT NOT NULL CHECK (status IN ('importing', 'ready', 'failed')),
  detail TEXT,
  imported_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (dataset_name, version, level, coverage)
);

ALTER TABLE weather_provenance
  ADD COLUMN IF NOT EXISTS forecast_start TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS forecast_end TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS provider_timezone TEXT;

CREATE TABLE IF NOT EXISTS basins (
  hybas_id BIGINT PRIMARY KEY,
  source_version TEXT NOT NULL,
  coverage TEXT NOT NULL,
  level SMALLINT NOT NULL CHECK (level BETWEEN 1 AND 12),
  next_down BIGINT,
  main_bas BIGINT,
  pfaf_id BIGINT,
  sub_area_km2 DOUBLE PRECISION NOT NULL CHECK (sub_area_km2 >= 0),
  upstream_area_km2 DOUBLE PRECISION CHECK (upstream_area_km2 >= 0),
  basin_order SMALLINT,
  endorheic BOOLEAN NOT NULL DEFAULT FALSE,
  coastal BOOLEAN NOT NULL DEFAULT FALSE,
  geom geometry(MultiPolygon, 4326) NOT NULL
);
CREATE INDEX IF NOT EXISTS basins_level_idx ON basins (level);
CREATE INDEX IF NOT EXISTS basins_next_down_idx ON basins (level, next_down);
CREATE INDEX IF NOT EXISTS basins_geom_gix ON basins USING GIST (geom);

CREATE TABLE IF NOT EXISTS rivers (
  hyriv_id BIGINT PRIMARY KEY,
  source_version TEXT NOT NULL,
  coverage TEXT NOT NULL,
  next_down BIGINT,
  main_riv BIGINT,
  hybas_l12 BIGINT,
  length_km DOUBLE PRECISION CHECK (length_km >= 0),
  upstream_area_km2 DOUBLE PRECISION CHECK (upstream_area_km2 >= 0),
  discharge_cms DOUBLE PRECISION,
  strahler_order SMALLINT,
  geom geometry(MultiLineString, 4326) NOT NULL
);
CREATE INDEX IF NOT EXISTS rivers_hybas_l12_idx ON rivers (hybas_l12);
CREATE INDEX IF NOT EXISTS rivers_coverage_idx ON rivers (coverage);
CREATE INDEX IF NOT EXISTS rivers_geom_gix ON rivers USING GIST (geom);

CREATE TABLE IF NOT EXISTS analysis_basin_context (
  analysis_id UUID PRIMARY KEY REFERENCES analyses(id) ON DELETE CASCADE,
  context JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
