"use client";

import { useEffect, useMemo, useState } from "react";
import { PageHeader } from "@/components/shared/PageHeader";
import { SentinelMap } from "@/components/maps/SentinelMap";
import { RainfallChart } from "@/components/charts/RainfallChart";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { api } from "@/lib/api";
import type { HazardCell, Weather } from "@/types";

type Terrain = { status: string; classification: string; summary?: Record<string, unknown>; notice?: string };
type Live = { status: string; provider: string; classification: string; current?: { time?: string; precipitation?: number | null }; hourly: { time: string; precipitation_mm: number | null }[]; rainfall_24h_mm: number | null; rainfall_72h_mm: number | null; forecast_24h_mm: number | null; timezone?: string; units?: string; retrieved_at?: string; notice: string };
type Area = { name: string; boundary: { type: string; coordinates: unknown } };

export function HazardAnalysis() {
  const [cells, setCells] = useState<HazardCell[]>([]);
  const [weather, setWeather] = useState<Weather | null>(null);
  const [terrain, setTerrain] = useState<Terrain | null>(null);
  const [area, setArea] = useState<Area | null>(null);
  const [filter, setFilter] = useState("all");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    Promise.all([
      api<{ data: { cells: HazardCell[] } }>("/hazard/screening"),
      api<{ data: Terrain }>("/terrain/status"),
      api<{ data: Weather }>("/weather/summary"),
      api<{ data: Live }>("/weather/live").catch(() => null),
      api<{ data: Area[] }>("/study-areas"),
    ]).then(([screening, t, demo, live, areas]) => {
      if (!active) return;
      setLoading(false);
      setCells(screening.data.cells);
      setTerrain(t.data);
      setArea(areas.data[0] ?? null);
      if (live?.data.status === "connected") {
        const w = live.data;
        setWeather({
          status: w.status, classification: w.classification, provider: w.provider,
          timestamp: w.current?.time ?? w.retrieved_at ?? "timestamp unavailable",
          rainfall_24h_mm: w.rainfall_24h_mm, rainfall_72h_mm: w.rainfall_72h_mm,
          forecast_24h_mm: w.forecast_24h_mm, latest_precipitation_mm: w.current?.precipitation ?? null,
          timezone: w.timezone, units: w.units,
          hourly: w.hourly.map(h => ({ time: h.time.slice(11, 16), precipitation: h.precipitation_mm })),
          notice: w.notice,
        });
      } else {
        setWeather({ ...demo.data, notice: `${demo.data.notice} The live provider query is unavailable; these are separate demonstration values.` });
      }
    }).catch(e => { if (active) { setError(e instanceof Error ? e.message : "Unable to load screening data"); setLoading(false); } });
    return () => { active = false; };
  }, []);

  const visible = useMemo(() => cells.filter(cell => filter === "all" || cell.screening_classification === filter), [cells, filter]);
  const fmt = (value: unknown) => typeof value === "number" ? value.toFixed(2) : "Unavailable";
  return <>
    <PageHeader eyebrow="Experimental screening" title="Hazard Analysis" description="Inspect rainfall context, terrain availability, component values, and assumptions behind screening outputs." />
    {error && <div className="error">{error}</div>}
    <div className="card"><h2>Methodology and guardrails</h2><p className="method">The demo formula is score = 0.45 × rainfall component + 0.55 × terrain component. Components are illustrative 0–100 inputs. Missing required components produce no score; inputs outside 0–100 are rejected. Weights and thresholds are demonstration assumptions, not locally calibrated values. This is not a landslide probability, forecast, or warning.</p></div>
    {weather && <div className="grid two section-space">
      <section className="card"><h2>Rainfall product</h2><p className="small">{weather.provider} · {weather.classification} · {weather.timestamp} · {weather.units ?? "mm"} · {weather.timezone ?? "UTC"}</p><RainfallChart weather={weather}/><p className="method">Previous 24h: {weather.rainfall_24h_mm ?? "Unavailable"} mm · previous 72h: {weather.rainfall_72h_mm ?? "Unavailable"} mm · next 24h: {weather.forecast_24h_mm ?? "Unavailable"} mm</p><p className="small muted">{weather.notice}</p></section>
      <section className="card"><h2>Terrain source</h2><StatusBadge value={terrain?.status}/>{terrain?.summary ? <><div className="source-row"><span>Elevation mean / range</span><strong>{fmt(terrain.summary.elevation_mean)} / {fmt(terrain.summary.elevation_min)}–{fmt(terrain.summary.elevation_max)} {String(terrain.summary.elevation_units)}</strong></div><div className="source-row"><span>Mean slope</span><strong>{fmt(terrain.summary.slope_mean_degrees)}°</strong></div><div className="source-row"><span>Valid coverage</span><strong>{fmt(terrain.summary.valid_coverage_percent)}%</strong></div></> : <p>{terrain?.notice ?? "No DEM is loaded. No measured terrain results are available."}</p>}</section>
    </div>}
    <section className="card section-space">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "end", gap: 12, flexWrap: "wrap" }}><div><h2>Screening cells</h2><p className="small">{area?.name} · {cells.length} illustrative cells</p></div><div className="field"><label htmlFor="classification-filter">Classification filter</label><select id="classification-filter" value={filter} onChange={e => setFilter(e.target.value)}><option value="all">All</option><option value="high">High</option><option value="moderate">Moderate</option><option value="low">Low</option></select></div></div>
      {loading && <p className="muted section-space" role="status">Loading screening cells, terrain status, and weather context…</p>}
      <div className="grid two section-space"><div><SentinelMap hazards={visible} assets={[]} boundary={area?.boundary}/></div><div>{!loading && visible.length ? visible.map(cell => <article className="card section-space" key={cell.id}><div style={{ display: "flex", justifyContent: "space-between", gap: 8 }}><h3>{cell.id} · {cell.name}</h3><StatusBadge value={cell.screening_classification}/></div><div className="metric-value">{cell.screening_score}<small className="muted">/100 heuristic</small></div><div className="source-row"><span>Rainfall component</span><strong>{cell.rainfall_component}/100</strong></div><div className="source-row"><span>Terrain component</span><strong>{cell.terrain_component}/100</strong></div><p className="small">{String(cell.data_completeness)}</p><p className="method">{cell.method}</p></article>) : !loading && <p className="muted">No cells match this filter.</p>}</div></div>
    </section>
  </>;
}
