#!/usr/bin/env python3
"""Download the V12 OSM layers from Overpass into tile files, for build_recreation.py.

This queries today's OSM, so the values differ from the committed features. To reproduce
those, use the Drive copy (DATA.md). A full run can take hours: the public servers often
return 502/504 under load, so the script rotates mirrors, backs off, and splits a failing
tile 2x2 (twice at most). Rerunning it skips tiles already saved.
"""
from pathlib import Path
import argparse
from datetime import datetime, timezone
import json
import sys
import time

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pigeon_ai.recreation import OVERPASS_DIR

# EPSG:7856 bounds of every study, growth and future hexagon plus 1.5 km, as lon/lat (W, S, E, N).
BBOX = (150.4939, -34.1406, 151.3624, -33.5211)
NX, NY = 4, 3
MAX_SPLITS = 2
ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
]
HEADERS = {"User-Agent": "pigeon-ai-uni-project (research)"}
FILTERS = [
    'nwr["leisure"~"^(pitch|sports_centre|stadium|track|golf_course|playground|beach_resort)$"]',
    'nwr["natural"="beach"]',
    'nwr["emergency"~"^(lifeguard|lifeguard_base|lifeguard_tower)$"]',
    'nwr["club"~"surf|lifesaving",i]',
    'nwr["amenity"~"^(lifeguard|surf_life_saving_club)$"]',
    'nwr["sport"~"surf|lifesaving",i]',
    'nwr["amenity"="toilets"]',
]
# A name regex is too slow per tile, so surf clubs found by name come from one coastal query.
SLSC_QUERY = 'nwr["name"~"surf life ?saving|SLSC",i]'
SLSC_WEST = 151.10


def query(filters, west, south, east, north):
    body = "".join(f"{f}({south},{west},{north},{east});" for f in filters)
    return f"[out:json][timeout:300];({body});out tags geom;"


def fetch(text, attempts=len(ENDPOINTS) * 2):
    """The response as parsed JSON, or None once every attempt has failed."""
    for attempt in range(attempts):
        url = ENDPOINTS[attempt % len(ENDPOINTS)]
        try:
            response = requests.post(url, data={"data": text}, headers=HEADERS, timeout=400)
            if response.ok and response.content.lstrip().startswith(b"{"):
                data = response.json()
                remark = data.get("remark", "")
                if "runtime error" not in remark and "timed out" not in remark:
                    return url, response.content, data
                print(f"  {url}: {remark[:120]}", file=sys.stderr)
            else:
                print(f"  {url}: HTTP {response.status_code}", file=sys.stderr)
        except requests.RequestException as error:
            print(f"  {url}: {type(error).__name__}", file=sys.stderr)
        time.sleep(min(15 * 2 ** (attempt // len(ENDPOINTS)), 120))
    return None


def save(out_dir, log, name, bbox, filters):
    path = out_dir / name
    if path.exists():
        return True
    print(f"tile {name}", file=sys.stderr, flush=True)
    result = fetch(query(filters, *bbox))
    if result is None:
        return False
    url, content, data = result
    path.write_bytes(content)
    log[name] = dict(bbox=list(bbox), endpoint=url, elements=len(data["elements"]),
                     osm_base=data.get("osm3s", {}).get("timestamp_osm_base"),
                     fetched_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"))
    (out_dir / "fetch_log.json").write_text(json.dumps(log, indent=1))
    print(f"  ok: {log[name]['elements']} elements via {url}", file=sys.stderr, flush=True)
    return True


def fetch_tile(out_dir, log, stem, bbox, depth=0):
    already_split = any(out_dir.glob(f"{stem}_[01][01]*.json"))
    if not already_split and save(out_dir, log, f"{stem}.json", bbox, FILTERS):
        return
    if depth == MAX_SPLITS:
        raise RuntimeError(f"Every endpoint failed for {stem}; rerun later to resume")
    west, south, east, north = bbox
    dx, dy = (east - west) / 2, (north - south) / 2
    for a in range(2):
        for b in range(2):
            sub = (west + a * dx, south + b * dy, west + (a + 1) * dx, south + (b + 1) * dy)
            fetch_tile(out_dir, log, f"{stem}_{a}{b}", sub, depth + 1)


def main(out_dir):
    out_dir.mkdir(parents=True, exist_ok=True)
    log_path = out_dir / "fetch_log.json"
    log = json.loads(log_path.read_text()) if log_path.exists() else {}
    west, south, east, north = BBOX
    dx, dy = (east - west) / NX, (north - south) / NY
    for i in range(NX):
        for j in range(NY):
            bbox = (west + i * dx, south + j * dy, west + (i + 1) * dx, south + (j + 1) * dy)
            fetch_tile(out_dir, log, f"overpass_tile_{i}_{j}", bbox)
    if not save(out_dir, log, "overpass_slsc_names.json", (SLSC_WEST, south, east, north), [SLSC_QUERY]):
        raise RuntimeError("Every endpoint failed for the surf-club name query; rerun later to resume")
    print(f"Done: {len(log)} files in {out_dir}", file=sys.stderr)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out-dir", type=Path, default=OVERPASS_DIR,
                        help="use an empty folder; existing tile files are kept, not refreshed")
    main(parser.parse_args().out_dir)
