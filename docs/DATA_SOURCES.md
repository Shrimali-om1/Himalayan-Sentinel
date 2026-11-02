# Data sources and provenance

| Source | Role | Classification when used | Current MVP state |
|---|---|---|---|
| [Open-Meteo Forecast API](https://open-meteo.com/en/docs) | point weather query | forecast/model product | connected on demand; no key |
| [OpenStreetMap / Overpass](https://wiki.openstreetmap.org/wiki/Overpass_API) | roads, bridges, buildings, healthcare, schools | source-derived OSM data | bounded CLI ingestion available; demo features display until run |
| Manually supplied GeoTIFF | elevation and terrain derivatives | provider-defined / derived | bounded CLI processing available; no file bundled |
| User submission | incident report | unverified user report | functional local form |

Open-Meteo’s forecast endpoint accepts WGS84 coordinates and can return current and hourly precipitation. The application stores its response as provider-labelled forecast/model information, never as a ground-station observation. See its [forecast documentation](https://open-meteo.com/en/docs) for time resolution, models, and current product behavior.

The OSM CLI runs a bounded query, sets an identifying User-Agent, stores by OSM element ID, and preserves tags/retrieval time. Run manually and infrequently; the shared public Overpass API is subject to load and usage limits. This follows the [Overpass usage guidance](https://wiki.openstreetmap.org/wiki/Overpass_API). Retrieved OSM geometry carries map attribution.

The basemap uses [OpenFreeMap’s documented Liberty style](https://openfreemap.org/quick_start/) when the browser can reach it. It is a display layer—not source evidence for any feature or hazard statement.

