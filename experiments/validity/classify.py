"""Proxy review: classify each target hex from OSM features and NSW zoning. Writes hex_osm_classified.csv."""
import json, os, sys
from collections import Counter
import numpy as np, pandas as pd, geopandas as gpd, h3
from shapely.geometry import Point, LineString, Polygon, shape
from shapely.ops import polygonize, unary_union
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from targets import load_targets, OUT

CRS = 32756
NEAR_M = 150
TOILET_SNAP_M = 50          # point-mapping slack around the hex edge for toilets / stations
PARK_MIN_M2 = 1500          # park polygon area inside the hex to count as a park in the hex
RETAIL_LANDUSE_MIN_M2 = 20000
RETAIL_BUILDING_MIN_M2 = 5000
PED_MIN_M = 50
COMMERCIAL_POI_MIN = 8
COMMERCIAL_SHARE_MIN = 0.25
RES_IND_SHARE_MIN = 0.25
ZONE_RECREATION_MIN = 0.3
BIG_PARK_M2 = 10000
STRONG_KINDS = {"beach", "library", "townhall", "community_centre", "marketplace", "bus_station", "ferry_terminal", "stadium", "sports_centre"}
PUBLIC_ACCESS = {"yes", "public", "permissive", "missing", "destination"}
CUSTOMER_ACCESS = {"customers", "private", "no", "permit", "employees", "students", "residents"}

PRECEDENCE = ["toilet_already_mapped_public", "toilet_customers_or_private", "shopping_centre",
              "public_destination", "commercial_street", "residential_or_industrial_only", "unknown"]

AREA_TAGS = ("landuse", "leisure", "natural", "building", "shop", "amenity", "tourism", "railway", "public_transport", "highway")


def element_geom(el):
    if el["type"] == "node":
        return Point(el["lon"], el["lat"])
    if el["type"] == "way":
        pts = [(p["lon"], p["lat"]) for p in el.get("geometry", []) if p]
        if len(pts) < 2:
            return None
        tags = el.get("tags", {})
        closed = pts[0] == pts[-1] and len(pts) >= 4
        if closed and tags.get("highway") != "pedestrian" or (closed and tags.get("area") == "yes"):
            return Polygon(pts)
        return LineString(pts)
    if el["type"] == "relation":
        lines = []
        for m in el.get("members", []):
            g = m.get("geometry")
            if m.get("type") == "way" and g and m.get("role", "outer") in ("outer", ""):
                pts = [(p["lon"], p["lat"]) for p in g if p]
                if len(pts) >= 2:
                    lines.append(LineString(pts))
        polys = list(polygonize(unary_union(lines))) if lines else []
        return unary_union(polys) if polys else None
    return None


def feature_kind(tags):
    k = []
    a, s, lu, le = tags.get("amenity"), tags.get("shop"), tags.get("landuse"), tags.get("leisure")
    if a == "toilets": k.append("toilet")
    if s == "mall": k.append("mall")
    if s == "department_store": k.append("department_store")
    if s == "supermarket": k.append("supermarket")
    if s: k.append("shop")
    if a in ("cafe", "restaurant", "fast_food", "pub", "bar"): k.append("food")
    if lu in ("retail", "commercial", "residential", "industrial"): k.append(f"landuse_{lu}")
    if tags.get("building") == "retail": k.append("building_retail")
    if le in ("park", "garden", "recreation_ground"): k.append("park")
    if le in ("playground", "pitch", "sports_centre", "stadium"): k.append(le)
    if tags.get("natural") == "beach": k.append("beach")
    if tags.get("railway") == "station" or tags.get("public_transport") == "station": k.append("station")
    if a in ("library", "community_centre", "townhall", "marketplace", "bus_station", "ferry_terminal"): k.append(a)
    if tags.get("highway") == "pedestrian": k.append("pedestrian")
    if tags.get("tourism") in ("attraction", "museum", "viewpoint", "zoo", "theme_park", "gallery", "picnic_site"): k.append("tourism")
    if tags.get("place"): k.append("place")
    return k


