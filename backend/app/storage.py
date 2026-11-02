"""Dependency-free SQLite store for the demo runtime.

PostgreSQL/PostGIS migration is maintained separately. Keeping the demo store free
of optional geospatial wheels makes the academic walkthrough runnable on a clean
machine while never implying that SQLite has PostGIS spatial capabilities.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import settings
from .demo_data import study_area
from .config import ROOT


def _sqlite_path() -> Path:
    prefix = "sqlite:///"
    if not settings.database_url.startswith(prefix):
        return Path(__file__).resolve().parents[2] / "data" / "himalayan_sentinel.db"
    return Path(settings.database_url.removeprefix(prefix)).resolve()


class DemoStore:
    backend = "sqlite"
    def __init__(self) -> None:
        self.path = _sqlite_path()

    def connection(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def initialize(self) -> None:
        with self.connection() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS study_areas (
                  id TEXT PRIMARY KEY, name TEXT NOT NULL, description TEXT NOT NULL,
                  boundary TEXT NOT NULL, crs TEXT NOT NULL, classification TEXT NOT NULL, created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS incidents (
                  id INTEGER PRIMARY KEY AUTOINCREMENT, incident_type TEXT NOT NULL, description TEXT NOT NULL,
                  latitude REAL NOT NULL, longitude REAL NOT NULL, incident_date TEXT, verification_status TEXT NOT NULL,
                  submission_origin TEXT NOT NULL, source_url TEXT, created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS scenarios (
                  id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, rainfall_adjustment REAL NOT NULL,
                  classification TEXT NOT NULL, results TEXT NOT NULL, created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS infrastructure_assets (
                  id TEXT PRIMARY KEY, category TEXT NOT NULL, name TEXT, geometry TEXT NOT NULL,
                  source TEXT NOT NULL, source_id TEXT NOT NULL, retrieved_at TEXT NOT NULL, classification TEXT NOT NULL,
                  attributes TEXT NOT NULL DEFAULT '{}'
                );
                CREATE TABLE IF NOT EXISTS terrain_datasets (
                  id INTEGER PRIMARY KEY AUTOINCREMENT, dataset_name TEXT NOT NULL UNIQUE, file_location TEXT NOT NULL,
                  source TEXT NOT NULL, retrieved_at TEXT NOT NULL, metadata TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS data_sources (
                  id TEXT PRIMARY KEY, provider TEXT NOT NULL, dataset_name TEXT NOT NULL, source_url TEXT,
                  category TEXT NOT NULL, classification TEXT NOT NULL, status TEXT NOT NULL,
                  last_retrieval TEXT, metadata TEXT NOT NULL DEFAULT '{}'
                );
                CREATE TABLE IF NOT EXISTS ingestion_runs (
                  id INTEGER PRIMARY KEY AUTOINCREMENT, source_id TEXT NOT NULL, started_at TEXT NOT NULL,
                  completed_at TEXT NOT NULL, status TEXT NOT NULL, record_count INTEGER NOT NULL,
                  error TEXT, coverage TEXT
                );
                CREATE TABLE IF NOT EXISTS weather_records (
                  id INTEGER PRIMARY KEY AUTOINCREMENT, latitude REAL NOT NULL, longitude REAL NOT NULL,
                  recorded_at TEXT NOT NULL, precipitation_mm REAL, time_basis TEXT NOT NULL,
                  source_id TEXT NOT NULL, provenance TEXT NOT NULL,
                  UNIQUE(latitude,longitude,recorded_at,time_basis,source_id)
                );
            """)
            if settings.demo_mode:
                item = study_area()
                conn.execute(
                    "INSERT OR IGNORE INTO study_areas (id,name,description,boundary,crs,classification,created_at) VALUES (?,?,?,?,?,?,?)",
                    (item["id"], item["name"], item["description"], json.dumps(item["boundary"]), item["crs"], item["classification"], datetime.now(timezone.utc).isoformat()),
                )

    def health(self) -> dict[str, str]:
        try:
            with self.connection() as conn:
                conn.execute("SELECT 1").fetchone()
            return {"status": "connected", "driver": "sqlite", "postgis": "not applicable — SQLite demo fallback"}
        except sqlite3.Error:
            return {"status": "unavailable", "driver": "sqlite", "postgis": "not applicable — SQLite demo fallback"}

    def study_areas(self) -> list[dict[str, Any]]:
        with self.connection() as conn:
            return [{**dict(row), "boundary": json.loads(row["boundary"])} for row in conn.execute("SELECT * FROM study_areas ORDER BY CASE WHEN classification='user-provided' THEN 0 ELSE 1 END, name")]

    def study_area(self, area_id: str) -> dict[str, Any] | None:
        with self.connection() as conn:
            row = conn.execute("SELECT * FROM study_areas WHERE id = ?", (area_id,)).fetchone()
        return {**dict(row), "boundary": json.loads(row["boundary"])} if row else None

    def configure_study_area(self, item: dict[str, Any]) -> dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        with self.connection() as conn:
            conn.execute("INSERT INTO study_areas(id,name,description,boundary,crs,classification,created_at) VALUES('kullu-manali-config',?,?,?,'EPSG:4326','user-provided',?) ON CONFLICT(id) DO UPDATE SET name=excluded.name,description=excluded.description,boundary=excluded.boundary,classification='user-provided'", (item["name"],item["description"],json.dumps(item["boundary"]),now))
        return self.study_area("kullu-manali-config")

    def incidents(self) -> list[dict[str, Any]]:
        with self.connection() as conn:
            return [dict(row) for row in conn.execute("SELECT * FROM incidents ORDER BY created_at DESC")]

    def add_incident(self, item: dict[str, Any]) -> dict[str, Any]:
        values = (item["incident_type"], item["description"], item["latitude"], item["longitude"], item.get("incident_date"), "UNVERIFIED USER REPORT", "user_submitted", item.get("source_url"), datetime.now(timezone.utc).isoformat())
        with self.connection() as conn:
            cursor = conn.execute("INSERT INTO incidents (incident_type,description,latitude,longitude,incident_date,verification_status,submission_origin,source_url,created_at) VALUES (?,?,?,?,?,?,?,?,?)", values)
            row = conn.execute("SELECT * FROM incidents WHERE id = ?", (cursor.lastrowid,)).fetchone()
        return dict(row)

    def scenarios(self) -> list[dict[str, Any]]:
        with self.connection() as conn:
            rows = conn.execute("SELECT * FROM scenarios ORDER BY created_at DESC").fetchall()
        return [{**dict(row), "results": json.loads(row["results"])} for row in rows]

    def add_scenario(self, name: str, rainfall_adjustment: float, results: dict[str, Any]) -> dict[str, Any]:
        with self.connection() as conn:
            cursor = conn.execute("INSERT INTO scenarios (name,rainfall_adjustment,classification,results,created_at) VALUES (?,?,?,?,?)", (name, rainfall_adjustment, "SIMULATED SCENARIO", json.dumps(results), datetime.now(timezone.utc).isoformat()))
            row = conn.execute("SELECT * FROM scenarios WHERE id = ?", (cursor.lastrowid,)).fetchone()
        return {**dict(row), "results": json.loads(row["results"])}

    def scenario(self, scenario_id: int) -> dict[str, Any] | None:
        with self.connection() as conn:
            row = conn.execute("SELECT * FROM scenarios WHERE id = ?", (scenario_id,)).fetchone()
        return {**dict(row), "results": json.loads(row["results"])} if row else None

    def assets(self) -> list[dict[str, Any]]:
        with self.connection() as conn:
            rows = conn.execute("SELECT * FROM infrastructure_assets ORDER BY category, name").fetchall()
        if not rows:
            from .demo_data import infrastructure_assets
            return infrastructure_assets()
        return [{**dict(row), "geometry": json.loads(row["geometry"]), "attributes": json.loads(row["attributes"])} for row in rows]

    def replace_assets(self, items: list[dict[str, Any]]) -> None:
        with self.connection() as conn:
            conn.execute("DELETE FROM infrastructure_assets WHERE source = 'OpenStreetMap / Overpass'")
            conn.executemany(
                "INSERT OR REPLACE INTO infrastructure_assets (id,category,name,geometry,source,source_id,retrieved_at,classification,attributes) VALUES (?,?,?,?,?,?,?,?,?)",
                [(item["id"], item["category"], item.get("name"), json.dumps(item["geometry"]), item["source"], item["source_id"], item["retrieved_at"], item["classification"], json.dumps(item.get("attributes", {}))) for item in items],
            )

    def save_terrain(self, name: str, path: str, metadata: dict[str, Any]) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self.connection() as conn:
            conn.execute("INSERT INTO terrain_datasets(dataset_name,file_location,source,retrieved_at,metadata) VALUES(?,?,?,?,?) ON CONFLICT(dataset_name) DO UPDATE SET file_location=excluded.file_location,source=excluded.source,retrieved_at=excluded.retrieved_at,metadata=excluded.metadata", (name, path, metadata.get("source", "manually supplied GeoTIFF"), now, json.dumps(metadata)))
            conn.execute("INSERT INTO data_sources(id,provider,dataset_name,source_url,category,classification,status,last_retrieval,metadata) VALUES('dem','Manual GeoTIFF',?,NULL,'terrain','derived','available',?,?) ON CONFLICT(id) DO UPDATE SET dataset_name=excluded.dataset_name,classification='derived',status='available',last_retrieval=excluded.last_retrieval,metadata=excluded.metadata", (name, now, json.dumps(metadata)))

    def terrain(self) -> dict[str, Any] | None:
        with self.connection() as conn:
            row = conn.execute("SELECT * FROM terrain_datasets ORDER BY retrieved_at DESC LIMIT 1").fetchone()
        return {**dict(row), "metadata": json.loads(row["metadata"])} if row else None

    def source(self, source_id: str) -> dict[str, Any] | None:
        with self.connection() as conn:
            row = conn.execute("SELECT * FROM data_sources WHERE id=?", (source_id,)).fetchone()
        return {**dict(row), "metadata": json.loads(row["metadata"])} if row else None

    def record_osm_ingestion(self, items: list[dict[str, Any]], source_url: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        self.replace_assets(items)
        metadata = {"count": len(items), "attribution": "© OpenStreetMap contributors", "source_url": source_url}
        with self.connection() as conn:
            conn.execute("INSERT INTO data_sources(id,provider,dataset_name,source_url,category,classification,status,last_retrieval,metadata) VALUES('osm','OpenStreetMap / Overpass','Pilot infrastructure',?,'infrastructure','real provider data','connected',?,?) ON CONFLICT(id) DO UPDATE SET source_url=excluded.source_url,status='connected',classification='real provider data',last_retrieval=excluded.last_retrieval,metadata=excluded.metadata", (source_url, now, json.dumps(metadata)))
            conn.execute("INSERT INTO ingestion_runs(source_id,started_at,completed_at,status,record_count,coverage) VALUES('osm',?,?, 'succeeded',?,?)", (now, now, len(items), json.dumps({"source_url": source_url})))

    def record_weather(self, data: dict[str, Any]) -> None:
        now = datetime.now(timezone.utc).isoformat()
        location = data["location"]
        provenance = {"provider": data["provider"], "source_url": data["source_url"], "retrieved_at": data["retrieved_at"], "timezone": data.get("timezone"), "units": data.get("units"), "classification": data["classification"]}
        values = []
        for row in data.get("hourly", []):
            instant = datetime.fromisoformat(str(row["time"]).replace("Z", "+00:00"))
            if instant.tzinfo is None: instant = instant.replace(tzinfo=timezone.utc)
            values.append((instant.astimezone(timezone.utc).isoformat(), row.get("precipitation_mm")))
        with self.connection() as conn:
            conn.execute("INSERT INTO data_sources(id,provider,dataset_name,source_url,category,classification,status,last_retrieval,metadata) VALUES('open-meteo','Open-Meteo','Forecast API',?,'weather',?,'connected',?,?) ON CONFLICT(id) DO UPDATE SET classification=excluded.classification,status='connected',last_retrieval=excluded.last_retrieval,metadata=excluded.metadata", (data["source_url"],data["classification"],now,json.dumps(provenance)))
            conn.executemany("INSERT INTO weather_records(latitude,longitude,recorded_at,precipitation_mm,time_basis,source_id,provenance) VALUES(?,?,?,?,?,'open-meteo',?) ON CONFLICT(latitude,longitude,recorded_at,time_basis,source_id) DO UPDATE SET precipitation_mm=excluded.precipitation_mm,provenance=excluded.provenance", [(location["latitude"],location["longitude"],instant,value,data["classification"],json.dumps(provenance)) for instant,value in values])
            conn.execute("INSERT INTO ingestion_runs(source_id,started_at,completed_at,status,record_count,coverage) VALUES('open-meteo',?,?,'succeeded',?,?)", (now,now,len(values),json.dumps(location)))

    def catalog(self) -> list[dict[str, Any]]:
        from .demo_data import data_sources
        base = {item["id"]: item for item in data_sources()}
        with self.connection() as conn:
            rows = conn.execute("SELECT * FROM data_sources").fetchall()
        for row in rows:
            item = dict(row)
            previous = base.get(item["id"], {})
            count = len(self.assets()) if item["id"] == "osm" else previous.get("record_count")
            if item["id"] == "open-meteo":
                with self.connection() as conn:
                    count = conn.execute("SELECT COUNT(*) FROM weather_records").fetchone()[0]
            base[item["id"]] = {**previous, "id": item["id"], "provider": item["provider"], "dataset": item["dataset_name"], "category": item["category"], "classification": item["classification"], "status": item["status"], "source_url": item["source_url"], "last_retrieval": item["last_retrieval"], "record_count": count, "coverage": previous.get("coverage", "Configured study area"), "limitation": previous.get("limitation", "Provider coverage and completeness may vary.")}
        terrain = self.terrain()
        if terrain:
            item = base["dem"]
            item.update({"classification": "derived from provider-supplied GeoTIFF", "status": "available", "last_retrieval": terrain["retrieved_at"], "coverage": terrain["metadata"].get("coverage", "Raster footprint"), "record_count": terrain["metadata"].get("valid_pixels")})
        return list(base.values())


class PostgresStore(DemoStore):
    """PostgreSQL/PostGIS adapter used when DATABASE_URL selects PostgreSQL."""
    backend = "postgresql+postgis"

    def __init__(self) -> None:
        try:
            import psycopg
            from psycopg.rows import dict_row
        except ImportError as exc:
            raise RuntimeError("PostgreSQL DATABASE_URL requires psycopg[binary]. Install backend requirements with the postgres extra.") from exc
        self._psycopg = psycopg
        self._dict_row = dict_row
        self.dsn = settings.database_url.replace("postgresql+psycopg://", "postgresql://", 1)

    def connection(self):
        return self._psycopg.connect(self.dsn, row_factory=self._dict_row)

    def initialize(self) -> None:
        migration = ROOT / "backend" / "migrations" / "001_postgis_schema.sql"
        with self.connection() as conn:
            statements = [statement.strip() for statement in migration.read_text(encoding="utf-8").split(";") if statement.strip()]
            for statement in statements:
                conn.execute(statement)
            if settings.demo_mode:
                item = study_area()
                conn.execute("INSERT INTO study_areas(id,name,description,boundary,crs,classification) VALUES(%s,%s,%s,ST_SetSRID(ST_GeomFromGeoJSON(%s),4326),%s,%s) ON CONFLICT(id) DO NOTHING", (item["id"], item["name"], item["description"], json.dumps(item["boundary"]), item["crs"], item["classification"]))

    def health(self) -> dict[str, str]:
        try:
            with self.connection() as conn:
                postgis = conn.execute("SELECT PostGIS_Version() AS version").fetchone()
            return {"status": "connected", "driver": "postgresql", "postgis": postgis["version"] if postgis else "unavailable"}
        except Exception:
            return {"status": "unavailable", "driver": "postgresql", "postgis": "unavailable"}

    def study_areas(self) -> list[dict[str, Any]]:
        with self.connection() as conn:
            rows = conn.execute("SELECT id,name,description,ST_AsGeoJSON(boundary) AS boundary,crs,classification,created_at FROM study_areas ORDER BY CASE WHEN classification='user-provided' THEN 0 ELSE 1 END,name").fetchall()
        return [{**row, "boundary": json.loads(row["boundary"])} for row in rows]

    def study_area(self, area_id: str) -> dict[str, Any] | None:
        with self.connection() as conn:
            row = conn.execute("SELECT id,name,description,ST_AsGeoJSON(boundary) AS boundary,crs,classification,created_at FROM study_areas WHERE id=%s", (area_id,)).fetchone()
        return {**row, "boundary": json.loads(row["boundary"])} if row else None

    def configure_study_area(self, item: dict[str, Any]) -> dict[str, Any]:
        with self.connection() as conn:
            conn.execute("INSERT INTO study_areas(id,name,description,boundary,crs,classification) VALUES('kullu-manali-config',?,?,ST_SetSRID(ST_GeomFromGeoJSON(%s),4326),'EPSG:4326','user-provided') ON CONFLICT(id) DO UPDATE SET name=excluded.name,description=excluded.description,boundary=excluded.boundary,classification='user-provided'", (item["name"],item["description"],json.dumps(item["boundary"])))
        return self.study_area("kullu-manali-config")

    def incidents(self) -> list[dict[str, Any]]:
        with self.connection() as conn:
            return conn.execute("SELECT id,incident_type,description,latitude,longitude,incident_date,verification_status,submission_origin,source_url,created_at FROM incidents ORDER BY created_at DESC").fetchall()

    def add_incident(self, item: dict[str, Any]) -> dict[str, Any]:
        with self.connection() as conn:
            return conn.execute("INSERT INTO incidents(incident_type,description,latitude,longitude,location,incident_date,verification_status,submission_origin,source_url) VALUES(%s,%s,%s,%s,ST_SetSRID(ST_MakePoint(%s,%s),4326),%s,'UNVERIFIED USER REPORT','user_submitted',%s) RETURNING id,incident_type,description,latitude,longitude,incident_date,verification_status,submission_origin,source_url,created_at", (item["incident_type"],item["description"],item["latitude"],item["longitude"],item["longitude"],item["latitude"],item.get("incident_date"),item.get("source_url"))).fetchone()

    def record_weather(self, data: dict[str, Any]) -> None:
        now = datetime.now(timezone.utc)
        location = data["location"]
        rows = data.get("hourly", [])
        provenance = {"provider":data["provider"],"source_url":data["source_url"],"retrieved_at":data["retrieved_at"],"timezone":data.get("timezone"),"units":data.get("units"),"classification":data["classification"]}
        with self.connection() as conn:
            conn.execute("INSERT INTO data_sources(id,provider,dataset_name,source_url,data_category,classification,status,last_successful_retrieval,metadata) VALUES('open-meteo','Open-Meteo','Forecast API',%s,'weather',%s,'connected',%s,%s::jsonb) ON CONFLICT(id) DO UPDATE SET classification=excluded.classification,status='connected',last_successful_retrieval=excluded.last_successful_retrieval,metadata=excluded.metadata", (data["source_url"],data["classification"],now,json.dumps({**provenance,"count":len(rows)})))
            for row in rows:
                instant = datetime.fromisoformat(str(row["time"]).replace("Z", "+00:00"))
                if instant.tzinfo is None: instant = instant.replace(tzinfo=timezone.utc)
                conn.execute("INSERT INTO weather_records(location,sample_latitude,sample_longitude,recorded_at,precipitation_mm,time_basis,source_id,provenance) VALUES(ST_SetSRID(ST_MakePoint(%s,%s),4326),%s,%s,%s,%s,%s,'open-meteo',%s::jsonb) ON CONFLICT(sample_latitude,sample_longitude,recorded_at,time_basis,source_id) DO UPDATE SET precipitation_mm=excluded.precipitation_mm,provenance=excluded.provenance", (location["longitude"],location["latitude"],location["latitude"],location["longitude"],instant.astimezone(timezone.utc),row.get("precipitation_mm"),data["classification"],json.dumps(provenance)))
            conn.execute("INSERT INTO ingestion_runs(source_id,started_at,completed_at,status,record_count,coverage) VALUES('open-meteo',%s,%s,'succeeded',%s,%s::jsonb)", (now,now,len(rows),json.dumps(location)))

    def scenarios(self) -> list[dict[str, Any]]:
        with self.connection() as conn:
            return conn.execute("SELECT id,name,rainfall_adjustment,classification,results,created_at FROM scenarios ORDER BY created_at DESC").fetchall()

    def add_scenario(self, name: str, rainfall_adjustment: float, results: dict[str, Any]) -> dict[str, Any]:
        with self.connection() as conn:
            return conn.execute("INSERT INTO scenarios(name,rainfall_adjustment,classification,results) VALUES(%s,%s,'SIMULATED SCENARIO',%s::jsonb) RETURNING id,name,rainfall_adjustment,classification,results,created_at", (name,rainfall_adjustment,json.dumps(results))).fetchone()

    def scenario(self, scenario_id: int) -> dict[str, Any] | None:
        with self.connection() as conn:
            return conn.execute("SELECT id,name,rainfall_adjustment,classification,results,created_at FROM scenarios WHERE id=%s", (scenario_id,)).fetchone()

    def assets(self) -> list[dict[str, Any]]:
        with self.connection() as conn:
            rows = conn.execute("SELECT id,asset_category AS category,name,ST_AsGeoJSON(asset_geometry) AS geometry,source_identifier AS source_id,source_id AS data_source,retrieved_at,attributes FROM infrastructure_assets ORDER BY asset_category,name").fetchall()
        if not rows:
            from .demo_data import infrastructure_assets
            return infrastructure_assets()
        return [{"id": row["id"], "category": row["category"], "name": row["name"], "geometry": json.loads(row["geometry"]), "source_id": row["source_id"], "source": "OpenStreetMap / Overpass", "retrieved_at": row["retrieved_at"].isoformat() if row["retrieved_at"] else None, "classification": "real provider data", "attributes": row["attributes"]} for row in rows]

    def assets_within(self, longitude: float, latitude: float, buffer_meters: int, category: str | None = None) -> list[dict[str, Any]] | None:
        query = "SELECT id,asset_category AS category,name,ST_AsGeoJSON(asset_geometry) AS geometry,source_identifier AS source_id,retrieved_at,attributes,ST_Distance(asset_geometry::geography,ST_SetSRID(ST_MakePoint(%s,%s),4326)::geography) AS distance_meters FROM infrastructure_assets WHERE ST_DWithin(asset_geometry::geography,ST_SetSRID(ST_MakePoint(%s,%s),4326)::geography,%s)"
        args: list[Any] = [longitude, latitude, longitude, latitude, buffer_meters]
        if category:
            query += " AND asset_category=%s"
            args.append(category)
        query += " ORDER BY distance_meters"
        with self.connection() as conn:
            has_ingested = conn.execute("SELECT EXISTS(SELECT 1 FROM data_sources WHERE id='osm' AND classification='real provider data') AS found").fetchone()["found"]
            if not has_ingested:
                return None
            rows = conn.execute(query, tuple(args)).fetchall()
        return [{"id":row["id"],"category":row["category"],"name":row["name"],"geometry":json.loads(row["geometry"]),"source_id":row["source_id"],"source":"OpenStreetMap / Overpass","retrieved_at":row["retrieved_at"].isoformat() if row["retrieved_at"] else None,"classification":"real provider data","attributes":row["attributes"],"distance_meters":round(row["distance_meters"])} for row in rows]

    def replace_assets(self, items: list[dict[str, Any]]) -> None:
        with self.connection() as conn:
            conn.execute("DELETE FROM infrastructure_assets WHERE source_identifier LIKE 'node/%' OR source_identifier LIKE 'way/%' OR source_identifier LIKE 'relation/%'")
            for item in items:
                conn.execute("INSERT INTO infrastructure_assets(id,asset_category,name,asset_geometry,source_identifier,source_id,retrieved_at,attributes) VALUES(%s,%s,%s,ST_SetSRID(ST_GeomFromGeoJSON(%s),4326),%s,%s,%s,%s::jsonb) ON CONFLICT(id) DO UPDATE SET asset_category=excluded.asset_category,name=excluded.name,asset_geometry=excluded.asset_geometry,retrieved_at=excluded.retrieved_at,attributes=excluded.attributes", (item["id"],item["category"],item.get("name"),json.dumps(item["geometry"]),item["source_id"],"osm",item["retrieved_at"],json.dumps(item.get("attributes",{}))))

    def record_osm_ingestion(self, items: list[dict[str, Any]], source_url: str) -> None:
        now = datetime.now(timezone.utc)
        metadata = {"count": len(items), "attribution": "© OpenStreetMap contributors", "source_url": source_url}
        with self.connection() as conn:
            conn.execute("INSERT INTO data_sources(id,provider,dataset_name,source_url,data_category,classification,status,last_successful_retrieval,metadata) VALUES('osm','OpenStreetMap / Overpass','Pilot infrastructure',%s,'infrastructure','real provider data','connected',%s,%s::jsonb) ON CONFLICT(id) DO UPDATE SET source_url=excluded.source_url,status='connected',classification='real provider data',last_successful_retrieval=excluded.last_successful_retrieval,metadata=excluded.metadata", (source_url,now,json.dumps(metadata)))
            conn.execute("INSERT INTO ingestion_runs(source_id,started_at,completed_at,status,record_count,coverage) VALUES('osm',%s,%s,'succeeded',%s,%s::jsonb)", (now,now,len(items),json.dumps({"source_url":source_url})))
        self.replace_assets(items)

    def save_terrain(self, name: str, path: str, metadata: dict[str, Any]) -> None:
        now = datetime.now(timezone.utc)
        with self.connection() as conn:
            conn.execute("INSERT INTO data_sources(id,provider,dataset_name,source_url,data_category,classification,status,last_successful_retrieval,metadata) VALUES('dem','Manual GeoTIFF',%s,NULL,'terrain','derived','available',%s,%s::jsonb) ON CONFLICT(id) DO UPDATE SET dataset_name=excluded.dataset_name,status='available',classification='derived',last_successful_retrieval=excluded.last_successful_retrieval,metadata=excluded.metadata", (name,now,json.dumps(metadata)))
            conn.execute("INSERT INTO terrain_datasets(dataset_name,file_location,crs,source_id,processing_metadata,retrieved_at) VALUES(%s,%s,%s,'dem',%s::jsonb,%s) ON CONFLICT(dataset_name) DO UPDATE SET file_location=excluded.file_location,crs=excluded.crs,processing_metadata=excluded.processing_metadata,retrieved_at=excluded.retrieved_at", (name,path,metadata.get("analysis_crs"),json.dumps(metadata),now))

    def terrain(self) -> dict[str, Any] | None:
        with self.connection() as conn:
            row = conn.execute("SELECT dataset_name,file_location,source_id,processing_metadata,retrieved_at FROM terrain_datasets ORDER BY id DESC LIMIT 1").fetchone()
        if not row: return None
        retrieved = row["retrieved_at"]
        return {"dataset_name":row["dataset_name"],"file_location":row["file_location"],"source":row["source_id"],"retrieved_at":retrieved.isoformat() if retrieved else None,"metadata":row["processing_metadata"]}

    def catalog(self) -> list[dict[str, Any]]:
        from .demo_data import data_sources
        base = {item["id"]:item for item in data_sources()}
        with self.connection() as conn:
            rows = conn.execute("SELECT id,provider,dataset_name,source_url,data_category,classification,status,last_successful_retrieval,metadata FROM data_sources").fetchall()
        for row in rows:
            metadata=row["metadata"] or {}
            item = {**base.get(row["id"],{}),"id":row["id"],"provider":row["provider"],"dataset":row["dataset_name"],"source_url":row["source_url"],"category":row["data_category"],"classification":row["classification"],"status":row["status"],"last_retrieval":row["last_successful_retrieval"].isoformat() if row["last_successful_retrieval"] else None,"record_count":metadata.get("count")}
            base[row["id"]]=item
        return list(base.values())


store = PostgresStore() if settings.database_url.startswith(("postgresql://", "postgresql+psycopg://")) else DemoStore()

