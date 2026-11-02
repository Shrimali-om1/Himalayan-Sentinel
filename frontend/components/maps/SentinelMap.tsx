"use client";

import { useEffect, useRef, useState } from "react";
import type { Map as MapLibreMap, MapLayerMouseEvent } from "maplibre-gl";
import type { HazardCell, PointFeature } from "@/types";

type Props = { hazards: HazardCell[]; assets: PointFeature[]; boundary?: { type: string; coordinates: unknown }; onSelect?: (item: { title: string; detail: string }) => void };

export function SentinelMap({ hazards, assets, boundary, onSelect }: Props) {
  const node = useRef<HTMLDivElement>(null); const map = useRef<MapLibreMap | null>(null);
  const [mapState, setMapState] = useState<"loading" | "ready" | "fallback">("loading");
  const [layers, setLayers] = useState({ hazards: true, assets: true });
  useEffect(() => {
    let alive = true;
    const setup = async () => {
      try {
        const maplibregl = await import("maplibre-gl");
        if (!node.current || !alive) return;
        let loaded = false;
        const instance = new maplibregl.Map({ container: node.current, style: "https://tiles.openfreemap.org/styles/liberty", center: [77.185, 32.25], zoom: 10.7, attributionControl: { compact: true } });
        map.current = instance;
        instance.addControl(new maplibregl.NavigationControl(), "top-right");
        instance.on("load", () => {
          loaded = true;
          if (boundary) {
            instance.addSource("study-area", { type: "geojson", data: { type: "Feature", properties: { title: "Illustrative study-area boundary" }, geometry: boundary as GeoJSON.Geometry } });
            instance.addLayer({ id: "study-area-fill", type: "fill", source: "study-area", paint: { "fill-color": "#8dd7ad", "fill-opacity": 0.08 } });
            instance.addLayer({ id: "study-area-line", type: "line", source: "study-area", paint: { "line-color": "#8dd7ad", "line-width": 2, "line-dasharray": [3, 2] } });
          }
          instance.addSource("hazards", { type: "geojson", data: { type: "FeatureCollection", features: hazards.map((h) => ({ type: "Feature", properties: { title: h.name, score: h.screening_score, kind: "Hazard screening" }, geometry: h.geometry as unknown as GeoJSON.Geometry })) } });
          instance.addLayer({ id: "hazards-layer", type: "circle", source: "hazards", paint: { "circle-radius": 10, "circle-color": ["interpolate", ["linear"], ["get", "score"], 0, "#8dd7ad", 55, "#f4c66b", 100, "#e98a7c"], "circle-stroke-width": 2, "circle-stroke-color": "#f5f5ea" } });
          instance.addSource("assets", { type: "geojson", data: { type: "FeatureCollection", features: assets.map((a) => ({ type: "Feature", properties: { title: a.name, kind: a.category ?? "Asset", classification: a.classification ?? "illustrative" }, geometry: a.geometry as unknown as GeoJSON.Geometry })) } });
          instance.addLayer({ id: "assets-points", type: "circle", source: "assets", filter: ["==", ["geometry-type"], "Point"], paint: { "circle-radius": 5, "circle-color": "#75b8ff", "circle-stroke-width": 1.5, "circle-stroke-color": "#071512" } });
          instance.addLayer({ id: "assets-lines", type: "line", source: "assets", filter: ["==", ["geometry-type"], "LineString"], paint: { "line-color": "#75b8ff", "line-width": 2.5, "line-opacity": 0.9 } });
          instance.addLayer({ id: "assets-areas", type: "fill", source: "assets", filter: ["==", ["geometry-type"], "Polygon"], paint: { "fill-color": "#75b8ff", "fill-opacity": 0.18, "fill-outline-color": "#75b8ff" } });
          instance.on("click", "hazards-layer", (event) => { const f = event.features?.[0]; if (f) onSelect?.({ title: String(f.properties?.title), detail: `${f.properties?.kind}: experimental score ${f.properties?.score}/100.` }); });
          const selectAsset = (event: MapLayerMouseEvent) => { const f = event.features?.[0]; if (f) onSelect?.({ title: String(f.properties?.title), detail: `${f.properties?.kind} feature · ${f.properties?.classification}. OSM coverage may be incomplete.` }); };
          for (const id of ["assets-points", "assets-lines", "assets-areas"]) instance.on("click", id, selectAsset);
          setMapState("ready");
        });
        instance.on("error", () => { if (alive && !loaded) setMapState("fallback"); });
      } catch { if (alive) setMapState("fallback"); }
    };
    setup(); return () => { alive = false; map.current?.remove(); map.current = null; };
    // GeoJSON data is deliberately initialized once per page; API reloads remount this component.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  function toggle(type: "hazards" | "assets") { const next = !layers[type]; setLayers({ ...layers, [type]: next }); const ids = type === "hazards" ? ["hazards-layer"] : ["assets-points", "assets-lines", "assets-areas"]; for (const id of ids) if (map.current?.getLayer(id)) map.current.setLayoutProperty(id, "visibility", next ? "visible" : "none"); }
  return <div className="map"><div ref={node} style={{ height: "100%", display: mapState === "fallback" ? "none" : "block" }} />{mapState === "fallback" && <div className="map-fallback"><strong>Interactive base map is unavailable</strong><span className="small">Overlay data is still available below. Check internet access or the public tile service.</span></div>}<div className="map-controls"><button className={layers.hazards ? "on" : ""} onClick={() => toggle("hazards")}>Hazard screening</button><button className={layers.assets ? "on" : ""} onClick={() => toggle("assets")}>Infrastructure</button></div><div className="map-attribution">○ screening · ● infrastructure · Base: © OpenFreeMap / © OpenStreetMap contributors</div></div>;
}

