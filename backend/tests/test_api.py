import pytest
from fastapi.testclient import TestClient

from app import main
from app.storage import DemoStore


@pytest.fixture
def client(tmp_path, monkeypatch):
    local = DemoStore()
    local.path = tmp_path / "api-test.db"
    monkeypatch.setattr(main, "store", local)
    with TestClient(main.app) as test_client:
        yield test_client


def test_health_reports_database_status(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_cors_supports_both_local_frontend_origins(client):
    for origin in ("http://localhost:3000", "http://127.0.0.1:3000"):
        response = client.options("/api/health", headers={"Origin": origin, "Access-Control-Request-Method": "GET"})
        assert response.status_code == 200
        assert response.headers["access-control-allow-origin"] == origin


def test_hazard_screening_is_explicitly_illustrative(client):
    response = client.get("/api/hazard/screening")
    payload = response.json()["data"]
    assert len(payload["cells"]) == 4
    assert "not a landslide probability" in payload["methodology"]
    assert payload["cells"][0]["classification"] == "illustrative"


def test_scenario_is_marked_simulated_and_retrievable(client):
    response = client.post("/api/scenarios", json={"name": "Wet test", "rainfall_adjustment": 25})
    assert response.status_code == 201
    scenario = response.json()["data"]
    assert scenario["classification"] == "SIMULATED SCENARIO"
    assert client.get(f"/api/scenarios/{scenario['id']}").json()["data"]["name"] == "Wet test"


def test_incident_submission_stays_unverified(client):
    response = client.post("/api/incidents", json={"incident_type": "landslide", "description": "A submitted report requiring independent review.", "latitude": 32.24, "longitude": 77.19})
    assert response.status_code == 201
    assert response.json()["data"]["verification_status"] == "UNVERIFIED USER REPORT"


def test_out_of_range_incident_coordinate_is_rejected(client):
    response = client.post("/api/incidents", json={"incident_type":"landslide","description":"Coordinate falls outside pilot limits.","latitude":10,"longitude":77})
    assert response.status_code == 422


def test_user_study_boundary_is_validated_and_persisted(client):
    response = client.put("/api/study-areas/configure", json={"name":"Reviewed test area","description":"Boundary provided for validation test.","boundary":{"type":"Polygon","coordinates":[[[77.1,32.1],[77.2,32.1],[77.2,32.2],[77.1,32.2],[77.1,32.1]]]}})
    assert response.status_code == 200
    areas = client.get("/api/study-areas").json()["data"]
    assert areas[0]["name"] == "Reviewed test area"
    assert areas[0]["classification"] == "user-provided"


def test_invalid_study_boundary_is_rejected(client):
    response = client.put("/api/study-areas/configure", json={"name":"Outside","description":"Out of bounds geometry.","boundary":{"type":"Polygon","coordinates":[[[10,10],[11,10],[11,11],[10,11],[10,10]]]}})
    assert response.status_code == 422


def test_report_works_without_ai_and_states_limitations(client, monkeypatch):
    async def unavailable_weather(*args, **kwargs):
        return {"status":"unavailable","provider":"Open-Meteo Forecast API","classification":"no data"}
    monkeypatch.setattr(main, "get_open_meteo_weather", unavailable_weather)
    response = client.post("/api/reports/generate")
    report = response.json()["data"]["document"]
    assert response.status_code == 200
    assert "Data sources" in report
    assert "No calibrated local probability model" in report
    assert "No live weather is available" in report

