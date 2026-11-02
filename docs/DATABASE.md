# Database

The SQLite demo creates `study_areas`, `incidents`, `scenarios`, `infrastructure_assets`, `terrain_datasets`, `data_sources`, and `ingestion_runs`. Geometry is retained as GeoJSON in the SQLite fallback. `incidents` maintains status and origin; every submitted record defaults to `UNVERIFIED USER REPORT`.

The PostGIS migration in `backend/migrations/001_postgis_schema.sql` creates application tables, spatial columns, foreign keys, and GIST indexes. The selected Postgres adapter uses PostGIS `ST_DWithin` and `ST_Distance` over geography for exposure buffers. PostgreSQL runtime validation still requires the local database credentials and PostGIS extension to be available.

SQLite is not represented as PostGIS. It is strictly a local deterministic demonstration fallback.

