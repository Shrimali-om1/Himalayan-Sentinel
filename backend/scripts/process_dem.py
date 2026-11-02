"""Validate a local DEM and derive a slope GeoTIFF for the current pilot area."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.storage import store
from app.terrain import process_dem


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dem", help="Existing licensed .tif/.tiff file")
    parser.add_argument("--source", default="Manually supplied GeoTIFF", help="Dataset/provider provenance label")
    args = parser.parse_args()
    store.initialize()
    areas = store.study_areas()
    if not areas:
        raise SystemExit("No study area is configured. Seed the demo or import a reviewed boundary first.")
    root = Path(__file__).resolve().parents[2]
    metadata = process_dem(args.dem, areas[0]["boundary"], root / "data" / "processed")
    metadata["source"] = args.source
    store.save_terrain(metadata["dataset_name"], metadata["slope_file"], metadata)
    (root / "data" / "processed" / "terrain_metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()

