"""Download OSM sports / playground / beach / lifesaving / toilet features from Overpass, tiled and cached.

Usage: python -I fetch_osm.py   (writes downloads/overpass_tile_<i>_<j>.json and downloads/fetch_log.json)
"""
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

DOWNLOADS = Path("/Users/summitsetia/Desktop/University/26T3/pigeon-v2/data/downloads")
BBOX = (150.4939, -34.1406, 151.3624, -33.5211)  # all hexes + 1.5 km margin (see README)
NX, NY = 4, 3
ENDPOINTS = ["https://overpass-api.de/api/interpreter",
             "https://overpass.kumi.systems/api/interpreter",
             "https://overpass.private.coffee/api/interpreter"]
UA = {"User-Agent": "pigeon-ai-uni-project (research)"}

FILTERS = [
    'nwr["leisure"~"^(pitch|sports_centre|stadium|track|golf_course|playground|beach_resort)$"]',
    'nwr["natural"="beach"]',
    'nwr["emergency"~"^(lifeguard|lifeguard_base|lifeguard_tower)$"]',
    'nwr["club"~"surf|lifesaving",i]',
    'nwr["amenity"~"^(lifeguard|surf_life_saving_club)$"]',
    'nwr["sport"~"surf|lifesaving",i]',
    'nwr["amenity"="toilets"]',
]


def query(s, w, n, e):
    body = "".join(f"{f}({s},{w},{n},{e});" for f in FILTERS)
    return f"[out:json][timeout:300];({body});out tags geom;"


def fetch(q, path):
    for attempt in range(8):
        url = ENDPOINTS[attempt % len(ENDPOINTS)]
        try:
            r = requests.post(url, data={"data": q}, headers=UA, timeout=400)
            if r.ok and r.content.lstrip().startswith(b"{"):
                data = r.json()
                remark = data.get("remark", "")
                if "runtime error" in remark or "timed out" in remark:
                    raise RuntimeError(remark)
                path.write_bytes(r.content)
                return url
            print(f"  {url} -> HTTP {r.status_code}", file=sys.stderr)
        except Exception as exc:  # network / DNS / timeout: rotate endpoint and back off
            print(f"  {url} -> {type(exc).__name__}: {str(exc)[:120]}", file=sys.stderr)
        time.sleep(min(15 * 2 ** (attempt // len(ENDPOINTS)), 120))
    raise RuntimeError(f"all endpoints failed for {path.name}")


def tiles():
    """Original 4x3 grid; tiles not already cached as a whole are split 2x2."""
    west, south, east, north = BBOX
    dx, dy = (east - west) / NX, (north - south) / NY
    for i in range(NX):
        for j in range(NY):
            w, s = west + i * dx, south + j * dy
            if (DOWNLOADS / f"overpass_tile_{i}_{j}.json").exists():
                continue
            for a in range(2):
                for b in range(2):
                    yield (f"overpass_tile_{i}_{j}_{a}{b}.json",
                           (w + a * dx / 2, s + b * dy / 2, w + (a + 1) * dx / 2, s + (b + 1) * dy / 2))


def fetch_slsc_names():
    """Name-regex search for surf clubs is expensive, so it runs once over the coastal strip only
    (tiles fetched before 2026-11-10 13:00 UTC also carried it per tile)."""
    path = DOWNLOADS / "overpass_slsc_names.json"
    if not path.exists():
        w, s, e, n = 151.10, BBOX[1], BBOX[2], BBOX[3]
        q = f'[out:json][timeout:300];nwr["name"~"surf life ?saving|SLSC",i]({s},{w},{n},{e});out tags geom;'
        url = fetch(q, path)
        (DOWNLOADS / (path.name + ".meta.json")).write_text(json.dumps(dict(
            bbox=[w, s, e, n], endpoint=url, elements=len(json.loads(path.read_text())["elements"]),
            fetched_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"))))


def fine_tiles():
    """Subtiles that kept failing with 502/504 are split 2x2 once more."""
    for name, (w, s, e, n) in tiles():
        if (DOWNLOADS / name).exists():
            continue
        hx, hy = (e - w) / 2, (n - s) / 2
        for c in range(2):
            for d in range(2):
                yield (name.replace(".json", f"_{c}{d}.json"),
                       (w + c * hx, s + d * hy, w + (c + 1) * hx, s + (d + 1) * hy))


def main_split(reverse=False, fine=False):
    todo = list(fine_tiles() if fine else tiles())
    for name, (w, s, e, n) in (reversed(todo) if reverse else todo):
        path = DOWNLOADS / name
        lock = DOWNLOADS / (name + ".lock")
        if path.exists() or lock.exists():
            continue
        lock.touch()
        try:
            print(f"tile {name}", file=sys.stderr, flush=True)
            url = fetch(query(s, w, n, e), path)
            data = json.loads(path.read_text())
            meta = dict(bbox=[w, s, e, n], endpoint=url, elements=len(data["elements"]),
                        osm_base=data.get("osm3s", {}).get("timestamp_osm_base"),
                        fetched_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"))
            (DOWNLOADS / (name + ".meta.json")).write_text(json.dumps(meta))
            print(f"  ok {meta['elements']} elements via {url}", file=sys.stderr, flush=True)
        finally:
            lock.unlink()


def main():
    DOWNLOADS.mkdir(parents=True, exist_ok=True)
    west, south, east, north = BBOX
    dx, dy = (east - west) / NX, (north - south) / NY
    log_path = DOWNLOADS / "fetch_log.json"
    log = json.loads(log_path.read_text()) if log_path.exists() else {}
    for i in range(NX):
        for j in range(NY):
            w, e = west + i * dx, west + (i + 1) * dx
            s, n = south + j * dy, south + (j + 1) * dy
            if (DOWNLOADS / f"overpass_tile_{i}_{j}.json").exists():
                continue
            # Remaining (denser) tiles are split 2x2 so each query stays well under the server limit.
            for a in range(2):
                for b in range(2):
                    sw, se = w + a * dx / 2, w + (a + 1) * dx / 2
                    ss, sn = s + b * dy / 2, s + (b + 1) * dy / 2
                    path = DOWNLOADS / f"overpass_tile_{i}_{j}_{a}{b}.json"
                    if path.exists():
                        continue
                    print(f"tile {path.name}", file=sys.stderr, flush=True)
                    url = fetch(query(ss, sw, sn, se), path)
                    data = json.loads(path.read_text())
                    log[path.name] = dict(bbox=[sw, ss, se, sn], endpoint=url, elements=len(data["elements"]),
                                          osm_base=data.get("osm3s", {}).get("timestamp_osm_base"),
                                          fetched_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"))
                    log_path.write_text(json.dumps(log, indent=1))
                    print(f"  ok {log[path.name]['elements']} elements via {url}", file=sys.stderr, flush=True)


if __name__ == "__main__":
    if "--slsc" in sys.argv:
        fetch_slsc_names()
    else:
        main_split(reverse="--reverse" in sys.argv, fine="--fine" in sys.argv)
