"use client";
import { useCallback, useEffect, useState } from "react";
import { PageHeader } from "@/components/shared/PageHeader";
import { SentinelMap } from "@/components/maps/SentinelMap";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { api } from "@/lib/api";
import type { HazardCell, PointFeature } from "@/types";

type Exposure = { hazard_cell: {id:string; name:string; screening_score:number}; buffer_meters:number; assets:{id:string;name:string;category:string;distance_meters:number;source:string;classification?:string;geometry:PointFeature["geometry"]}[]; category_counts:Record<string,number>; method:string; notice:string; classification:string };
type Area = { name:string; boundary:{type:string;coordinates:unknown} };
const categories = ["all", "road", "bridge", "healthcare", "school", "building", "settlement"];

export function ImpactAnalysis() {
  const [result,setResult]=useState<Exposure|null>(null); const [cells,setCells]=useState<HazardCell[]>([]); const [area,setArea]=useState<Area|null>(null);
  const [buffer,setBuffer]=useState(2000); const [category,setCategory]=useState("all"); const [error,setError]=useState(""); const [loading,setLoading]=useState(true);
  const load=useCallback(async()=>{setLoading(true);setError("");try{const suffix=category==="all"?"":`&category=${category}`;const [exposure,cellsResult,areas]=await Promise.all([api<{data:Exposure}>(`/exposure/summary?cell_id=HC-002&buffer_meters=${buffer}${suffix}`),api<{data:HazardCell[]}>("/hazard/cells"),api<{data:Area[]}>("/study-areas")]);setResult(exposure.data);setCells(cellsResult.data);setArea(areas.data[0]??null)}catch(e){setError(e instanceof Error?e.message:"Unable to load exposure data")}finally{setLoading(false)}},[buffer,category]);
  useEffect(()=>{void load()},[load]);
  return <><PageHeader eyebrow="Spatial screening" title="Impact Analysis" description="Review infrastructure proximity to a screening cell. Proximity does not mean that an asset is damaged."/>
    <section className="card"><div style={{display:"flex",alignItems:"end",gap:12,flexWrap:"wrap"}}><div className="field"><label htmlFor="buffer">Analysis buffer (m)</label><input id="buffer" type="number" min="100" max="10000" value={buffer} onChange={e=>setBuffer(Number(e.target.value))}/></div><div className="field"><label htmlFor="category">Infrastructure category</label><select id="category" value={category} onChange={e=>setCategory(e.target.value)}>{categories.map(item=><option key={item} value={item}>{item === "all" ? "All categories" : item}</option>)}</select></div><button className="button" onClick={()=>void load()}>Recalculate</button></div></section>
    {error&&<div className="error section-space">{error}</div>}
    {loading&&<p className="muted section-space" role="status">Loading screening cells and infrastructure proximity…</p>}
    {result&&<><div className="grid stats section-space"><div className="card"><div className="metric-label">Selected cell</div><div className="metric-value">{result.hazard_cell.id}</div><div className="metric-sub">Experimental score {result.hazard_cell.screening_score}/100</div></div><div className="card"><div className="metric-label">Buffer</div><div className="metric-value">{result.buffer_meters.toLocaleString()} m</div><div className="metric-sub">Illustrative proximity threshold</div></div><div className="card"><div className="metric-label">Assets within buffer</div><div className="metric-value">{result.assets.length}</div><div className="metric-sub">Returned provider/demo features</div></div><div className="card"><div className="metric-label">Data class</div><div className="metric-value" style={{fontSize:18}}>{result.classification}</div><div className="metric-sub">Coverage may be incomplete</div></div></div>
      <div className="grid two"><section className="card"><h2>Infrastructure map</h2><p className="small">{area?.name}</p><SentinelMap hazards={cells} assets={result.assets} boundary={area?.boundary}/><p className="small muted">Map overlays distinguish available asset records; unmapped infrastructure may still exist.</p></section><section className="card"><h2>Assets in the analysis buffer</h2>{result.assets.length?result.assets.map(asset=><div className="list-row" key={asset.id}><div><strong>{asset.name}</strong><p>{asset.source}</p></div><div style={{textAlign:"right"}}><StatusBadge value={asset.category}/><div className="small muted" style={{marginTop:6}}>{asset.distance_meters.toLocaleString()} m</div></div></div>):<p className="muted">No assets in this category were returned within the selected buffer. This does not establish absence of infrastructure.</p>}<p className="method section-space">{result.method}</p><p className="notice">{result.notice}</p></section></div></>}
  </>;
}
