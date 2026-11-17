#!/usr/bin/env python3
"""Download the water fountain sources for build_bubblers.py into --raw-dir (default data/raw/bubblers).

  official/<stem>.geojson   every feature of each council layer in pigeon_ai.bubblers.OFFICIAL
  osm/drinking_water.json   OpenStreetMap drinking-water features from Overpass, with the same
                            bounding box and mirrors as fetch_overpass.py, in one query
  osm/fetch_log.json        the Overpass endpoint, query and OSM snapshot time

The council boundaries (lga/lga.geojson) are downloaded by hand; see DATA.md.
"""
from pathlib import Path
import argparse
from datetime import datetime, timezone
import json
import sys

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from fetch_overpass import BBOX, HEADERS, fetch, query
from pigeon_ai.bubblers import OFFICIAL, RAW_DIR

FILTERS = [
    'nwr["amenity"="drinking_water"]',
    'nwr["man_made"="water_tap"]',
    'nwr["drinking_water"]',
    'nwr["amenity"="water_point"]',
    'nwr["amenity"="fountain"]',
]
COUNCIL_QUERY = {"where": "1=1", "outFields": "*", "outSR": 4326, "f": "geojson"}


def fetch_councils(out_dir):
    out_dir.mkdir(parents=True, exist_ok=True)
    for stem, (council, url) in OFFICIAL.items():
        response = requests.get(f"{url}/query", params=COUNCIL_QUERY, headers=HEADERS, timeout=120)
        response.raise_for_status()
        data = response.json()
        # ArcGIS caps a query at the layer's maxRecordCount; every layer here is far below it.
        if "features" not in data or data.get("exceededTransferLimit") or data.get("properties", {}).get("exceededTransferLimit"):
            raise RuntimeError(f"{stem}: incomplete or failed query ({str(data)[:200]})")
        (out_dir / f"{stem}.geojson").write_bytes(response.content)
        print(f"ok: {stem} ({council}): {len(data['features'])} features")


def fetch_osm(out_dir):
    out_dir.mkdir(parents=True, exist_ok=True)
    text = query(FILTERS, *BBOX).replace("out tags geom;", "out tags center;")
    result = fetch(text)
    if result is None:
        raise RuntimeError("Every endpoint failed; rerun later")
    url, content, data = result
    (out_dir / "drinking_water.json").write_bytes(content)
    (out_dir / "fetch_log.json").write_text(json.dumps(dict(
        endpoint=url, elements=len(data["elements"]), query=text,
        osm_base=data.get("osm3s", {}).get("timestamp_osm_base"),
        fetched_utc=datetime.now(timezone.utc).isoformat(timespec="seconds")), indent=1))
    print(f"ok: {len(data['elements'])} elements via {url}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--raw-dir", type=Path, default=RAW_DIR)
    parser.add_argument("--skip-osm", action="store_true", help="download only the council layers (Overpass is slow)")
    args = parser.parse_args()
    fetch_councils(args.raw_dir / "official")
    if not args.skip_osm:
        fetch_osm(args.raw_dir / "osm")
