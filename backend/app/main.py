from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from shapely.geometry import shape

from .config import settings
from .demo_data import DEMO_NOTICE, hazard_cells, weather_summary
from .schemas import IncidentCreate, ScenarioCreate, StudyAreaConfigure
from .services import calculate_scenario, chain_data, exposure_summary, get_open_meteo_weather
from .storage import store


@asynccontextmanager
async def lifespan(_: FastAPI):
    store.initialize()
    yield


app = FastAPI(title="Himalayan Sentinel API", version="0.1.0", description="Experimental compound-hazard screening research prototype. Not an official warning system.", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.allowed_origins, allow_credentials=False, allow_methods=["GET", "POST", "PUT"], allow_headers=["Content-Type"])


@app.get("/api/health")
def health() -> dict:
    sources = {item["id"]: item for item in store.catalog()}
    return {"status": "healthy", "service": "himalayan-sentinel-api", "database": store.health(), "demo_mode": settings.demo_mode, "timestamp": datetime.now(timezone.utc).isoformat(), "external_sources": {"open_meteo": sources.get("open-meteo", {}).get("status", "available on demand"), "osm": sources.get("osm", {}).get("status", "not ingested"), "dem": sources.get("dem", {}).get("status", "not configured")}}


@app.get("/api/study-areas")
def list_study_areas() -> dict:
    return {"data": [{**item, "notice": DEMO_NOTICE if item["classification"] == "illustrative" else None} for item in store.study_areas()]}


@app.put("/api/study-areas/configure")
def configure_study_area(payload: StudyAreaConfigure) -> dict:
    geometry = payload.boundary.get("geometry") if payload.boundary.get("type") == "Feature" else payload.boundary
    if not isinstance(geometry, dict) or geometry.get("type") not in {"Polygon", "MultiPolygon"}:
        raise HTTPException(status_code=422, detail="Boundary must be a GeoJSON Polygon, MultiPolygon, or Feature with one of those geometries.")
    try:
        polygon = shape(geometry)
        west, south, east, north = polygon.bounds
        if polygon.is_empty or not polygon.is_valid or west < 74 or east > 80 or south < 30 or north > 35 or east - west > 1 or north - south > 1:
            raise ValueError
    except Exception as exc:
        raise HTTPException(status_code=422, detail="Study area must be a valid, bounded polygon within the Kullu–Manali pilot guardrails (74–80°E, 30–35°N; at most 1° each direction).") from exc
    item = store.configure_study_area({"name": payload.name, "description": payload.description, "boundary": geometry})
    return {"data": item, "notice": "User-provided study boundary stored in EPSG:4326. Verify its source and coverage before analysis."}


@app.get("/api/study-areas/{area_id}")
def get_study_area(area_id: str) -> dict:
    item = store.study_area(area_id)
    if not item:
        raise HTTPException(status_code=404, detail="Study area not found")
    return {"data": {**item, "notice": DEMO_NOTICE if item["classification"] == "illustrative" else None}}


@app.get("/api/weather/summary")
def weather_demo() -> dict:
    return {"data": weather_summary()}


@app.get("/api/weather/live")
async def weather_live(latitude: float | None = Query(None, ge=30, le=35), longitude: float | None = Query(None, ge=74, le=80)) -> dict:
    if latitude is None or longitude is None:
        area = store.study_areas()[0]
        centroid = shape(area["boundary"]).centroid
        latitude, longitude = centroid.y, centroid.x
    return {"data": await get_open_meteo_weather(latitude, longitude)}


@app.get("/api/terrain/status")
def terrain_status() -> dict:
    terrain = store.terrain()
    if terrain:
        return {"data": {"status": "available", "classification": "derived", "dataset": terrain["dataset_name"], "source": terrain["source"], "retrieved_at": terrain["retrieved_at"], **terrain["metadata"]}}
    return {"data": {"status": "not_configured", "classification": "no terrain dataset", "dataset": None, "notice": "No DEM GeoTIFF has been loaded. Terrain/slope results in the demo screening fixture are illustrative only.", "ingestion": "Run python scripts/process_dem.py path/to/dem.tif from backend/."}}


@app.get("/api/terrain/analysis")
def terrain_analysis() -> dict:
    terrain = store.terrain()
    if not terrain:
        return {"data": {"status": "unavailable", "classification": "no derived terrain data", "features": [], "notice": "DEM processing is intentionally not simulated as observed terrain."}}
    return {"data": {"status": "available", "classification": "derived terrain summary", "features": [], "summary": terrain["metadata"], "notice": "Summary statistics are from the processed raster footprint; per-cell hazard analysis remains illustrative."}}


@app.get("/api/hazard/screening")
def hazard_screening() -> dict:
    return {"data": {"cells": hazard_cells(), "methodology": "Experimental, configurable weighted screening heuristic; it is not a landslide probability or official warning.", "formula": "score = 0.45 × rainfall_component + 0.55 × terrain_component", "weights": {"rainfall": 0.45, "terrain": 0.55}, "component_range": [0, 100], "classification_thresholds": {"high": ">=65", "moderate": "40–64", "low": "<40", "classification": "illustrative only"}, "data_completeness": "Illustrative demo inputs only", "notice": DEMO_NOTICE}}


@app.get("/api/hazard/cells")
def hazard_cells_endpoint() -> dict:
    return {"data": hazard_cells()}