def load_osm():
    manifest = json.load(open(f"{OUT}/cache/osm/manifest.json"))
    seen, rows = set(), []
    for m in manifest:
        for el in json.load(open(m["path"]))["elements"]:
            key = (el["type"], el["id"])
            if key in seen:
                continue
            seen.add(key)
            tags = el.get("tags", {})
            kinds = feature_kind(tags)
            if not kinds:
                continue
            g = element_geom(el)
            if g is None or g.is_empty:
                continue
            if not g.is_valid:
                g = g.buffer(0)
            rows.append({"osm": f"{el['type']}/{el['id']}", "kinds": kinds, "name": tags.get("name", ""),
                         "access": tags.get("access", "missing"), "place": tags.get("place", ""), "geometry": g})
    gdf = gpd.GeoDataFrame(rows, geometry="geometry", crs=4326).to_crs(CRS)
    gdf["area"] = gdf.geometry.area
    return gdf.explode("kinds").rename(columns={"kinds": "kind"}).reset_index(drop=True)


def load_zoning(hex_id, hexpoly_proj):
    path = f"{OUT}/cache/zoning/{hex_id}.json"
    if not os.path.exists(path):
        pt = f"{OUT}/cache/zoning_point/{hex_id}.json"
        if not os.path.exists(pt):
            return {}, ""
        feats = json.load(open(pt)).get("features", [])
        if not feats:
            return {}, ""
        a = feats[0]["attributes"]
        return {(a.get("SYM_CODE") or "?"): 1.0}, a.get("LGA_NAME", "")
    d = json.load(open(path))
    shares, lga = Counter(), ""
    for f in d.get("features", []):
        rings = f.get("geometry", {}).get("rings")
        if not rings:
            continue
        polys = [Polygon(r) for r in rings if len(r) >= 4]
        g = gpd.GeoSeries(polys, crs=4326).to_crs(CRS).buffer(0)
        geom = unary_union(list(g))
        inter = geom.intersection(hexpoly_proj).area
        shares[f["attributes"].get("SYM_CODE") or "?"] += inter
        lga = lga or f["attributes"].get("LGA_NAME", "")
    tot = hexpoly_proj.area
    return {k: min(v / tot, 1.0) for k, v in shares.items() if v > 0}, lga


def zone_group(code):
    if not code: return ""
    c = code.upper()
    if c.startswith("R") and not c.startswith("RE") and not c.startswith("RU"): return "residential"
    if c.startswith("RE"): return "recreation"
    if c.startswith("IN") or c in ("E3", "E4", "E5"): return "industrial"
    if c.startswith("B") or c in ("E1", "E2", "MU1", "SP5"): return "commercial"
    if c.startswith("SP"): return "special_purpose"
    if c.startswith("C") or c.startswith("E") or c.startswith("W") or c.startswith("RU"): return "conservation_rural_water"
    return "other"


