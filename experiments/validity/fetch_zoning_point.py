"""Fallback for hexes whose zoning polygon query failed: zone at the hex centre point (no geometry). Cached."""
import json, os, sys, time, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import h3
from targets import load_targets, OUT
from fetch_zoning import URL, UA

CACHE = f"{OUT}/cache/zoning_point"


def fetch_one(h):
    path = f"{CACHE}/{h}.json"
    lat, lng = h3.cell_to_latlng(h)
    q = urllib.parse.urlencode({"geometry": f"{lng},{lat}", "geometryType": "esriGeometryPoint", "inSR": 4326,
                                "spatialRel": "esriSpatialRelIntersects", "outFields": "SYM_CODE,LAY_CLASS,LGA_NAME",
                                "returnGeometry": "false", "f": "json"})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(f"{URL}?{q}", headers={"User-Agent": UA}), timeout=60) as r:
                body = r.read()
            if "error" in json.loads(body):
                raise RuntimeError(body[:200])
            with open(path + ".tmp", "wb") as f:
                f.write(body)
            os.replace(path + ".tmp", path)
            return 1
        except Exception as ex:
            print("retry", h, ex, flush=True)
            time.sleep(5 * (attempt + 1))
    print("FAILED", h, flush=True)
    return 0


def main():
    os.makedirs(CACHE, exist_ok=True)
    t, _ = load_targets()
    todo = [h for h in t.hex_id.unique() if not os.path.exists(f"{OUT}/cache/zoning/{h}.json") and not os.path.exists(f"{CACHE}/{h}.json")]
    print("todo", len(todo), flush=True)
    with ThreadPoolExecutor(3) as ex:
        print("done, new", sum(ex.map(fetch_one, todo)), flush=True)


if __name__ == "__main__":
    main()
