# Setup

## Environment observed during development

- Windows / PowerShell workspace
- Node.js 20.20.1 and npm 10.8.2
- Python 3.14.3
- Git, Docker CLI, and PostgreSQL 18 client installed

Docker Desktop was unavailable for PostGIS validation. PostgreSQL 18 is installed and listening locally, but its credentials were not configured and the PostGIS extension files are absent. npm registry access later recovered and the frontend dependencies were installed.
The production build, tests, and browser check passed on Node 20.20.1, but MapLibre's current style-spec dependency declares Node 22 or newer; use Node 22+ for a clean install without engine warnings.

## Local demo

1. Install Node and Python packages according to the root README.
2. Start FastAPI at port 8000. SQLite creates `data/himalayan_sentinel.db` and seeds the illustrative study area.
3. Start Next.js at port 3000.
4. Navigate through all sections. The Situation Room requests provider weather on demand and clearly labels the separate demo data when a live request fails.

## Database

For PostgreSQL/PostGIS, copy the root `.env.example` to `.env` and replace `POSTGRES_PASSWORD` with a local secret before starting `docker compose up -d postgis`. Ensure `CREATE EXTENSION postgis` is permitted, set a backend-only `DATABASE_URL=postgresql+psycopg://user:password@localhost:5432/himalayan_sentinel`, then start FastAPI. The adapter applies the idempotent SQL migration during startup. The current Windows Postgres service accepts connections but requires credentials; PostGIS files are absent, so the migration and spatial queries could not be verified in this session.

## DEM prerequisites

Use a reviewed/licensed GeoTIFF. `pip install -r requirements.txt` installs Rasterio, NumPy, PyProj, and Shapely. Run `python scripts/process_dem.py path\to\dem.tif --source "Dataset/provider"` from `backend`. It checks overlap, clips a window to the study area, reprojects to UTM 43N, derives slope in degrees, writes a GeoTIFF under `data/processed`, and stores a metadata summary. The default boundary is illustrative, and per-cell hazard scores remain demo values.

## OpenStreetMap

Run `python scripts/ingest_osm.py` from `backend` for one bounded Overpass request. Retrieved features are upserted by OSM element ID and become available through `/api/exposure/assets`. Set `OVERPASS_URL` in `backend/.env` to choose another global-coverage instance if needed. The default host returned HTTP 502 and one alternate timed out during the completion pass, so live OSM ingestion is implemented but was not successfully verified. Public Overpass servers are shared; do not schedule frequent or parallel runs.