def classify_hex(hex_id, F, sidx, use_toilets=True):
    P = gpd.GeoSeries([Polygon([(lng, lat) for lat, lng in h3.cell_to_boundary(hex_id)])], crs=4326).to_crs(CRS).iloc[0]
    P50, B = P.buffer(TOILET_SNAP_M), P.buffer(NEAR_M)
    idx = sidx.query(B, predicate="intersects")
    near = F.iloc[idx]
    inside = near[near.intersects(P)]
    inside_inter = inside.geometry.intersection(P)
    r = {"hex_id": hex_id}
    ev = []

    def named(df, n=2):
        return ", ".join(list(dict.fromkeys(x for x in df.name.tolist() if x))[:n])

    t50 = near[(near.kind == "toilet") & near.intersects(P50)]
    t150 = near[near.kind == "toilet"]
    acc = Counter(t50.access)
    r["osm_toilets_in_hex"] = len(t50)
    r["osm_toilets_within_150m"] = len(t150)
    r["osm_toilet_access"] = ";".join(f"{k}:{v}" for k, v in sorted(acc.items()))
    pub = t50[t50.access.isin(PUBLIC_ACCESS)]
    cust = t50[t50.access.isin(CUSTOMER_ACCESS)]
    r["osm_public_toilets_in_hex"] = len(pub)
    r["osm_public_toilet_access_missing_only"] = bool(len(pub) and (pub.access == "missing").all())
    r["osm_customer_private_toilets_in_hex"] = len(cust)

    mall = inside[inside.kind == "mall"]
    dept = inside[inside.kind == "department_store"]
    lu_retail_big = inside[(inside.kind == "landuse_retail") & (inside.area >= RETAIL_LANDUSE_MIN_M2)]
    bld_retail_big = inside[(inside.kind == "building_retail") & (inside.area >= RETAIL_BUILDING_MIN_M2)]
    r["mall"] = named(mall) or ("unnamed mall" if len(mall) else "")
    r["department_store"] = named(dept)
    r["large_retail"] = len(lu_retail_big) + len(bld_retail_big)
    shopping = len(mall) > 0 or len(lu_retail_big) > 0 or len(bld_retail_big) > 0

    is_park = (inside.kind == "park") & (inside_inter.area >= PARK_MIN_M2)
    dest_mask = is_park | inside.kind.isin(["playground", "sports_centre", "stadium", "beach", "library", "community_centre",
                                            "townhall", "marketplace", "bus_station", "ferry_terminal", "tourism"])
    dest_mask |= (inside.kind == "pitch") & (inside.access != "private")
    dest_mask &= ~inside.access.isin(["private", "no"])
    ped = inside[(inside.kind == "pedestrian")]
    ped_len = ped.geometry.intersection(P).length.sum() if len(ped) else 0.0
    stations = near[(near.kind == "station") & near.intersects(P50)]
    dest = inside[dest_mask]
    big_park = (is_park & (inside_inter.area >= BIG_PARK_M2)).any()
    strong = set(dest.kind) & STRONG_KINDS
    strong |= ({"station"} if len(stations) else set()) | ({"pedestrian_street"} if ped_len >= PED_MIN_M else set()) | ({"park_1ha"} if big_park else set())
    r["strong_destinations"] = ";".join(sorted(strong))
    dest_kinds = sorted(set(dest.kind) | ({"station"} if len(stations) else set()) | ({"pedestrian_street"} if ped_len >= PED_MIN_M else set()))
    r["destinations_in_hex"] = ";".join(dest_kinds)
    r["destination_names"] = named(pd.concat([stations, dest]), 3)
    near_only = near[near.kind.isin(["park", "playground", "beach", "station", "library", "community_centre", "tourism", "mall"]) & ~near.index.isin(inside.index)]
    r["destinations_within_150m"] = ";".join(sorted(set(near_only.kind)))
    zones, lga = load_zoning(hex_id, P)
    r["zoning_source"] = "hex_polygon" if os.path.exists(f"{OUT}/cache/zoning/{hex_id}.json") else ("centre_point" if zones else "none")
    if sum(v for k, v in zones.items() if zone_group(k) == "recreation") >= ZONE_RECREATION_MIN:
        dest_kinds.append("zoned_public_recreation")
        r["destinations_in_hex"] = ";".join(dest_kinds)
    public_dest = len(dest_kinds) > 0

    pois = inside[inside.kind.isin(["shop", "food"]) & (inside.geometry.geom_type == "Point")]
    r["shops_food_in_hex"] = pois.osm.nunique()
    lu = {}
    for k in ("residential", "industrial", "commercial", "retail"):
        sub = inside_inter[inside.kind == f"landuse_{k}"]
        lu[k] = unary_union(list(sub)).area / P.area if len(sub) else 0.0
    r.update({f"landuse_{k}_share": round(v, 3) for k, v in lu.items()})
    dom = max(lu, key=lu.get)
    r["dominant_landuse"] = dom if lu[dom] > 0.05 else ""
    zmain = max(zones, key=zones.get) if zones else ""
    r["zoning_main"] = zmain
    r["zoning_main_share"] = round(zones.get(zmain, 0), 3) if zmain else np.nan
    r["zoning_all"] = ";".join(f"{k}:{v:.2f}" for k, v in sorted(zones.items(), key=lambda kv: -kv[1]) if v >= 0.05)
    r["lga"] = lga
    zg = zone_group(zmain)
    commercial = r["shops_food_in_hex"] >= COMMERCIAL_POI_MIN or (lu["commercial"] + lu["retail"]) >= COMMERCIAL_SHARE_MIN
    commercial = commercial or zg == "commercial"
    res_ind = (lu["residential"] + lu["industrial"]) >= RES_IND_SHARE_MIN or zg in ("residential", "industrial")

    if use_toilets and len(pub):
        cat = "toilet_already_mapped_public"; ev.append(f"OSM toilet in hex ({r['osm_toilet_access']})")
    elif use_toilets and len(cust):
        cat = "toilet_customers_or_private"; ev.append(f"OSM toilet in hex ({r['osm_toilet_access']})")
    elif shopping:
        cat = "shopping_centre"
    elif public_dest:
        cat = "public_destination"
    elif commercial:
        cat = "commercial_street"
    elif res_ind:
        cat = "residential_or_industrial_only"
    else:
        cat = "unknown"
    if shopping: ev.append(f"shopping: {r['mall'] or r['department_store'] or 'large retail polygon'}")
    if public_dest: ev.append(f"destinations: {r['destinations_in_hex']}" + (f" ({r['destination_names']})" if r["destination_names"] else ""))
    if r["destinations_within_150m"]: ev.append(f"within 150m: {r['destinations_within_150m']}")
    ev.append(f"{r['shops_food_in_hex']} shops/food")
    if r["dominant_landuse"]: ev.append(f"landuse {r['dominant_landuse']} {lu[r['dominant_landuse']]:.0%}")
    if zmain: ev.append(f"zone {zmain} {zones[zmain]:.0%}")
    r["category"] = cat
    r["destination_tier"] = ("strong" if strong else "weak") if cat == "public_destination" else ""
    r["evidence"] = "; ".join(ev)
    return r