@app.get("/api/exposure/summary")
def exposure(cell_id: str = "HC-002", buffer_meters: int = Query(2000, ge=100, le=10_000), category: str | None = None) -> dict:
    try:
        cell = next((item for item in hazard_cells() if item["id"] == cell_id), None)
        if not cell:
            raise ValueError("Unknown hazard cell")
        longitude, latitude = cell["geometry"]["coordinates"]
        if hasattr(store, "assets_within"):
            selected_assets = store.assets_within(longitude, latitude, buffer_meters, category)
        else:
            selected_assets = None
        if selected_assets is None:
            selected_assets = store.assets()
            if category:
                selected_assets = [item for item in selected_assets if item.get("category") == category]
        return {"data": exposure_summary(cell_id, buffer_meters, selected_assets)}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/exposure/assets")
def assets(category: str | None = None) -> dict:
    items = store.assets()
    if category:
        items = [item for item in items if item.get("category") == category]
    real = bool(items) and all(item.get("classification") == "real provider data" for item in items)
    return {"data": items, "meta": {"classification": "real provider data" if real else "illustrative", "attribution": "© OpenStreetMap contributors" if real else None, "notice": "OSM coverage can be incomplete." if real else DEMO_NOTICE}}


@app.get("/api/disaster-chain")
def disaster_chain() -> dict:
    return {"data": chain_data()}


@app.get("/api/incidents")
def list_incidents() -> dict:
    return {"data": store.incidents(), "meta": {"notice": "Only user submissions are shown in this seed database. They remain UNVERIFIED USER REPORTS until reviewed."}}


@app.post("/api/incidents", status_code=201)
def create_incident(payload: IncidentCreate) -> dict:
    item = store.add_incident({**payload.model_dump(), "source_url": str(payload.source_url) if payload.source_url else None})
    return {"data": item, "notice": "Submission recorded as UNVERIFIED USER REPORT. It is not a confirmed incident."}


@app.get("/api/scenarios")
def list_scenarios() -> dict:
    return {"data": store.scenarios()}


@app.post("/api/scenarios", status_code=201)
def create_scenario(payload: ScenarioCreate) -> dict:
    return {"data": store.add_scenario(payload.name, payload.rainfall_adjustment, calculate_scenario(payload.rainfall_adjustment))}


@app.get("/api/scenarios/{scenario_id}")
def get_scenario(scenario_id: int) -> dict:
    item = store.scenario(scenario_id)
    if not item:
        raise HTTPException(status_code=404, detail="Scenario not found")
    return {"data": item}


@app.post("/api/reports/generate")
async def generate_report() -> dict:
    generated_at = datetime.now(timezone.utc).isoformat()
    area = store.study_areas()[0] if store.study_areas() else {"name": "Study area unavailable", "classification": "unavailable"}
    weather = await get_open_meteo_weather()
    terrain = store.terrain()
    summary = exposure_summary(asset_rows=store.assets())
    scenarios = store.scenarios()
    screening = hazard_screening()["data"]
    source_lines = [f"- {item['provider']}: {item['status']} ({item['classification']})" for item in store.catalog()]
    weather_section = (
        f"- Provider: {weather['provider']} ({weather['classification']})\n- Retrieved: {weather.get('retrieved_at', 'unavailable')}\n- Previous 24h: {weather.get('rainfall_24h_mm', 'unavailable')} mm\n- Previous 72h: {weather.get('rainfall_72h_mm', 'unavailable')} mm\n- Next 24h: {weather.get('forecast_24h_mm', 'unavailable')} mm"
        if weather["status"] == "connected" else "- No live weather is available; no live measurement is reported."
    )
    terrain_section = f"- Dataset: {terrain['dataset_name']}\n- Mean slope: {terrain['metadata'].get('slope_mean_degrees', 'unavailable')} degrees\n- Coverage: {terrain['metadata'].get('valid_coverage_percent', 'unavailable')}%" if terrain else "- No DEM has been ingested. Terrain values in the bundled screening fixture are illustrative."
    scenario_section = f"- Most recent: {scenarios[0]['name']} ({scenarios[0]['classification']}, rainfall adjustment {scenarios[0]['rainfall_adjustment']}%)." if scenarios else "- No saved scenario is available."
    document = "\n".join([
        "# Himalayan Sentinel — Research Screening Summary", "", f"Generated: {generated_at}",
        "", "## Classification and scope", f"- Study area: {area['name']} ({area['classification']})",
        "- This is an experimental research prototype, not an official warning or emergency decision service.",
        "", "## Data sources", *source_lines,
        "", "## Weather", weather_section,
        "", "## Terrain", terrain_section,
        "", "## Experimental screening", f"- Cells in current response: {len(screening['cells'])}",
        f"- Method: {screening['methodology']}", "- Scores are not calibrated landslide probabilities.",
        "", "## Infrastructure proximity", f"- Assets within selected illustrative 2,000 m buffer: {len(summary['assets'])}.",
        f"- Classification: {summary['classification']}. Proximity is not confirmed damage. {summary['notice']}",
        "", "## Disaster-chain interpretation", "Rainfall, slope screening, a potential landslide pathway, river obstruction, downstream flooding, and infrastructure effects are separate stages. Available links express hypotheses and do not establish that an event occurred.",
        "", "## Scenario", scenario_section,
        "", "## Missing data and limitations", "No calibrated local probability model, validated thresholds, or physical flood simulation is implemented. OSM coverage can be incomplete. User reports remain unverified. Data gaps do not imply absence of hazards or infrastructure.",
        "", "## Methodology", screening["methodology"],
    ])
    return {"data": {"format": "markdown", "document": document, "classification": "deterministic research report; includes provider data only when available", "generated_at": generated_at}}


@app.get("/api/data-sources")
def data_sources() -> dict:
    return {"data": store.catalog()}


@app.get("/api/data-sources/status")
def data_source_status() -> dict:
    return {"data": [{"id": item["id"], "status": item["status"], "classification": item["classification"], "limitation": item["limitation"]} for item in store.catalog()]}

