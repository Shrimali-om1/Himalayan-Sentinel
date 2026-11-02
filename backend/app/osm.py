"""Small deterministic parser for Overpass JSON feature responses."""
from __future__ import annotations

from typing import Any


def parse_overpass_elements(payload: dict[str, Any], retrieved_at: str) -> list[dict[str, Any]]:
    elements = payload.get("elements")
    if not isinstance(elements, list):
        raise ValueError("Overpass response has no elements array.")
    records = []
    for element in elements:
        if not isinstance(element, dict):
            continue
        tags = element.get("tags") or {}
        if not isinstance(tags, dict):
            continue
        if tags.get("bridge") or tags.get("highway"):
            category = "bridge" if tags.get("bridge") else "road"
        elif tags.get("amenity") in {"hospital", "clinic", "doctors"}:
            category = "healthcare"
        elif tags.get("amenity") == "school":
            category = "school"
        elif tags.get("building"):
            category = "building"
        else:
            continue
        geometry = element.get("geometry") or []
        if element.get("type") == "node" and element.get("lat") is not None and element.get("lon") is not None:
            geom = {"type": "Point", "coordinates": [element["lon"], element["lat"]]}
        elif geometry:
            coordinates = [[point["lon"], point["lat"]] for point in geometry if "lat" in point and "lon" in point]
            if len(coordinates) < 2:
                continue
            is_area = bool(tags.get("building")) and coordinates[0] == coordinates[-1] and len(coordinates) >= 4
            geom = {"type": "Polygon", "coordinates": [coordinates]} if is_area else {"type": "LineString", "coordinates": coordinates}
        elif element.get("center"):
            center = element["center"]
            geom = {"type": "Point", "coordinates": [center["lon"], center["lat"]]}
        else:
            continue
        osm_id = f"{element.get('type')}/{element.get('id')}"
        records.append({"id": osm_id, "category": category, "name": tags.get("name", f"{category.title()} {osm_id}"),
                       "geometry": geom, "source": "OpenStreetMap / Overpass", "source_id": osm_id,
                       "retrieved_at": retrieved_at, "classification": "real provider data", "attributes": tags})
    return records

