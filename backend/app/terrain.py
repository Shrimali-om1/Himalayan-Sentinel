"""Controlled DEM inspection and slope derivation for a manually supplied GeoTIFF."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import rasterio
from pyproj import CRS, Transformer
from rasterio.features import geometry_mask, geometry_window
from rasterio.transform import array_bounds
from rasterio.warp import calculate_default_transform, reproject, Resampling
from shapely.geometry import shape, box, mapping
from shapely.ops import transform as transform_geometry

MAX_PIXELS = 8_000_000


def process_dem(path: str | Path, boundary_geojson: dict[str, Any], output_dir: str | Path) -> dict[str, Any]:
    source = Path(path).resolve()
    if not source.is_file() or source.suffix.lower() not in {".tif", ".tiff"}:
        raise ValueError("Provide an existing .tif or .tiff DEM file.")
    output = Path(output_dir).resolve()
    output.mkdir(parents=True, exist_ok=True)
    slope_path = output / f"{source.stem}_slope_utm43n.tif"
    area_wgs84 = shape(boundary_geojson)
    if not area_wgs84.is_valid:
        raise ValueError("Study area boundary is invalid GeoJSON.")
    try:
        opened = rasterio.open(source)
    except rasterio.errors.RasterioError as exc:
        raise ValueError(f"Could not read DEM GeoTIFF: {exc}") from exc
    with opened as dataset:
        if dataset.crs is None:
            raise ValueError("DEM has no CRS; assign a CRS before processing.")
        if dataset.count < 1:
            raise ValueError("DEM does not contain a readable band.")
        src_crs = CRS.from_user_input(dataset.crs)
        to_source = Transformer.from_crs("EPSG:4326", src_crs, always_xy=True).transform
        area_in_source = transform_geometry(to_source, area_wgs84)
        if not box(*dataset.bounds).intersects(area_in_source):
            raise ValueError("DEM extent does not overlap the configured study area.")
        src_meta = dataset.meta.copy()
        window = geometry_window(dataset, [mapping(area_in_source)])
        if window.width * window.height > MAX_PIXELS:
            raise ValueError(f"The study-area DEM window exceeds the {MAX_PIXELS:,}-pixel processing limit.")
        raw = dataset.read(1, window=window, masked=True).astype("float64")
        src_meta["transform"] = rasterio.windows.transform(window, dataset.transform)
        src_meta["width"], src_meta["height"] = int(window.width), int(window.height)
        source_resolution = [abs(float(dataset.res[0])), abs(float(dataset.res[1]))]
        source_nodata = dataset.nodata
        elevation_units = dataset.units[0] if dataset.units else None
        source_bounds = [float(v) for v in array_bounds(src_meta["height"], src_meta["width"], src_meta["transform"])]

    # UTM zone 43N is a local metric CRS appropriate for this pilot region.
    dst_crs = CRS.from_epsg(32643)
    area_to_metric = Transformer.from_crs("EPSG:4326", dst_crs, always_xy=True).transform
    area_metric = transform_geometry(area_to_metric, area_wgs84)
    transform, width, height = calculate_default_transform(src_crs, dst_crs, src_meta["width"], src_meta["height"], *source_bounds)
    if width * height > MAX_PIXELS:
        raise ValueError(f"Reprojected DEM exceeds the {MAX_PIXELS:,}-pixel processing limit.")
    destination = np.full((height, width), np.nan, dtype="float32")
    reproject(source=raw.filled(np.nan).astype("float32"), destination=destination, src_transform=src_meta["transform"],
              src_crs=src_crs, src_nodata=np.nan, dst_transform=transform, dst_crs=dst_crs, dst_nodata=np.nan,
              resampling=Resampling.bilinear)
    inside_area = geometry_mask([mapping(area_metric)], out_shape=destination.shape, transform=transform, invert=True)
    valid = np.isfinite(destination) & inside_area
    if not valid.any():
        raise ValueError("The overlapping study area contains no valid elevation pixels.")

    # np.gradient returns dz/dy, dz/dx; UTM resolutions make these derivatives metric.
    yres, xres = abs(float(transform.e)), abs(float(transform.a))
    filled = np.where(valid, destination, np.nanmedian(destination[valid]))
    dz_dy, dz_dx = np.gradient(filled, yres, xres)
    slope_degrees = np.degrees(np.arctan(np.hypot(dz_dx, dz_dy))).astype("float32")
    slope_valid = valid.copy()
    slope_valid[1:-1, :] &= valid[:-2, :] & valid[2:, :]
    slope_valid[:, 1:-1] &= valid[:, :-2] & valid[:, 2:]
    slope_degrees[~slope_valid] = np.nan
    profile = {"driver": "GTiff", "height": height, "width": width, "count": 1, "dtype": "float32", "crs": dst_crs,
               "transform": transform, "nodata": -9999.0, "compress": "deflate"}
    with rasterio.open(slope_path, "w", **profile) as output_dataset:
        output_dataset.write(np.where(slope_valid, slope_degrees, -9999.0), 1)
        output_dataset.set_band_description(1, "slope_degrees")

    values, slope_values = destination[valid], slope_degrees[slope_valid]
    return {
        "dataset_name": source.name, "source": "manually supplied GeoTIFF; source/license must be recorded by operator",
        "source_file": str(source), "slope_file": str(slope_path), "source_crs": src_crs.to_string(),
        "analysis_crs": dst_crs.to_string(), "source_resolution": source_resolution,
        "analysis_resolution_m": [abs(float(transform.a)), abs(float(transform.e))],
        "elevation_units": elevation_units or "source units unspecified", "source_nodata": source_nodata,
        "valid_pixels": int(valid.sum()), "total_pixels": int(inside_area.sum()),
        "valid_coverage_percent": round(float(valid.sum() / max(inside_area.sum(), 1) * 100), 2),
        "slope_valid_pixels": int(slope_valid.sum()),
        "elevation_min": round(float(values.min()), 2), "elevation_max": round(float(values.max()), 2),
        "elevation_mean": round(float(values.mean()), 2), "slope_min_degrees": round(float(slope_values.min()), 2),
        "slope_max_degrees": round(float(slope_values.max()), 2), "slope_mean_degrees": round(float(slope_values.mean()), 2),
        "coverage": "Raster footprint overlap checked; elevation and slope summaries are clipped to the configured study-area polygon.",
        "method": "Bilinear reprojection to WGS 84 / UTM zone 43N; slope = atan(sqrt((dz/dx)^2 + (dz/dy)^2)) in degrees using pixel gradients. NoData cells are omitted from summaries.",
    }

