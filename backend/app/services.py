from __future__ import annotations

import math
import asyncio
import copy
import logging
from datetime import datetime, timedelta, timezone

import httpx

from .config import settings
from .demo_data import data_sources, disaster_chain, hazard_cells, infrastructure_assets, weather_summary
from .storage import store

logger = logging.getLogger(__name__)

_weather_cache: dict[tuple[float, float], tuple[datetime, dict]] = {}
_weather_lock = asyncio.Lock()


def haversine_meters(lat_a: float, lon_a: float, lat_b: float, lon_b: float) -> float:
    """Great-circle point distance for demo fallback. Production uses ST_DWithin in PostGIS."""
    radius = 6_371_000
    phi_a, phi_b = math.radians(lat_a), math.radians(lat_b)
    delta_phi, delta_lambda = math.radians(lat_b - lat_a), math.radians(lon_b - lon_a)
    value = math.sin(delta_phi / 2) ** 2 + math.cos(phi_a) * math.cos(phi_b) * math.sin(delta_lambda / 2) ** 2
    return radius * 2 * math.atan2(math.sqrt(value), math.sqrt(1 - value))


def calculate_screening_score(rainfall_component: float | None, terrain_component: float | None) -> float | None:
    """Return the documented 45/55 heuristic score, or None when an input is missing."""
    if rainfall_component is None or terrain_component is None:
        return None
    if not 0 <= rainfall_component <= 100 or not 0 <= terrain_component <= 100:
        raise ValueError("Screening components must be between 0 and 100.")
    return round(rainfall_component * 0.45 + terrain_component * 0.55)


async def get_open_meteo_weather(latitude: float = 32.2396, longitude: float = 77.1887) -> dict:
    """Fetch provider-labelled forecast data. Failures are returned as availability metadata."""
    key = (round(latitude, 4), round(longitude, 4))
    async with _weather_lock:
        cached = _weather_cache.get(key)
        if cached and datetime.now(timezone.utc) - cached[0] < timedelta(minutes=15):
            return copy.deepcopy({**cached[1], "cache": "hit"})
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": "precipitation",
        "hourly": "precipitation",
        "past_days": 3,
        "forecast_days": 3,
        "timezone": "UTC",
    }
    try:
        async with httpx.AsyncClient(timeout=settings.request_timeout_seconds) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            payload = response.json()
        if not isinstance(payload, dict) or not isinstance(payload.get("hourly"), dict) or not isinstance(payload["hourly"].get("time"), list) or not isinstance(payload["hourly"].get("precipitation"), list):
            raise ValueError("Open-Meteo response is missing hourly time-series arrays.")
        times = payload["hourly"]["time"]
        values = payload["hourly"]["precipitation"]
        if len(times) != len(values) or not times:
            raise ValueError("Open-Meteo response has mismatched or empty hourly values.")
        rows = [{"time": time, "precipitation_mm": amount} for time, amount in zip(times, values)]
        current_payload = payload.get("current") if isinstance(payload.get("current"), dict) else {}
        current_time = datetime.fromisoformat(current_payload.get("time", datetime.now(timezone.utc).isoformat()).replace("Z", "+00:00"))
        # Provider timestamps are requested in UTC; precipitation values are preceding-hour sums.
        parsed = [(datetime.fromisoformat(str(row["time"]).replace("Z", "+00:00")), row["precipitation_mm"]) for row in rows]

        def total(start: datetime, end: datetime, expected_hours: int) -> tuple[float | None, bool]:
            entries = [(instant, value) for instant, value in parsed if start < instant <= end]
            present = [float(value) for _, value in entries if value is not None]
            complete = len(entries) >= expected_hours and len(present) == len(entries)
            return (round(sum(present), 2) if complete else None), complete

        rainfall_24h, complete_24h = total(current_time - timedelta(hours=24), current_time, 24)
        rainfall_72h, complete_72h = total(current_time - timedelta(hours=72), current_time, 72)
        forecast_24h, complete_forecast = total(current_time, current_time + timedelta(hours=24), 24)
        result = {
            "status": "connected", "classification": "forecast/model product", "provider": "Open-Meteo Forecast API",
            "source_url": "https://open-meteo.com/en/docs", "retrieved_at": datetime.now(timezone.utc).isoformat(),
            "timezone": payload.get("timezone", "UTC"), "units": payload.get("hourly_units", {}).get("precipitation", "mm"),
            "location": {"latitude": latitude, "longitude": longitude}, "current": current_payload, "hourly": rows,
            "rainfall_24h_mm": rainfall_24h, "rainfall_72h_mm": rainfall_72h, "forecast_24h_mm": forecast_24h,
            "completeness": {"past_24h_complete": complete_24h, "past_72h_complete": complete_72h, "forecast_24h_complete": complete_forecast},
            "notice": "Provider forecast/model output. It is not represented as a physical ground-station observation.",
        }
        result["cache"] = "miss"
        try:
            store.record_weather(result)
            result["persistence_status"] = "stored"
        except Exception:
            logger.exception("Live weather was retrieved but could not be persisted")
            result["persistence_status"] = "unavailable"
        async with _weather_lock:
            _weather_cache[key] = (datetime.now(timezone.utc), copy.deepcopy(result))
        return result
    except (httpx.HTTPError, ValueError, TypeError, KeyError, AttributeError):
        return {
            "status": "unavailable", "classification": "no data", "provider": "Open-Meteo Forecast API",
            "source_url": "https://open-meteo.com/en/docs", "error": "Live provider request failed or timed out.",
            "notice": "No live weather output is substituted. Use the clearly labelled demo fixture to explore the interface.",
        }


