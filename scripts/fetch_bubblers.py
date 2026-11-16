#!/usr/bin/env python3
"""Download OpenStreetMap drinking-water features from Overpass, for build_bubblers.py.

Uses the same bounding box and mirrors as fetch_overpass.py, in one query. Writes
drinking_water.json and fetch_log.json into --out-dir (default data/raw/bubblers/osm).
The council layers are downloaded by hand; see DATA.md.
"""
from pathlib import Path
import argparse
from datetime import datetime, timezone
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from fetch_overpass import BBOX, fetch, query
from pigeon_ai.bubblers import RAW_DIR

FILTERS = [
    'nwr["amenity"="drinking_water"]',
    'nwr["man_made"="water_tap"]',
    'nwr["drinking_water"]',
    'nwr["amenity"="water_point"]',
    'nwr["amenity"="fountain"]',
]


def main(out_dir):
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
    parser.add_argument("--out-dir", type=Path, default=RAW_DIR / "osm")
    main(parser.parse_args().out_dir)
