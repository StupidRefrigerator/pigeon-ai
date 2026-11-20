"""Download Sydney bike infrastructure from Overpass, tiled and cached.

Usage: python -I fetch_bike_osm.py OUT_DIR

Writes one JSON per tile (ways with tags and geometry) plus fetch_log.json. Rerunning
skips tiles already saved. Same bbox, mirrors and retry policy as scripts/fetch_overpass.py.
"""
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

# Same as scripts/fetch_overpass.py: every study, growth and future hexagon plus 1.5 km.
BBOX = (150.4939, -34.1406, 151.3624, -33.5211)
NX, NY = 4, 3
ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
]
HEADERS = {"User-Agent": "pigeon-ai-uni-project (research)"}
FILTERS = [
    'way["highway"="cycleway"]',
    'way["cycleway"]',
    'way["cycleway:both"]',
    'way["cycleway:left"]',
    'way["cycleway:right"]',
    'way["bicycle"="designated"]',
    'way["bicycle_road"="yes"]',
]


def query(south, west, north, east):
    body = "".join(f"{f}({south},{west},{north},{east});" for f in FILTERS)
    return f"[out:json][timeout:300];({body});out tags geom;"


def fetch(text):
    for attempt in range(len(ENDPOINTS) * 3):
        url = ENDPOINTS[attempt % len(ENDPOINTS)]
        try:
            r = requests.post(url, data={"data": text}, headers=HEADERS, timeout=400)
            if r.ok and r.content.lstrip().startswith(b"{"):
                data = r.json()
                remark = data.get("remark", "")
                if "runtime error" not in remark and "timed out" not in remark:
                    return url, r.content, data
                print(f"  {url}: {remark[:120]}", file=sys.stderr)
            else:
                print(f"  {url}: HTTP {r.status_code}", file=sys.stderr)
        except requests.RequestException as error:
            print(f"  {url}: {type(error).__name__}", file=sys.stderr)
        time.sleep(min(10 * 2 ** (attempt // len(ENDPOINTS)), 60))
    raise RuntimeError("every endpoint failed; rerun to resume")


def main(out_dir):
    out_dir.mkdir(parents=True, exist_ok=True)
    log_path = out_dir / "fetch_log.json"
    log = json.loads(log_path.read_text()) if log_path.exists() else {}
    west, south, east, north = BBOX
    dx, dy = (east - west) / NX, (north - south) / NY
    for i in range(NX):
        for j in range(NY):
            name = f"bike_tile_{i}_{j}.json"
            if (out_dir / name).exists():
                continue
            w, s = west + i * dx, south + j * dy
            print(f"tile {name}", file=sys.stderr, flush=True)
            url, content, data = fetch(query(s, w, s + dy, w + dx))
            (out_dir / name).write_bytes(content)
            log[name] = dict(bbox=[w, s, w + dx, s + dy], endpoint=url, elements=len(data["elements"]),
                             osm_base=data.get("osm3s", {}).get("timestamp_osm_base"),
                             fetched_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"))
            log_path.write_text(json.dumps(log, indent=1))
            print(f"  ok: {log[name]['elements']} ways via {url}", file=sys.stderr, flush=True)


if __name__ == "__main__":
    main(Path(sys.argv[1]))
