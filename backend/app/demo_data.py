from __future__ import annotations

from datetime import datetime, timezone


DEMO_NOTICE = "DEMO DATA — NOT A LIVE OBSERVATION. Illustrative values exist only to demonstrate workflows."
PILOT_BOUNDARY = {
    "type": "Polygon",
    "coordinates": [[[77.080, 32.205], [77.265, 32.205], [77.265, 32.305], [77.080, 32.305], [77.080, 32.205]]],
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def study_area() -> dict:
    return {
        "id": "kullu-manali-demo",
        "name": "Kullu–Manali pilot area (illustrative boundary)",
        "description": "A configurable, bounded demonstration area near Kullu–Manali. This rectangular study boundary is illustrative and is not an administrative boundary.",
        "boundary": PILOT_BOUNDARY,
        "crs": "EPSG:4326",
        "classification": "illustrative",
        "notice": DEMO_NOTICE,
    }


def weather_summary() -> dict:
    return {
        "status": "demo_available",
        "classification": "illustrative",
        "provider": "Demonstration fixture (not Open-Meteo)",
        "time_basis": "illustrative example",
        "timestamp": "2026-08-15T06:00:00Z",
        "latest_precipitation_mm": 3.4,
        "rainfall_24h_mm": 28.0,
        "rainfall_72h_mm": 64.0,
        "forecast_24h_mm": 18.0,
        "notice": DEMO_NOTICE,
        "hourly": [
            {"time": "00:00", "precipitation": 0.0}, {"time": "03:00", "precipitation": 1.2},
            {"time": "06:00", "precipitation": 3.4}, {"time": "09:00", "precipitation": 5.8},
            {"time": "12:00", "precipitation": 4.6}, {"time": "15:00", "precipitation": 2.1},
        ],
    }


def hazard_cells() -> list[dict]:
    rows = [
        ("HC-001", 77.147, 32.246, 37, 58, 49, "moderate", "North valley slope"),
        ("HC-002", 77.174, 32.256, 59, 72, 66, "high", "River-adjacent slope"),
        ("HC-003", 77.202, 32.237, 43, 44, 44, "moderate", "East corridor"),
        ("HC-004", 77.224, 32.268, 68, 83, 76, "high", "Upper catchment"),
    ]
    return [
        {
            "id": identifier,
            "name": name,
            "geometry": {"type": "Point", "coordinates": [lon, lat]},
            "rainfall_component": rain,
            "terrain_component": terrain,
            "screening_score": score,
            "screening_classification": level,
            "data_completeness": "illustrative rainfall and terrain inputs",
            "classification": "illustrative",
            "calculation_timestamp": "2026-08-15T06:10:00Z",
            "method": "Experimental weighted heuristic (rainfall 45%, slope/terrain 55%); score is not a landslide probability.",
            "notice": DEMO_NOTICE,
        }
        for identifier, lon, lat, rain, terrain, score, level, name in rows
    ]


def infrastructure_assets() -> list[dict]:
    rows = [
        ("osm-demo-road-1", "road", "NH-3 corridor (illustrative)", 77.181, 32.253, "OpenStreetMap-style demonstration feature"),
        ("osm-demo-bridge-1", "bridge", "Beas crossing (illustrative)", 77.177, 32.255, "OpenStreetMap-style demonstration feature"),
        ("osm-demo-hospital-1", "healthcare", "Manali health facility (illustrative)", 77.188, 32.244, "OpenStreetMap-style demonstration feature"),
        ("osm-demo-school-1", "school", "Valley school (illustrative)", 77.159, 32.248, "OpenStreetMap-style demonstration feature"),
        ("osm-demo-settlement-1", "settlement", "Riverside settlement (illustrative)", 77.180, 32.257, "OpenStreetMap-style demonstration feature"),
    ]
    return [
        {
            "id": identifier, "category": category, "name": name,
            "geometry": {"type": "Point", "coordinates": [lon, lat]},
            "source": source, "source_id": identifier, "retrieved_at": "2026-08-01T09:00:00Z",
            "classification": "illustrative", "notice": DEMO_NOTICE,
        }
        for identifier, category, name, lon, lat, source in rows
    ]


def data_sources() -> list[dict]:
    return [
        {"id": "open-meteo", "provider": "Open-Meteo", "dataset": "Forecast API", "category": "weather", "classification": "forecast/model product when retrieved", "status": "available on demand", "source_url": "https://open-meteo.com/en/docs", "coverage": "Point sampling at configured pilot centroid", "record_count": None, "limitation": "Not a ground-station observation. Live fetch is separate from deterministic demo data."},
        {"id": "dem", "provider": "Manual GeoTIFF upload", "dataset": "DEM ingestion interface", "category": "terrain", "classification": "unavailable in current demo", "status": "not configured", "source_url": None, "coverage": "No DEM loaded", "record_count": 0, "limitation": "Slope cannot be derived until a valid GeoTIFF is supplied and processed."},
        {"id": "osm", "provider": "OpenStreetMap / Overpass", "dataset": "Infrastructure ingestion", "category": "infrastructure", "classification": "illustrative demo features currently displayed", "status": "demo data", "source_url": "https://www.openstreetmap.org/copyright", "coverage": "Five illustrative point features", "record_count": 5, "limitation": "Demo features are not OSM records. Production ingestion retains OSM IDs, tags, and retrieval dates."},
        {"id": "incidents", "provider": "User submissions", "dataset": "Incident reports", "category": "incidents", "classification": "unverified user report", "status": "available", "source_url": None, "coverage": "User-defined location in configured longitude/latitude guardrails", "record_count": 0, "limitation": "Submitted reports are never confirmed events without review and evidence."},
    ]


def disaster_chain() -> dict:
    return {
        "classification": "illustrative inferred relationship",
        "notice": DEMO_NOTICE,
        "nodes": [
            {"id": "rain", "label": "Heavy rainfall", "type": "environment", "evidence": "Provider forecast or reanalysis; demo rainfall is illustrative", "indicators": "24h/72h totals, provider timestamp, product type", "status": "provider data or demo"},
            {"id": "slope", "label": "Slope instability", "type": "screening", "evidence": "Rainfall and terrain inputs; local calibration is unavailable", "indicators": "DEM-derived slope and rainfall conditions", "status": "derived screening or illustrative"},
            {"id": "landslide", "label": "Potential landslide", "type": "hazard pathway", "evidence": "Screening does not confirm a landslide event", "indicators": "Reviewed incident records and field evidence", "status": "inferred pathway"},
            {"id": "obstruction", "label": "Possible river obstruction", "type": "hydrology pathway", "evidence": "No blockage observation or physical model is bundled", "indicators": "Verified river observations and channel geometry", "status": "hypothesis"},
            {"id": "flood", "label": "Potential downstream flooding", "type": "hydrology pathway", "evidence": "No physical flood simulation is implemented", "indicators": "Observed river flow and validated hydraulic model", "status": "not simulated"},
            {"id": "disruption", "label": "Infrastructure disruption", "type": "exposure", "evidence": "Proximity analysis only; no damage observations", "indicators": "Road, bridge, and facility geometry", "status": "derived proximity or illustrative"},
            {"id": "services", "label": "Settlement and service effects", "type": "impact pathway", "evidence": "No population or service impact data is bundled", "indicators": "Verified exposure and service availability information", "status": "unavailable"},
        ],
        "edges": [
            {"source": "rain", "target": "slope", "relationship": "may influence", "status": "inferred", "confidence": "context dependent"},
            {"source": "slope", "target": "landslide", "relationship": "may indicate susceptibility", "status": "hypothesis", "confidence": "uncalibrated"},
            {"source": "landslide", "target": "obstruction", "relationship": "could enter a channel", "status": "hypothesis", "confidence": "site specific"},
            {"source": "obstruction", "target": "flood", "relationship": "could alter flow", "status": "not simulated", "confidence": "unknown"},
            {"source": "flood", "target": "disruption", "relationship": "could expose infrastructure", "status": "inferred", "confidence": "unknown"},
            {"source": "disruption", "target": "services", "relationship": "could affect access", "status": "hypothesis", "confidence": "unknown"},
        ],
    }

