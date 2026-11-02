# Methodology

## Rainfall

The live connector requests `current=precipitation` and hourly `precipitation` from Open-Meteo for a configurable point. Returned values remain forecast/model product data with provider timestamp and source URL. The bundled rainfall chart is a deterministic illustrative fixture and has a permanent demo label.

## Terrain

A valid DEM is checked for CRS, raster window overlap, resolution, and NoData before processing. The covered window is reprojected to WGS 84 / UTM zone 43N, a local metric CRS for this pilot. Slope in degrees is `atan(sqrt((dz/dx)^2 + (dz/dy)^2))`, estimated by central pixel gradients using projected metre resolution. Bilinear reprojection and edge/NoData handling affect the derivative. Summary pixels are masked to the study polygon. No terrain raster or slope is invented; no source file is bundled.

## Screening

The bundled example calculates an experimental score:

`score = round(0.45 × rainfall component + 0.55 × terrain component)`

Both illustrative components are bounded 0–100; if either required component is missing the score should be absent, and out-of-range components are rejected. Demo category cutoffs are high >=65, moderate 40–64, and low <40. These are explicit demonstration assumptions, chosen for transparency rather than validation. Scores/classes are not a probability of a landslide or an alert level. A real pilot needs local calibration, historical data, sensitivity testing, expert review, and a versioned parameter set.

## Exposure and chain relationships

The demo measures point proximity with a great-circle distance, flags assets inside a user-chosen buffer, and calls this a screening relationship—not expected damage. Production uses PostGIS `ST_DWithin` / projected spatial methods. Disaster-chain arrows are classified as inferred, hypothesis, or simulated, with a stated evidence basis; they do not confirm a hazard event.

## Scenarios and reports

Scenario Studio changes only the illustrative rainfall component by an explicit percentage and recomputes the example score. Generated reports restate classification and limitations and do not use an LLM or create facts.

