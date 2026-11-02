-- Run only against a reviewed PostgreSQL database with PostGIS enabled.
CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE IF NOT EXISTS study_areas (
  id TEXT PRIMARY KEY, name TEXT NOT NULL, description TEXT NOT NULL,
  boundary geometry(Geometry,4326) NOT NULL, crs TEXT NOT NULL DEFAULT 'EPSG:4326',
  classification TEXT NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS data_sources (
  id TEXT PRIMARY KEY, provider TEXT NOT NULL, dataset_name TEXT NOT NULL,
  source_url TEXT, data_category TEXT NOT NULL, classification TEXT NOT NULL,
  last_successful_retrieval TIMESTAMPTZ, status TEXT NOT NULL, metadata JSONB NOT NULL DEFAULT '{}'::jsonb
);
CREATE TABLE IF NOT EXISTS ingestion_runs (
  id BIGSERIAL PRIMARY KEY, source_id TEXT REFERENCES data_sources(id), started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  completed_at TIMESTAMPTZ, status TEXT NOT NULL, record_count INTEGER NOT NULL DEFAULT 0, error_details TEXT, coverage JSONB
);
CREATE TABLE IF NOT EXISTS weather_records (
  id BIGSERIAL PRIMARY KEY, location geometry(Point,4326) NOT NULL,
  sample_latitude DOUBLE PRECISION NOT NULL, sample_longitude DOUBLE PRECISION NOT NULL,
  recorded_at TIMESTAMPTZ NOT NULL, precipitation_mm DOUBLE PRECISION, time_basis TEXT NOT NULL,
  source_id TEXT REFERENCES data_sources(id), provenance JSONB NOT NULL DEFAULT '{}'::jsonb,
  UNIQUE(sample_latitude,sample_longitude,recorded_at,time_basis,source_id)
);
CREATE TABLE IF NOT EXISTS terrain_datasets (
  id BIGSERIAL PRIMARY KEY, dataset_name TEXT NOT NULL UNIQUE, file_location TEXT NOT NULL, resolution JSONB,
  crs TEXT, bounds geometry(Polygon,4326), source_id TEXT REFERENCES data_sources(id), processing_metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  retrieved_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS hazard_cells (
  id TEXT PRIMARY KEY, cell geometry(Geometry,4326) NOT NULL, rainfall_component DOUBLE PRECISION,
  terrain_component DOUBLE PRECISION, screening_score DOUBLE PRECISION, screening_classification TEXT,
  data_completeness TEXT, calculated_at TIMESTAMPTZ NOT NULL, provenance JSONB NOT NULL DEFAULT '{}'::jsonb
);
CREATE TABLE IF NOT EXISTS infrastructure_assets (
  id TEXT PRIMARY KEY, asset_category TEXT NOT NULL, asset_geometry geometry(Geometry,4326) NOT NULL,
  name TEXT, source_identifier TEXT UNIQUE, source_id TEXT REFERENCES data_sources(id), retrieved_at TIMESTAMPTZ, attributes JSONB NOT NULL DEFAULT '{}'::jsonb
);
CREATE TABLE IF NOT EXISTS incidents (
  id BIGSERIAL PRIMARY KEY, incident_type TEXT NOT NULL, description TEXT NOT NULL,
  latitude DOUBLE PRECISION NOT NULL, longitude DOUBLE PRECISION NOT NULL, location geometry(Point,4326) NOT NULL,
  incident_date TEXT, verification_status TEXT NOT NULL DEFAULT 'UNVERIFIED USER REPORT',
  submission_origin TEXT NOT NULL DEFAULT 'user_submitted', source_url TEXT, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS scenarios (
  id BIGSERIAL PRIMARY KEY, name TEXT NOT NULL, rainfall_adjustment DOUBLE PRECISION NOT NULL,
  classification TEXT NOT NULL DEFAULT 'SIMULATED SCENARIO', results JSONB NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS disaster_chain_records (
  id BIGSERIAL PRIMARY KEY, node_type TEXT NOT NULL, relationship_type TEXT NOT NULL, source_evidence TEXT,
  evidence_classification TEXT NOT NULL, description TEXT NOT NULL, relationship_status TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS study_areas_boundary_gix ON study_areas USING GIST(boundary);
CREATE INDEX IF NOT EXISTS weather_location_gix ON weather_records USING GIST(location);
CREATE INDEX IF NOT EXISTS terrain_bounds_gix ON terrain_datasets USING GIST(bounds);
CREATE INDEX IF NOT EXISTS hazard_cells_gix ON hazard_cells USING GIST(cell);
CREATE INDEX IF NOT EXISTS infrastructure_assets_gix ON infrastructure_assets USING GIST(asset_geometry);
CREATE INDEX IF NOT EXISTS incidents_location_gix ON incidents USING GIST(location);

