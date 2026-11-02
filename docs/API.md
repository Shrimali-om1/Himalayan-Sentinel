# API

Interactive documentation is available at `http://localhost:8000/docs` after FastAPI starts.

- `GET /api/health` checks process/database state without failing on unavailable providers.
- `GET /api/study-areas`, `/api/weather/summary`, `/api/weather/live`, `/api/terrain/status`, `/api/hazard/screening`, `/api/exposure/summary`, `/api/disaster-chain`, and `/api/data-sources` support read-only exploration.
- `POST /api/scenarios` accepts `{name, rainfall_adjustment}` with a `-50` to `200` guardrail and returns a `SIMULATED SCENARIO`.
- `GET|POST /api/incidents` lists or records bounded-coordinate submissions. A POST always creates `UNVERIFIED USER REPORT` status.
- `POST /api/reports/generate` returns a deterministic Markdown summary that explicitly states demo classification and limitations.

Public deployments need authentication, authorization, abuse controls, audit logging, CSRF strategy, and incident-review workflow before enabling incident writes.

