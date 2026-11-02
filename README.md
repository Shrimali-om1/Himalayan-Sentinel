# Himalayan Sentinel

Himalayan Sentinel is an experimental compound-hazard intelligence and geospatial risk-screening capstone for a bounded Kullu–Manali pilot. It combines a Next.js/MapLibre interface and FastAPI service for weather provenance, transparent screening, infrastructure proximity, disaster-chain hypotheses, scenarios, reports, and unverified incident submissions.

> **This is not an official warning system.** The bundled records are permanently labelled **DEMO DATA — NOT A LIVE OBSERVATION**. Screening scores are not landslide probabilities, disaster confirmations, or instructions for emergency action.

## What works now

- Eight-page responsive frontend with MapLibre layers, source register, interactive chain nodes, scenario calculation, report generator, and incident form.
- FastAPI endpoints with Pydantic validation, CORS, OpenAPI documentation, error handling, and a dependency-free SQLite deterministic demo fallback.
- A live, cached Open-Meteo forecast connector at `/api/weather/live`, used on the Situation Room and hazard pages. If unavailable, the UI falls back to a separately labelled demo fixture.
- A bounded local DEM workflow at `backend/scripts/process_dem.py` that checks study-area overlap, reprojects to UTM 43N, masks outside the pilot polygon, calculates slope degrees, saves a slope GeoTIFF, and persists processing metadata.
- A bounded Overpass workflow at `backend/scripts/ingest_osm.py` that retrieves and upserts roads, bridges, healthcare, schools, and buildings with OSM identifiers, tags, retrieval time, and attribution.
- An optional PostgreSQL/PostGIS adapter selected by backend-only `DATABASE_URL`; SQLite remains the default demo database.
- Demonstration hazard cells, assets, rainfall, and chain relationships with provenance labels.
- Postgres/PostGIS-oriented schema migration for moving from the demo fallback to production-style spatial storage.

## Quick start (PowerShell)

Internet access to npm and PyPI is required once to install packages. Node.js 22+ is recommended for the current MapLibre dependency tree; Python 3.14 was used for backend verification.

```powershell
# Terminal 1
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Terminal 2
cd frontend
npm install
Copy-Item .env.local.example .env.local
npm run dev
```

Open [http://localhost:3000](http://localhost:3000), then inspect API documentation at [http://localhost:8000/docs](http://localhost:8000/docs).

The local demo database is created and seeded automatically on API startup. To seed explicitly, run `python scripts/seed_demo.py` from `backend` after dependencies are installed.

## Ingestion workflows

```powershell
cd backend
python scripts/process_dem.py D:\path\to\licensed-dem.tif --source "Dataset title and provider"
python scripts/ingest_osm.py
```

The DEM processing command expects a valid GeoTIFF overlapping the configured pilot. The default boundary is illustrative; supply/review a study boundary before interpreting any raster summary. The Overpass workflow makes one bounded query and caches records locally; avoid frequent repeated runs and follow Overpass usage guidance. OSM feature counts describe retrieved records only.
If the default Overpass host is unavailable, set backend `OVERPASS_URL` to another global-coverage endpoint listed by the [OpenStreetMap Overpass API wiki](https://wiki.openstreetmap.org/wiki/Overpass_API). The endpoint is configurable; public instances can be overloaded.

## PostGIS path

The app runs without Docker using SQLite only for its deterministic demo. For PostgreSQL/PostGIS, start the optional `docker-compose.yml` service (or use a native PostGIS server), set backend `DATABASE_URL` to a PostgreSQL URL such as `postgresql+psycopg://user:password@localhost:5432/himalayan_sentinel`, and start FastAPI. The startup adapter applies `backend/migrations/001_postgis_schema.sql`. PostGIS is required for persisted geometries, GIST indexes, and spatial exposure queries. Never place this URL in the frontend environment.

## Test and verify

```powershell
cd backend
pytest -q

cd ..\frontend
npm run typecheck
npm run lint
npm run test
npm run test:contracts
npm run build
```

The backend suite does not call external weather or map services. Frontend `npm run test` runs component tests, while `npm run test:contracts` checks source-level UI and API contracts; the production routes, live weather presentation, and map were also checked in the browser. See [docs/SETUP.md](docs/SETUP.md) for environment details, [docs/DATA_SOURCES.md](docs/DATA_SOURCES.md) for provenance, and [docs/DEMONSTRATION_GUIDE.md](docs/DEMONSTRATION_GUIDE.md) for the presentation flow.

## Structure

```text
frontend/                 Next.js App Router interface
backend/app/              FastAPI API, models, services, demo fixtures
backend/tests/            deterministic endpoint tests
backend/migrations/       PostGIS-oriented schema migration
data/                     local raw, processed, raster locations (ignored)
docs/                     setup, architecture, methodology, limitations, guide
```

## Environment variables

Copy `.env.example` / `backend/.env.example`. `DATABASE_URL`, `ALLOWED_ORIGINS`, and `DEMO_MODE` are supported. No API key is currently required for Open-Meteo. Do not put database credentials in the frontend.

