CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE IF NOT EXISTS analyses (
  id UUID PRIMARY KEY,
  latitude DOUBLE PRECISION NOT NULL CHECK (latitude >= -90 AND latitude <= 90),
  longitude DOUBLE PRECISION NOT NULL CHECK (longitude >= -180 AND longitude <= 180),
  radius_km SMALLINT NOT NULL CHECK (radius_km IN (1, 2, 5)),
  status TEXT NOT NULL CHECK (status IN ('queued', 'running', 'waiting_for_data', 'complete', 'failed')),
  progress SMALLINT NOT NULL DEFAULT 0 CHECK (progress BETWEEN 0 AND 100),
  message TEXT NOT NULL DEFAULT '',
  error_code TEXT,
  result JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS analyses_status_created_idx ON analyses (status, created_at);

CREATE TABLE IF NOT EXISTS weather_provenance (
  id UUID PRIMARY KEY,
  analysis_id UUID NOT NULL REFERENCES analyses(id) ON DELETE CASCADE,
  provider TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('available', 'unavailable')),
  fetched_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  source_time TIMESTAMPTZ,
  response JSONB,
  detail TEXT
);
CREATE INDEX IF NOT EXISTS weather_provenance_analysis_idx ON weather_provenance (analysis_id);
