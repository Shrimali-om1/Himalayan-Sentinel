# Limitations

- This is an experimental academic prototype, not an official warning, forecasting, or emergency-response service.
- The supplied study boundary, rainfall, terrain components, hazard cells, chain, and assets are demonstration data, not observations.
- The GeoTIFF ingestion and slope derivation workflow is implemented and tested with a synthetic raster, but no genuine DEM is bundled or ingested. Demo terrain values must not be treated as terrain measurements until a real source is supplied and processed.
- Open-Meteo output is model/forecast data; it is not automatically a ground observation.
- OpenStreetMap coverage may be incomplete and must retain attribution and source identifiers after ingestion. The bounded ingestion workflow is implemented, but the default Overpass host returned HTTP 502 and one alternate timed out during the completion pass; no real OSM records were retrieved then.
- There is no calibrated local landslide probability model and no physically based river-blockage or flood simulation.
- User reports remain unverified until independent review with evidence.
- SQLite supports the reproducible demo only; full spatial database capability requires PostgreSQL/PostGIS. The adapter and migration are implemented, but local PostGIS validation is blocked because the installed PostgreSQL service lacks the PostGIS extension and configured application credentials.

