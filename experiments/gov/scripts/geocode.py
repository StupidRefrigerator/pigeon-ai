"""Geocode planned toilet sites with cached Nominatim + Overpass lookups.

Precedence per site: street intersection (geo_query with '&') -> Overpass named
park/feature (osm_name) near the suburb -> Nominatim free text.
"""
import csv, json, hashlib, os, sys, time, urllib.parse, urllib.request

WORK = "/tmp/pigeon-eval/gov"
CACHE = f"{WORK}/geocache"
UA = "pigeon-ai-uni-project"
VIEWBOX = "150.4,-33.4,151.4,-34.2"
os.makedirs(CACHE, exist_ok=True)
_last = [0.0]

def fetch(url, data=None):
    key = hashlib.sha1((url + (data or "")).encode()).hexdigest()
    path = f"{CACHE}/{key}.json"
    if os.path.exists(path):
        return json.load(open(path))
    wait = 1.1 - (time.time() - _last[0])
    if wait > 0:
        time.sleep(wait)
    urls = [url]
    if "overpass" in url:
        urls = ["https://maps.mail.ru/osm/tools/overpass/api/interpreter", url]
    out, err = None, None
    for attempt in range(6):
        u = urls[attempt % len(urls)]
        req = urllib.request.Request(u, data=data.encode() if data else None, headers={"User-Agent": UA})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                out = json.loads(r.read())
            break
        except Exception as e:
            err = e
            time.sleep(3 * (attempt + 1))
    _last[0] = time.time()
    if out is None:
        raise err
    json.dump(out, open(path, "w"))
    return out

def nominatim(q):
    url = "https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode(
        {"q": q, "format": "jsonv2", "countrycodes": "au", "viewbox": VIEWBOX, "bounded": 1, "limit": 3})
    return fetch(url)

def overpass(ql):
    return fetch("https://overpass-api.de/api/interpreter", "data=" + urllib.parse.quote(ql))

def suburb_point(suburb):
    res = nominatim(f"{suburb}, NSW")
    return (float(res[0]["lat"]), float(res[0]["lon"])) if res else None

def overpass_named(name, around):
    lat, lon = around
    ql = f"""[out:json][timeout:60];
(nwr["name"="{name}"](around:3000,{lat},{lon}););
out center tags;"""
    els = overpass(ql)["elements"]
    pref = ["leisure", "amenity", "natural", "landuse", "tourism", "building", "place"]
    def rank(e):
        t = e.get("tags", {})
        for i, k in enumerate(pref):
            if k in t:
                return i
        return 99
    els = [e for e in els if rank(e) < 99]
    if not els:
        return None
    e = sorted(els, key=rank)[0]
    c = e.get("center") or {"lat": e.get("lat"), "lon": e.get("lon")}
    tag = next(f"{k}={e['tags'][k]}" for k in pref if k in e["tags"])
    return c["lat"], c["lon"], tag

def intersection(q, around):
    streets = [s.strip() for s in q.split(",")[0].split("&")]
    lat, lon = around
    sets = []
    for s in streets:
        ql = f'[out:json][timeout:60];way["highway"]["name"="{s}"](around:2500,{lat},{lon});out geom;'
        pts = set()
        for w in overpass(ql)["elements"]:
            for p in w.get("geometry", []):
                pts.add((round(p["lat"], 7), round(p["lon"], 7)))
        sets.append(pts)
    common = set.intersection(*sets) if sets else set()
    if not common:
        return None
    la = sum(p[0] for p in common) / len(common)
    lo = sum(p[1] for p in common) / len(common)
    return la, lo

def classify(r):
    cls = r.get("category") or r.get("class")
    if cls in ("leisure", "amenity", "tourism", "natural", "building", "landuse", "railway", "shop"):
        return "exact feature/park centroid"
    if cls == "highway":
        return "street"
    if cls in ("place", "boundary"):
        return "suburb-only"
    return "exact feature/park centroid"

def main(seed, out):
    rows = list(csv.DictReader(open(seed), delimiter="|"))
    for r in rows:
        r["lat"] = r["lng"] = ""
        r["geocode_method"] = r["geocode_confidence"] = r["geocode_detail"] = ""
        if r.get("manual_lat"):
            r["lat"], r["lng"] = float(r["manual_lat"]), float(r["manual_lng"])
            r["geocode_method"], r["geocode_confidence"], r["geocode_detail"] = "manual", "park centroid (manual approx)", r["manual_note"]
            continue
        sub = suburb_point(r["suburb"])
        q = r["geo_query"]
        if "&" in q and sub:
            hit = intersection(q, sub)
            if hit:
                r["lat"], r["lng"] = hit
                r["geocode_method"], r["geocode_confidence"] = "overpass street intersection", "exact feature/park centroid"
                r["geocode_detail"] = q
                print(r["site_id"], "intersection", hit, flush=True)
                continue
        if r["osm_name"] and sub:
            hit = overpass_named(r["osm_name"], sub)
            if hit:
                r["lat"], r["lng"], tag = hit
                r["geocode_method"] = "overpass name"
                r["geocode_confidence"] = "street" if tag.startswith("place") else "exact feature/park centroid"
                r["geocode_detail"] = tag
                continue
        res = nominatim(q.replace("&", "and"))
        if res:
            r["lat"], r["lng"] = float(res[0]["lat"]), float(res[0]["lon"])
            r["geocode_method"] = "nominatim"
            r["geocode_confidence"] = classify(res[0])
            r["geocode_detail"] = f"{res[0].get('category')}={res[0].get('type')}: {res[0].get('display_name','')[:80]}"
        elif sub:
            r["lat"], r["lng"] = sub
            r["geocode_method"], r["geocode_confidence"], r["geocode_detail"] = "suburb fallback", "suburb-only", r["suburb"]
        print(r["site_id"], r["geocode_method"], r["geocode_confidence"], r["geocode_detail"][:70], flush=True)
    fields = list(rows[0].keys())
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
