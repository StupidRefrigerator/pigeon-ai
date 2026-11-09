"""Parse cached Overpass tiles into feature layers (EPSG:7856)."""
import glob
import json

import geopandas as gpd
import pandas as pd
import shapely
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import polygonize, unary_union

from hexsets import CRS, OUT

SPORTS = {"pitch", "sports_centre", "stadium", "track"}  # golf_course kept out (own layer, unused in features)


def _ring(coords):
    return [(c["lon"], c["lat"]) for c in coords if c is not None]


def _geometry(el):
    if el["type"] == "node":
        return Point(el["lon"], el["lat"])
    if el["type"] == "way":
        pts = _ring(el.get("geometry", []))
        if len(pts) >= 4 and pts[0] == pts[-1]:
            return Polygon(pts)
        return LineString(pts) if len(pts) >= 2 else None
    lines = {"outer": [], "inner": []}
    for m in el.get("members", []):
        if m["type"] == "way" and m.get("geometry"):
            pts = _ring(m["geometry"])
            if len(pts) >= 2:
                lines["inner" if m.get("role") == "inner" else "outer"].append(LineString(pts))
    outer = unary_union(list(polygonize(unary_union(lines["outer"])))) if lines["outer"] else None
    if outer is None or outer.is_empty:
        return None
    if lines["inner"]:
        inner = unary_union(list(polygonize(unary_union(lines["inner"]))))
        outer = outer.difference(inner)
    return outer


def load_elements():
    seen, rows = set(), []
    for path in sorted(p for p in glob.glob(f"{OUT}/downloads/overpass_*.json") if not p.endswith(".meta.json")):
        for el in json.load(open(path))["elements"]:
            key = (el["type"], el["id"])
            if key in seen:
                continue
            seen.add(key)
            geom = _geometry(el)
            if geom is None or geom.is_empty:
                continue
            rows.append({"osm_type": el["type"], "osm_id": el["id"], **el.get("tags", {}), "geometry": geom})
    gdf = gpd.GeoDataFrame(rows, geometry="geometry", crs=4326)
    gdf["geometry"] = gdf.geometry.make_valid()
    for col in ("leisure", "natural", "emergency", "club", "amenity", "name", "access", "fee", "operator", "sport", "highway"):
        if col not in gdf:
            gdf[col] = None
    return gdf


def is_slsc(g):
    name = g["name"].fillna("").str.contains(r"surf\s*life\s*saving|\bSLSC\b", case=False, regex=True)
    # Bus stops, AEDs, car parks and toilets named after a club are not the club itself.
    noise = g["highway"].notna() | (g["emergency"] == "defibrillator") | g["amenity"].isin(["parking", "toilets"])
    name = name & ~noise & ~g["name"].fillna("").str.contains("parking|opp ", case=False)
    club = g["club"].fillna("").str.contains("surf|lifesaving", case=False)
    emerg = g["emergency"].isin(["lifeguard", "lifeguard_base", "lifeguard_tower"])
    amen = g["amenity"].isin(["lifeguard", "surf_life_saving_club"])
    sport = g["sport"].fillna("").str.contains("life_?saving", case=False)
    return name | club | emerg | amen | sport


def layers():
    g = load_elements()
    out = {
        "sports": g[g.leisure.isin(SPORTS)],
        "golf": g[g.leisure == "golf_course"],
        "playground": g[g.leisure == "playground"],
        "beach": g[(g.natural == "beach") | (g.leisure == "beach_resort") | is_slsc(g)],
        "toilets": g[g.amenity == "toilets"],
    }
    res = {}
    for k, v in out.items():
        v = v.copy()
        # Counts use representative points taken BEFORE projection, as osm.py does.
        v["point"] = gpd.GeoSeries(v.geometry.representative_point(), crs=4326).to_crs(CRS)
        v = v.to_crs(CRS)
        res[k] = v
    return res
