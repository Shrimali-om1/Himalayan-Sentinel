from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

import httpx
import pytest

from app import services
from app.demo_data import hazard_cells
from app.storage import DemoStore


def test_screening_score_range_missing_and_invalid_inputs():
    assert services.calculate_screening_score(100, 100) == 100
    assert services.calculate_screening_score(0, 0) == 0
    assert services.calculate_screening_score(None, 80) is None
    with pytest.raises(ValueError):
        services.calculate_screening_score(101, 20)


def test_screening_fixture_values_match_documented_formula():
    for cell in hazard_cells():
        expected = round(cell["rainfall_component"] * 0.45 + cell["terrain_component"] * 0.55)
        assert cell["screening_score"] == expected


def test_scenario_rainfall_assumption_changes_scores_monotonically():
    baseline = services.calculate_scenario(0)
    wetter = services.calculate_scenario(50)
    assert all(high["scenario_score"] >= low["scenario_score"] for low, high in zip(baseline["cells"], wetter["cells"]))
    assert wetter["classification"] == "SIMULATED SCENARIO"
    assert wetter["thresholds"]["classification"] == "illustrative only"


def test_weather_provider_error_is_reported_without_demo_substitution(monkeypatch):
    class FakeResponse:
        status_code = 429
        def raise_for_status(self):
            request = httpx.Request("GET", "https://example.test")
            response = httpx.Response(429, request=request)
            raise httpx.HTTPStatusError("rate limited", request=request, response=response)

    class FakeClient:
        def __init__(self, **kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): return None
        async def get(self, *args, **kwargs): return FakeResponse()

    services._weather_cache.clear()
    monkeypatch.setattr(services.httpx, "AsyncClient", FakeClient)
    result = asyncio.run(services.get_open_meteo_weather(32.24, 77.19))
    assert result["status"] == "unavailable"
    assert result["classification"] == "no data"
    assert "substituted" in result["notice"]


def test_weather_rollups_require_full_nonmissing_hourly_windows(monkeypatch, tmp_path):
    current = datetime(2026, 11, 2, 12, tzinfo=timezone.utc)
    times = [(current - timedelta(hours=72) + timedelta(hours=i)).strftime("%Y-%m-%dT%H:%M") for i in range(1, 97)]
    amounts = [1.0] * 96

    class FakeResponse:
        def raise_for_status(self): pass
        def json(self):
            return {"timezone":"UTC", "current":{"time":current.strftime("%Y-%m-%dT%H:%M"),"precipitation":1.0},
                    "hourly_units":{"precipitation":"mm"}, "hourly":{"time":times,"precipitation":amounts}}

    class FakeClient:
        def __init__(self, **kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): return None
        async def get(self, *args, **kwargs): return FakeResponse()

    services._weather_cache.clear()
    monkeypatch.setattr(services.httpx, "AsyncClient", FakeClient)
    local_store = DemoStore()
    local_store.path = tmp_path / "weather.db"
    local_store.initialize()
    monkeypatch.setattr(services, "store", local_store)
    result = asyncio.run(services.get_open_meteo_weather(32.241, 77.191))
    assert result["rainfall_24h_mm"] == 24.0
    assert result["rainfall_72h_mm"] == 72.0
    assert result["forecast_24h_mm"] == 24.0
    assert result["completeness"]["past_72h_complete"] is True

    services._weather_cache.clear()
    amounts[0] = None
    result = asyncio.run(services.get_open_meteo_weather(32.242, 77.192))
    assert result["rainfall_72h_mm"] is None
    assert result["completeness"]["past_72h_complete"] is False
