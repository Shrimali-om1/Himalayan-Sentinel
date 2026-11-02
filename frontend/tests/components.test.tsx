import React from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";

vi.mock("@/lib/api", () => ({ api: vi.fn() }));
vi.mock("@/components/maps/SentinelMap", () => ({ SentinelMap: () => null }));
vi.mock("@/components/charts/RainfallChart", () => ({ RainfallChart: () => null }));
vi.mock("next/navigation", () => ({ usePathname: () => "/" }));
vi.mock("next/link", async () => {
  const ReactModule = await import("react");
  return { default: ({ href, children, ...props }: React.AnchorHTMLAttributes<HTMLAnchorElement> & { href: string }) => ReactModule.createElement("a", { href, ...props }, children) };
});
vi.mock("recharts", async () => {
  const ReactModule = await import("react");
  const Wrapper = ({ children }: { children?: React.ReactNode }) => ReactModule.createElement("div", null, children);
  return { ResponsiveContainer: Wrapper, BarChart: Wrapper, CartesianGrid: Wrapper, Legend: Wrapper, Tooltip: Wrapper, XAxis: Wrapper, YAxis: Wrapper, Bar: () => null };
});

import { api } from "@/lib/api";
import { AppShell } from "@/components/layout/AppShell";
import { SituationRoom } from "@/components/dashboard/SituationRoom";
import { HazardAnalysis } from "@/components/pages/HazardAnalysis";
import { DisasterChain } from "@/components/pages/DisasterChain";
import { ImpactAnalysis } from "@/components/pages/ImpactAnalysis";
import { ScenarioStudio } from "@/components/pages/ScenarioStudio";
import { IncidentReports } from "@/components/pages/IncidentReports";
import { DataSources } from "@/components/pages/DataSources";

const apiMock = vi.mocked(api);
const area = { id: "pilot", name: "Kullu–Manali pilot", description: "Illustrative boundary", crs: "EPSG:4326", classification: "illustrative", boundary: { type: "Polygon", coordinates: [] } };
const cell = { id: "HC-001", name: "North slope", geometry: { type: "Point", coordinates: [77.19, 32.24] }, rainfall_component: 40, terrain_component: 60, screening_score: 51, screening_classification: "moderate", classification: "illustrative", method: "Experimental heuristic" };
const exposure = (assets: Record<string, unknown>[]) => ({ hazard_cell: { id: "HC-001", name: "North slope", screening_score: 51 }, buffer_meters: 2000, assets, category_counts: {}, method: "Projected proximity screening", notice: "Proximity is not damage.", classification: "illustrative derived analysis" });
const scenario = { id: 4, name: "Rainfall sensitivity test", rainfall_adjustment: 50, classification: "SIMULATED SCENARIO", created_at: "2026-11-02T10:00:00Z", results: { cells: [{ id: "HC-001", baseline_score: 51, scenario_score: 62, scenario_classification: "simulated" }], summary: { high: 0, moderate: 1, low: 0 }, method: "Rainfall sensitivity assumption only." } };

afterEach(cleanup);
beforeEach(() => apiMock.mockReset());

