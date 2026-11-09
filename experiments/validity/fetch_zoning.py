"""Fetch NSW LEP Land Zoning (layer 19) polygons intersecting each target hex. One request per hex, cached."""
import json, os, sys, time, urllib.parse, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import h3
from concurrent.futures import ThreadPoolExecutor
from targets import load_targets, OUT

URL = "https://mapprod3.environment.nsw.gov.au/arcgis/rest/services/ePlanning/Planning_Portal_Principal_Planning/MapServer/19/query"
UA = "pigeon-ai-uni-project"
CACHE = f"{OUT}/cache/zoning"
WORKERS = 3


def main():
    os.makedirs(CACHE, exist_ok=True)
    t, _ = load_targets()
    hexes = t.hex_id.unique()
    todo = [h for h in hexes if not os.path.exists(f"{CACHE}/{h}.json")]
    print("todo", len(todo), flush=True)
    with ThreadPoolExecutor(WORKERS) as ex:
        n_new = sum(ex.map(fetch_one, todo))
    print("done, new", n_new)


def fetch_one(h):
        path = f"{CACHE}/{h}.json"
        ring = [[lng, lat] for lat, lng in h3.cell_to_boundary(h)]
        ring.append(ring[0])
        params = {"geometry": json.dumps({"rings": [ring], "spatialReference": {"wkid": 4326}}),
                  "geometryType": "esriGeometryPolygon", "inSR": 4326, "outSR": 4326,
                  "spatialRel": "esriSpatialRelIntersects", "outFields": "SYM_CODE,LAY_CLASS,LGA_NAME",
                  "returnGeometry": "true", "maxAllowableOffset": 0.00002, "f": "json"}
        data = urllib.parse.urlencode(params).encode()
        for attempt in range(4):
            try:
                req = urllib.request.Request(URL, data=data, headers={"User-Agent": UA})
                with urllib.request.urlopen(req, timeout=60) as r:
                    body = r.read()
                d = json.loads(body)
                if "error" in d:
                    raise RuntimeError(d["error"])
                break
            except Exception as ex:
                print("retry", h, ex, flush=True)
                time.sleep(5 * (attempt + 1))
        else:
            print("FAILED", h, flush=True)
            return 0
        with open(path + ".tmp", "wb") as f:
            f.write(body)
        os.replace(path + ".tmp", path)
        time.sleep(0.2)
        return 1


if __name__ == "__main__":
    main()
