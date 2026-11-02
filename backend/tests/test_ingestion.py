from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import rasterio
from pyproj import Transformer
from rasterio.transform import from_origin
from shapely.geometry import Polygon, mapping

from app.osm import parse_overpass_elements
from app.storage import DemoStore
from app.terrain import process_dem


def test_overpass_parser_preserves_ids_tags_and_geometry():
    result = parse_overpass_elements({"elements":[
        {"type":"node","id":17,"lat":32.24,"lon":77.19,"tags":{"amenity":"hospital","name":"Clinic"}},
        {"type":"way","id":21,"geometry":[{"lat":32.24,"lon":77.19},{"lat":32.25,"lon":77.20}],"tags":{"highway":"primary"}},
    ]}, "2026-11-02T10:00:00Z")
    assert [row["id"] for row in result] == ["node/17", "way/21"]
    assert result[0]["category"] == "healthcare"
    assert result[0]["attributes"]["amenity"] == "hospital"
    assert result[1]["geometry"]["type"] == "LineString"


def test_osm_upsert_is_idempotent(tmp_path):
    store = DemoStore()
    store.path = tmp_path / "seed.db"
    store.initialize()
    asset = {"id":"way/4","category":"road","name":"A road","geometry":{"type":"LineString","coordinates":[[77.1,32.2],[77.2,32.3]]},"source":"OpenStreetMap / Overpass","source_id":"way/4","retrieved_at":"2026-11-02T10:00:00Z","classification":"real provider data","attributes":{"highway":"primary"}}
    store.record_osm_ingestion([asset], "https://overpass-api.de/api/interpreter")
    store.record_osm_ingestion([asset], "https://overpass-api.de/api/interpreter")
    assert len(store.assets()) == 1
    assert any(item["id"] == "osm" and item["record_count"] == 1 for item in store.catalog())


def test_dem_invalid_file_is_rejected(tmp_path):
    bad = tmp_path / "bad.tif"
    bad.write_text("not a raster", encoding="utf-8")
    boundary = mapping(Polygon([(77.0,32.0),(77.3,32.0),(77.3,32.3),(77.0,32.3)]))
    with pytest.raises(ValueError, match="Could not read DEM GeoTIFF"):
        process_dem(bad, boundary, tmp_path / "out")


def test_dem_overlap_and_slope_derivation(tmp_path):
    boundary_coords = [(77.05,32.18),(77.27,32.18),(77.27,32.32),(77.05,32.32),(77.05,32.18)]
    boundary = mapping(Polygon(boundary_coords))
    project = Transformer.from_crs("EPSG:4326","EPSG:32643",always_xy=True).transform
    west,south = project(77.0,32.15)
    east,north = project(77.3,32.35)
    width=120; height=120; xres=(east-west)/width; yres=(north-south)/height
    transform=from_origin(west,north,xres,yres)
    rows,cols=np.mgrid[0:height,0:width]
    elevation=(1000+0.1*cols*xres).astype("float32")
    elevation[40:45,:]=-9999
    path=tmp_path/"plane.tif"
    with rasterio.open(path,"w",driver="GTiff",width=width,height=height,count=1,dtype="float32",crs="EPSG:32643",transform=transform,nodata=-9999) as dst:
        dst.write(elevation,1)
    result=process_dem(path,boundary,tmp_path/"processed")
    assert result["source_crs"] == "EPSG:32643"
    assert result["valid_pixels"] < result["total_pixels"]
    assert result["slope_mean_degrees"] == pytest.approx(5.71, abs=0.7)
    assert Path(result["slope_file"]).is_file()