def nearest_place(F, pts):
    places = F[F.kind == "place"]
    places = places[places.place.isin(["suburb", "neighbourhood", "quarter", "locality", "town", "village"])]
    j = gpd.sjoin_nearest(pts, places[["name", "place", "geometry"]], how="left", distance_col="place_dist_m")
    j = j[~j.index.duplicated()]
    return j["name"].fillna(""), j["place_dist_m"]


def main():
    t, _ = load_targets()
    F = load_osm()
    print("features", len(F), F.kind.value_counts().head(25).to_dict(), flush=True)
    sidx = F.sindex
    hexes = t.hex_id.unique()
    full = pd.DataFrame([classify_hex(h, F, sidx) for h in hexes])
    site = pd.DataFrame([{"hex_id": h, "category_site_only": classify_hex(h, F, sidx, use_toilets=False)["category"]} for h in hexes])
    out = full.merge(site, on="hex_id")
    ll = out.hex_id.map(h3.cell_to_latlng)
    pts = gpd.GeoDataFrame(out[["hex_id"]], geometry=[Point(b, a) for a, b in ll], crs=4326).to_crs(CRS)
    out["nearest_suburb"], out["nearest_suburb_dist_m"] = nearest_place(F, pts)
    out["lat"], out["lng"] = [a for a, _ in ll], [b for _, b in ll]
    out.to_csv(f"{OUT}/hex_osm_classified.csv", index=False)
    print(out.category.value_counts())


if __name__ == "__main__":
    main()
