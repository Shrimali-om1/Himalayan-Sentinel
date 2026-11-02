import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const frontend = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const source = (relativePath) => readFile(path.join(frontend, relativePath), "utf8");

test("shared navigation lists each of the eight application routes", async () => {
  const shell = await source("components/layout/AppShell.tsx");
  const expected = [
    ["/", "Situation Room"], ["/hazard-analysis", "Hazard Analysis"], ["/disaster-chain", "Disaster Chain"],
    ["/impact-analysis", "Impact Analysis"], ["/scenarios", "Scenario Studio"], ["/incidents", "Incident Reports"],
    ["/data-sources", "Data Sources"], ["/settings", "Settings & About"],
  ];
  for (const [route, label] of expected) assert.ok(shell.includes(`"${route}", "${label}"`), `${label} route should remain in navigation`);
});

test("all route entry points use the shared shell and their intended view", async () => {
  const routes = [
    ["app/page.tsx", "SituationRoom"], ["app/hazard-analysis/page.tsx", "HazardAnalysis"],
    ["app/disaster-chain/page.tsx", "DisasterChain"], ["app/impact-analysis/page.tsx", "ImpactAnalysis"],
    ["app/scenarios/page.tsx", "ScenarioStudio"], ["app/incidents/page.tsx", "IncidentReports"],
    ["app/data-sources/page.tsx", "DataSources"], ["app/settings/page.tsx", "SettingsAbout"],
  ];
  for (const [file, component] of routes) {
    const page = await source(file);
    assert.ok(page.includes("AppShell"), `${file} should use the shared shell`);
    assert.ok(page.includes(component), `${file} should render ${component}`);
  }
});

test("API calls have bounded waits and explicit failures", async () => {
  const api = await source("lib/api.ts");
  assert.match(api, /AbortSignal\.timeout\(10_000\)/);
  assert.match(api, /API request timed out/);
  assert.match(api, /Unable to reach the API/);
  assert.match(api, /cache: "no-store"/);
});

test("screening view states the heuristic, units, and non-probability guardrail", async () => {
  const view = await source("components/pages/HazardAnalysis.tsx");
  assert.match(view, /0\.45 × rainfall component \+ 0\.55 × terrain component/);
  assert.match(view, /not a landslide probability/);
  assert.match(view, /Loading screening cells/);
  assert.match(view, /No cells match this filter/);
});

test("scenario and incident views preserve simulation and verification labels", async () => {
  const scenario = await source("components/pages/ScenarioStudio.tsx");
  const incident = await source("components/pages/IncidentReports.tsx");
  assert.match(scenario, /method:\s*"POST"/);
  assert.match(scenario, /SIMULATED SCENARIO/);
  assert.match(scenario, /Compare with saved scenario/);
  assert.match(incident, /method:"POST"/);
  assert.match(incident, /Submit as unverified/);
  assert.match(incident, /verification_status/);
});

test("source register renders provenance and status fields", async () => {
  const view = await source("components/pages/DataSources.tsx");
  for (const field of ["classification", "status", "coverage", "last_retrieval", "record_count", "limitation"]) {
    assert.ok(view.includes(field), `source register should expose ${field}`);
  }
  assert.match(view, /Loading source register/);
  assert.match(view, /No data sources are registered/);
});
