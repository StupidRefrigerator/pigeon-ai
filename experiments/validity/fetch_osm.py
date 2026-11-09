"""Fetch OSM features around target hexes from Overpass, one query per 0.15-degree tile that holds targets. Cached."""
import json, os, sys, time, urllib.parse, urllib.request
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from targets import load_targets, OUT

URL = "https://overpass-api.de/api/interpreter"
UA = "pigeon-ai-uni-project (university research; contact via repo)"
CACHE = f"{OUT}/cache/osm"
TILE, MARGIN = 0.15, 0.006

FILTERS = """
  nwr["amenity"="toilets"];
  nwr["shop"~"^(mall|department_store|supermarket)$"];
  nwr["landuse"~"^(retail|commercial|residential|industrial)$"];
  way["building"~"^(retail|commercial)$"];
  nwr["leisure"~"^(park|playground|pitch|sports_centre|stadium|garden|recreation_ground)$"];
  nwr["natural"="beach"];
  nwr["railway"="station"];
  nwr["public_transport"="station"];
  nwr["amenity"~"^(library|community_centre|townhall|marketplace|bus_station|ferry_terminal|cafe|restaurant|fast_food|pub|bar)$"];
  way["highway"="pedestrian"];
  nwr["tourism"~"^(attraction|museum|viewpoint|zoo|theme_park|gallery|picnic_site)$"];
  node["shop"];
  node["place"~"^(suburb|neighbourhood|locality|quarter|town|village|city)$"];
"""


def fetch(bbox, path):
    if os.path.exists(path):
        return False
    s, w, n, e = bbox
    q = f"[out:json][timeout:300][bbox:{s:.5f},{w:.5f},{n:.5f},{e:.5f}];\n(\n{FILTERS});\nout tags geom;"
    data = urllib.parse.urlencode({"data": q}).encode()
    for attempt in range(5):
        try:
            req = urllib.request.Request(URL, data=data, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=360) as r:
                body = r.read()
            json.loads(body)
            with open(path + ".tmp", "wb") as f:
                f.write(body)
            os.replace(path + ".tmp", path)
            return True
        except Exception as ex:
            print("retry", attempt, bbox, ex, flush=True)
            time.sleep(30 * (attempt + 1))
    raise RuntimeError(f"failed {bbox}")


def main():
    os.makedirs(CACHE, exist_ok=True)
    t, _ = load_targets()
    t["ti"], t["tj"] = np.floor(t.lat / TILE).astype(int), np.floor(t.lng / TILE).astype(int)
    tiles = t.groupby(["ti", "tj"]).agg(s=("lat", "min"), n=("lat", "max"), w=("lng", "min"), e=("lng", "max"))
    manifest = []
    for (i, j), r in tiles.iterrows():
        bbox = (r.s - MARGIN, r.w - MARGIN, r.n + MARGIN, r.e + MARGIN)
        path = f"{CACHE}/tile_{i}_{j}.json"
        did = fetch(bbox, path)
        manifest.append({"tile": f"{i}_{j}", "bbox": bbox, "path": path})
        print(f"tile {i}_{j} {'fetched' if did else 'cached'} {os.path.getsize(path)/1e6:.1f} MB", flush=True)
        if did:
            time.sleep(5)
    json.dump(manifest, open(f"{CACHE}/manifest.json", "w"), indent=1)


if __name__ == "__main__":
    main()