def exposure_summary(cell_id: str = "HC-002", buffer_meters: float = 2000, asset_rows: list[dict] | None = None) -> dict:
    cell = next((item for item in hazard_cells() if item["id"] == cell_id), None)
    if not cell:
        raise ValueError("Unknown hazard cell")
    lon, lat = cell["geometry"]["coordinates"]
    exposed = []
    available_assets = asset_rows if asset_rows is not None else infrastructure_assets()
    for asset in available_assets:
        geometry = asset["geometry"]
        try:
            from pyproj import Transformer
            from shapely.geometry import Point, shape
            from shapely.ops import transform
            project = Transformer.from_crs("EPSG:4326", "EPSG:32643", always_xy=True).transform
            distance = round(transform(project, shape(geometry)).distance(transform(project, Point(lon, lat))))
        except (ImportError, ValueError, TypeError):
            coordinates = geometry.get("coordinates", [])
            stack = [coordinates]
            points = []
            while stack:
                part = stack.pop()
                if isinstance(part, list) and len(part) >= 2 and all(isinstance(v, (int, float)) for v in part[:2]):
                    points.append(part[:2])
                elif isinstance(part, list):
                    stack.extend(part)
            if not points:
                continue
            distance = min(round(haversine_meters(lat, lon, point[1], point[0])) for point in points)
        if distance <= buffer_meters:
            exposed.append({**asset, "distance_meters": distance, "relationship": f"Within {buffer_meters:,} m illustrative analysis buffer"})
    categories: dict[str, int] = {}
    for asset in exposed:
        categories[asset["category"]] = categories.get(asset["category"], 0) + 1
    return {
        "hazard_cell": cell, "buffer_meters": buffer_meters, "assets": exposed, "category_counts": categories,
        "classification": "derived from provider data" if any(a.get("classification") == "real provider data" for a in available_assets) else "illustrative derived analysis",
        "method": "Geometry distance in WGS 84 / UTM zone 43N using projected asset geometries; great-circle vertex distance is the fallback. Proximity screening does not estimate damage.",
        "notice": "OSM coverage can be incomplete. Assets in this buffer are proximity matches, not confirmed impacts." if any(a.get("classification") == "real provider data" for a in available_assets) else "DEMO DATA — NOT A LIVE OBSERVATION. This is a screening proximity result, not a damage estimate.",
    }


def calculate_scenario(rainfall_adjustment: float) -> dict:
    multiplier = 1 + rainfall_adjustment / 100
    computed = []
    for cell in hazard_cells():
        adjusted_rain = min(100, round(cell["rainfall_component"] * multiplier))
        score = calculate_screening_score(adjusted_rain, cell["terrain_component"])
        category = "high" if score >= 65 else "moderate" if score >= 40 else "low"
        computed.append({**cell, "baseline_score": cell["screening_score"], "adjusted_rainfall_component": adjusted_rain, "scenario_score": score, "scenario_classification": category})
    return {
        "rainfall_adjustment_percent": rainfall_adjustment, "cells": computed,
        "summary": {"high": sum(c["scenario_classification"] == "high" for c in computed), "moderate": sum(c["scenario_classification"] == "moderate" for c in computed), "low": sum(c["scenario_classification"] == "low" for c in computed)},
        "classification": "SIMULATED SCENARIO", "thresholds": {"high": ">=65", "moderate": "40–64", "low": "<40", "classification": "illustrative only"},
        "method": "Rainfall component multiplied by scenario assumption, then combined with unchanged illustrative terrain component (45/55 weighting). Classes use illustrative cutoffs (high >=65, moderate 40–64, low <40). Not a forecast or probability.",
    }


def source_catalog() -> list[dict]:
    return data_sources()


def chain_data() -> dict:
    return disaster_chain()

