"""Fetch and persist a bounded OSM feature set. Run from backend/: python scripts/ingest_osm.py"""
from __future__ import annotations

import sys
import os
from datetime import datetime, timezone
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.storage import store
from app.osm import parse_overpass_elements

ENDPOINT = os.getenv("OVERPASS_URL", "https://overpass-api.de/api/interpreter")
USER_AGENT = "HimalayanSentinelAcademicPrototype/0.1 (bounded pilot; contact: local operator)"


def main() -> None:
    store.initialize()
    area = store.study_areas()[0]
    ring = area["boundary"]["coordinates"][0]
    lons, lats = [p[0] for p in ring], [p[1] for p in ring]
    bbox = f"{min(lats)},{min(lons)},{max(lats)},{max(lons)}"
    query = f'''[out:json][timeout:40];
(
  nwr["highway"]({bbox});
  nwr["bridge"]({bbox});
  nwr["amenity"~"hospital|clinic|doctors|school"]({bbox});
  nwr["building"]({bbox});
);
out center geom;'''
    try:
        response = httpx.post(ENDPOINT, data={"data": query}, headers={"User-Agent": USER_AGENT}, timeout=50)
        response.raise_for_status()
        payload = response.json()
    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code
        retry_hint = " Wait at least 30 seconds before retrying a rate-limited request." if status in {429, 406} else ""
        raise SystemExit(
            f"Overpass returned HTTP {status}; no OSM records were stored. "
            f"Retry later or set OVERPASS_URL to another global-coverage endpoint.{retry_hint}"
        ) from exc
    except (httpx.RequestError, ValueError) as exc:
        raise SystemExit(f"Overpass request failed; no OSM records were stored: {exc}") from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("elements"), list):
        raise SystemExit("Overpass returned an unexpected payload; no OSM records were stored.")
    now = datetime.now(timezone.utc).isoformat()
    records = parse_overpass_elements(payload, now)
    store.record_osm_ingestion(records, ENDPOINT)
    print(f"Stored {len(records)} OSM features for {area['name']} ({bbox}); OSM contributors attribution required.")


if __name__ == "__main__":
    main()