describe("frontend interactions", () => {
  it("renders all eight shared navigation links", () => {
    render(<AppShell><span>Page body</span></AppShell>);
    const links = screen.getAllByRole("link");
    expect(links).toHaveLength(8);
    expect(screen.getByRole("link", { name: /Situation Room/ })).toBeTruthy();
    expect(screen.getByRole("link", { name: /Settings & About/ })).toBeTruthy();
  });

  it("shows loading, API error, and a working retry on the Situation Room", async () => {
    let rejectSummary: ((error: Error) => void) | undefined;
    let summaryCalls = 0;
    apiMock.mockImplementation((path) => {
      if (path === "/weather/summary") {
        summaryCalls += 1;
        if (summaryCalls === 1) return new Promise((_, reject) => { rejectSummary = reject; }) as never;
        return Promise.reject(new Error("offline")) as never;
      }
      if (path === "/weather/live") return Promise.reject(new Error("provider offline")) as never;
      return Promise.resolve({ data: [] }) as never;
    });
    render(<SituationRoom />);
    expect(screen.getByText(/Loading study area and available provider data/)).toBeTruthy();
    rejectSummary?.(new Error("offline"));
    expect((await screen.findByRole("alert")).textContent).toContain("API unavailable");
    fireEvent.click(screen.getByRole("button", { name: "retry" }));
    await waitFor(() => expect(summaryCalls).toBe(2));
    expect((await screen.findByRole("alert")).textContent).toContain("offline");
  });

  it("shows the screening formula and lets users filter hazard cells", async () => {
    apiMock.mockImplementation(async (path) => {
      if (path === "/hazard/screening") return { data: { cells: [cell, { ...cell, id: "HC-002", name: "High slope", screening_classification: "high" }] } } as never;
      if (path === "/terrain/status") return { data: { status: "not_configured", notice: "No DEM loaded." } } as never;
      if (path === "/weather/summary") return { data: { provider: "demo", classification: "illustrative", rainfall_24h_mm: null, rainfall_72h_mm: null, forecast_24h_mm: null, latest_precipitation_mm: null, hourly: [], notice: "Demo only." } } as never;
      if (path === "/weather/live") throw new Error("offline");
      return { data: [area] } as never;
    });
    render(<HazardAnalysis />);
    expect(screen.getByText(/0\.45 × rainfall component/)).toBeTruthy();
    expect(await screen.findByText("HC-001 · North slope")).toBeTruthy();
    fireEvent.change(screen.getByLabelText("Classification filter"), { target: { value: "high" } });
    expect(screen.getByText("HC-002 · High slope")).toBeTruthy();
    expect(screen.queryByText("HC-001 · North slope")).toBeNull();
  });

  it("shows evidence details when a disaster-chain stage is selected", async () => {
    apiMock.mockResolvedValue({ data: { classification: "illustrative", notice: "Conceptual only.", nodes: [{ id: "rain", label: "Heavy rainfall", type: "environment", evidence: "Forecast or reanalysis; demo values are illustrative", indicators: "24h/72h totals and timestamp", status: "provider data or demo" }], edges: [] } } as never);
    render(<DisasterChain />);
    const node = await screen.findByRole("button", { name: /Heavy rainfall/ });
    fireEvent.click(node);
    expect(screen.getByText(/Indicators to examine: 24h\/72h totals and timestamp/)).toBeTruthy();
  });

  it("filters impact assets by category and keeps proximity distinct from damage", async () => {
    const road = { id: "road/1", name: "Main road", category: "road", source: "demo", distance_meters: 400, geometry: { type: "Point", coordinates: [77.19, 32.24] } };
    const clinic = { id: "node/2", name: "Manali clinic", category: "healthcare", source: "demo", distance_meters: 800, geometry: { type: "Point", coordinates: [77.2, 32.24] } };
    apiMock.mockImplementation(async (path) => {
      if (typeof path !== "string") return { data: exposure([clinic]) } as never;
      if (path.startsWith("/exposure/summary")) return { data: exposure(path.includes("category=healthcare") ? [clinic] : [road, clinic]) } as never;
      if (path === "/hazard/cells") return { data: [cell] } as never;
      return { data: [area] } as never;
    });
    render(<ImpactAnalysis />);
    expect(await screen.findByText("Main road")).toBeTruthy();
    expect(screen.getByText(/Proximity does not mean that an asset is damaged/)).toBeTruthy();
    fireEvent.change(screen.getByLabelText("Infrastructure category"), { target: { value: "healthcare" } });
    expect(await screen.findByText("Manali clinic")).toBeTruthy();
    await waitFor(() => expect(screen.queryByText("Main road")).toBeNull());
    expect(apiMock.mock.calls.some(([path]) => path.includes("category=healthcare"))).toBe(true);
  });

  it("saves and labels scenarios as simulated", async () => {
    let listCalls = 0;
    apiMock.mockImplementation(async (path, options) => {
      if (typeof path !== "string") return { data: [] } as never;
      if (path === "/scenarios" && options?.method === "POST") return { data: scenario } as never;
      if (path === "/scenarios") return { data: listCalls++ === 0 ? [] : [scenario] } as never;
      throw new Error(`Unexpected request ${path}`);
    });
    render(<ScenarioStudio />);
    await screen.findByText(/No saved scenarios yet/);
    fireEvent.change(screen.getByLabelText("Scenario name"), { target: { value: "Rainfall sensitivity test" } });
    fireEvent.change(screen.getByLabelText(/Rainfall adjustment/), { target: { value: "50" } });
    fireEvent.click(screen.getByRole("button", { name: "Run and save scenario" }));
    expect(await screen.findByRole("heading", { name: "Rainfall sensitivity test" })).toBeTruthy();
    expect(screen.getAllByText("SIMULATED SCENARIO").length).toBeGreaterThan(0);
    const post = apiMock.mock.calls.find(([path, options]) => path === "/scenarios" && options?.method === "POST");
    expect(JSON.parse(String(post?.[1]?.body))).toEqual({ name: "Rainfall sensitivity test", rainfall_adjustment: 50 });
  });

  it("submits incident reports with an unverified status and renders source provenance", async () => {
    let incidentCalls = 0;
    apiMock.mockImplementation(async (path, options) => {
      if (typeof path !== "string") return { data: [] } as never;
      if (path === "/incidents" && options?.method === "POST") return { notice: "Submission recorded as UNVERIFIED USER REPORT." } as never;
      if (path === "/incidents") return { data: incidentCalls++ === 0 ? [] : [{ id: 8, incident_type: "landslide", description: "Possible slope movement reported.", latitude: 32.24, longitude: 77.19, incident_date: null, verification_status: "UNVERIFIED USER REPORT", created_at: "2026-11-02T10:00:00Z" }] } as never;
      if (path === "/data-sources") return { data: [{ id: "open-meteo", provider: "Open-Meteo", dataset: "Forecast API", category: "weather", classification: "forecast/model product", status: "connected", source_url: "https://open-meteo.com/en/docs", coverage: "Point sampling", record_count: 96, limitation: "Not a ground observation.", last_retrieval: "2026-11-02T10:00:00Z" }] } as never;
      throw new Error(`Unexpected request ${path}; calls=${JSON.stringify(apiMock.mock.calls)}`);
    });
    const incidentView = render(<IncidentReports />);
    fireEvent.change(screen.getByLabelText("Description"), { target: { value: "Possible slope movement reported." } });
    fireEvent.click(screen.getByRole("button", { name: "Submit as unverified" }));
    expect((await screen.findAllByText(/UNVERIFIED USER REPORT/)).length).toBeGreaterThan(0);
    expect(apiMock.mock.calls.some(([path, options]) => path === "/incidents" && options?.method === "POST")).toBe(true);
    incidentView.unmount();

    render(<DataSources />);
    expect(await screen.findByText("connected")).toBeTruthy();
    expect(screen.getByText(/forecast\/model product/)).toBeTruthy();
    expect(screen.getByText(/Not a ground observation/)).toBeTruthy();
  });
});
