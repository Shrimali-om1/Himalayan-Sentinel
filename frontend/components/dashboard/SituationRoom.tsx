"use client";

import { useCallback, useEffect, useState } from "react";
import type { ReactNode } from "react";
import { AlertTriangle, CloudRain, MapPinned, Mountain, RefreshCw } from "lucide-react";
import { RainfallChart } from "@/components/charts/RainfallChart";
import { SentinelMap } from "@/components/maps/SentinelMap";
import { PageHeader } from "@/components/shared/PageHeader";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { api } from "@/lib/api";
import type { HazardCell, PointFeature, Weather } from "@/types";

type Source = Record<string, unknown>;
type StudyArea = { id: string; name: string; boundary: { type: string; coordinates: unknown }; classification: string };
type Load = { weather: Weather; cells: HazardCell[]; assets: PointFeature[]; sources: Source[]; area: StudyArea };
type LiveWeather = { status: string; provider: string; classification: string; retrieved_at?: string; current?: { time?: string; precipitation?: number | null }; hourly: { time: string; precipitation_mm: number | null }[]; rainfall_24h_mm: number | null; rainfall_72h_mm: number | null; forecast_24h_mm: number | null; units?: string; timezone?: string; notice: string };

export function SituationRoom() {
  const [data, setData] = useState<Load | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selection, setSelection] = useState<{ title: string; detail: string } | null>(null);
  const load = useCallback(async () => {
    setError(null);
    try {
      const [demo, live, hazard, assets, sources, areas] = await Promise.all([
        api<{ data: Weather }>("/weather/summary"),
        api<{ data: LiveWeather }>("/weather/live").catch(() => null),
        api<{ data: { cells: HazardCell[] } }>("/hazard/screening"),
        api<{ data: PointFeature[] }>("/exposure/assets"),
        api<{ data: Source[] }>("/data-sources"),
        api<{ data: StudyArea[] }>("/study-areas"),
      ]);
      const measured = live?.data.status === "connected" ? live.data : null;
      const weather: Weather = measured ? {
        status: measured.status, classification: measured.classification, provider: measured.provider,
        timestamp: measured.current?.time ?? measured.retrieved_at ?? "timestamp unavailable",
        rainfall_24h_mm: measured.rainfall_24h_mm, rainfall_72h_mm: measured.rainfall_72h_mm,
        forecast_24h_mm: measured.forecast_24h_mm, latest_precipitation_mm: measured.current?.precipitation ?? null,
        units: measured.units ?? "mm", timezone: measured.timezone ?? "UTC",
        hourly: measured.hourly.map(row => ({ time: row.time.slice(11, 16), precipitation: row.precipitation_mm })), notice: measured.notice,
      } : { ...demo.data, status: live ? live.data.status : "unavailable", classification: "illustrative", notice: `${demo.data.notice} Live Open-Meteo data is currently unavailable; this chart uses a separate deterministic fixture.` };
      setData({ weather, cells: hazard.data.cells, assets: assets.data, sources: sources.data, area: areas.data[0] });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to reach the API");
    }
  }, []);
  useEffect(() => { void load(); }, [load]);
  const value = (amount: number | null | undefined) => amount == null ? "Unavailable" : `${amount} mm`;
  return <><PageHeader eyebrow="Operational overview" title="Situation Room" description="Weather conditions, experimental screening, and mapped infrastructure for the selected pilot area." />
    {error && <div className="error" role="alert">API unavailable: {error}. Start the FastAPI backend on port 8000, then <button className="button ghost" onClick={() => void load()}>retry</button>.</div>}
    {!data && !error && <div className="loading">Loading study area and available provider data…</div>}
    {data && <><div className="notice section-space">Selected area: <strong>{data.area.name}</strong> · boundary classification: {data.area.classification}. {data.area.classification === "illustrative" ? "The outline is a demonstration rectangle, not an administrative boundary." : ""}</div>
      <div className="grid stats"><Metric icon={<CloudRain size={18}/>} label={`Rainfall · previous 24h · ${data.weather.classification}`} value={value(data.weather.rainfall_24h_mm)} sub={`${data.weather.provider} · ${data.weather.timezone ?? "UTC"}`}/><Metric icon={<Mountain size={18}/>} label="High screening cells" value={`${data.cells.filter(c => c.screening_classification === "high").length}`} sub="Experimental classifications"/><Metric icon={<MapPinned size={18}/>} label="Mapped infrastructure features" value={`${data.assets.length}`} sub={data.assets.every(a => a.classification === "real provider data") ? "OSM provider records; may be incomplete" : "Illustrative demo features"}/><Metric icon={<AlertTriangle size={18}/>} label="DEM availability" value="Check source register" sub="Terrain status is shown on Data Sources"/></div>
      <div className="grid two"><section className="card"><div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}><h2>Map workspace</h2><button className="button ghost" onClick={() => void load()}><RefreshCw size={14} /> Refresh</button></div><SentinelMap hazards={data.cells} assets={data.assets} boundary={data.area.boundary} onSelect={setSelection}/>{selection && <div className="method section-space"><strong>{selection.title}</strong><br />{selection.detail}</div>}</section><section className="card"><h2>Precipitation indicator</h2><p className="small">{data.weather.provider} · {data.weather.timestamp} · mm · {data.weather.classification}</p><RainfallChart weather={data.weather}/><div className="grid three"><div><div className="metric-label">Last 24h</div><strong>{value(data.weather.rainfall_24h_mm)}</strong></div><div><div className="metric-label">Last 72h</div><strong>{value(data.weather.rainfall_72h_mm)}</strong></div><div><div className="metric-label">Next 24h</div><strong>{value(data.weather.forecast_24h_mm)}</strong></div></div><p className="method section-space">{data.weather.notice}</p></section></div>
      <div className="grid two section-space"><section className="card"><h2>Screening watchlist</h2>{data.cells.length ? data.cells.map(cell => <div className="list-row" key={cell.id}><div><strong>{cell.name}</strong><p>{cell.method}</p></div><div style={{ textAlign: "right" }}><StatusBadge value={cell.screening_classification}/><div className="small muted" style={{ marginTop: 6 }}>{cell.screening_score}/100</div></div></div>) : <p className="muted">No screening cells are available.</p>}</section><section className="card"><h2>Source status</h2>{data.sources.map(source => <div className="source-row" key={String(source.id)}><div><strong>{String(source.provider)}</strong><p>{String(source.dataset)}{source.last_retrieval ? ` · retrieved ${String(source.last_retrieval)}` : ""}</p></div><StatusBadge value={String(source.id) === "open-meteo" ? (data.weather.status === "connected" ? "connected" : "unavailable; demo shown") : String(source.status)} /></div>)}</section></div></>}
  </>;
}

function Metric({ icon, label, value, sub }: { icon: ReactNode; label: string; value: string; sub: string }) { return <div className="card"><div style={{ color: "var(--mint)" }}>{icon}</div><div className="metric-label">{label}</div><div className="metric-value" style={{fontSize: value === "Unavailable" ? 20 : undefined}}>{value}</div><div className="metric-sub">{sub}</div></div>; }
