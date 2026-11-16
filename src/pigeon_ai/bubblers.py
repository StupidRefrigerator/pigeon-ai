"""Water fountain (bubbler) labels: council records plus OpenStreetMap, counted per res-9 hexagon.

The label is a union. Every council point counts. An OSM fountain counts only when no council
point lies within MATCH_M, so a fountain on both maps counts once. The downloads are in
data/raw/bubblers/ (see DATA.md); scripts/build_bubblers.py writes the processed files.
"""
import json

import geopandas as gpd
import h3
import pandas as pd
from shapely.geometry import Point

from .paths import CRS, PROCESSED, RAW

RAW_DIR = RAW / "bubblers"
POINTS_FILE = PROCESSED / "bubbler_points.csv"
LABELS_FILE = PROCESSED / "bubbler_labels.csv"
LABEL = "bubbler_count"
MATCH_M = 50
NOT_PUBLIC = {"private", "customers", "no"}

# File stem in RAW_DIR/official -> the council it covers. Penrith and Fairfield are partial layers.
OFFICIAL = {
    "cos_fountains": "SYDNEY",
    "parramatta_fountains": "CITY OF PARRAMATTA",
    "fairfield_bubblers": "FAIRFIELD",
    "northern_beaches_bubblers": "NORTHERN BEACHES",
    "penrith_bubblers": "PENRITH",
}
POINT_COLUMNS = ["source", "council", "rule", "osm_id", "lat", "lng", "hex_id", "counted"]
LABEL_COLUMNS = ["hex_id", "area", "lga", "bubbler_osm", "bubbler_official", LABEL]


def osm_rule(tags):
    """The inclusion rule a feature meets, or None. First match wins.

    A toilet block, shelter or BBQ that merely has drinking water is not a fountain, so a tap
    or fountain counts only with drinking_water=yes.
    """
    if tags.get("access") in NOT_PUBLIC:
        return None
    dw = tags.get("drinking_water")
    if tags.get("amenity") == "drinking_water" and dw != "no":
        return "amenity=drinking_water"
    if dw == "yes" and tags.get("man_made") in {"water_tap", "tap", "drinking_fountain"}:
        return "man_made=water_tap|tap|drinking_fountain + drinking_water=yes"
    if tags.get("man_made") == "drinking_fountain" and dw != "no":
        return "man_made=drinking_fountain"
    if dw == "yes" and tags.get("amenity") in {"water_point", "fountain"}:
        return "amenity=water_point|fountain + drinking_water=yes"
    if dw == "yes" and tags.get("amenity") is None and tags.get("man_made") is None:
        return "untyped feature + drinking_water=yes"
    return None


def load_osm(path):
    """OSM fountains that meet a rule, and a count of every rule and exclusion."""
    rows, skipped = [], {}
    for e in json.loads(path.read_text())["elements"]:
        tags = e.get("tags", {})
        rule = osm_rule(tags)
        if rule is None:
            key = (f"excluded: access={tags['access']}" if tags.get("access") in NOT_PUBLIC else
                   f"excluded: amenity={tags.get('amenity')} man_made={tags.get('man_made')} "
                   f"drinking_water={tags.get('drinking_water')}")
            skipped[key] = skipped.get(key, 0) + 1
            continue
        lat, lng = (e["lat"], e["lon"]) if e["type"] == "node" else (e["center"]["lat"], e["center"]["lon"])
        rows.append(dict(source="osm", rule=rule, osm_id=f"{e['type']}/{e['id']}", lat=lat, lng=lng))
    osm = pd.DataFrame(rows)
    tag_counts = pd.concat([
        osm["rule"].value_counts().rename("count").rename_axis("rule").reset_index(),
        pd.DataFrame(sorted(skipped.items(), key=lambda kv: -kv[1]), columns=["rule", "count"]),
    ])
    return osm, tag_counts


def load_official(folder):
    rows = []
    for stem, council in OFFICIAL.items():
        for f in json.loads((folder / f"{stem}.geojson").read_text())["features"]:
            if f["geometry"] is None:
                continue
            lng, lat = f["geometry"]["coordinates"][:2]
            rows.append(dict(source=stem, council=council, lat=float(lat), lng=float(lng)))
    return pd.DataFrame(rows)


def to_gdf(df):
    return gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df.lng, df.lat), crs=4326).to_crs(CRS)


def nearest_m(points, targets):
    """Metres from each point to the nearest target."""
    near = gpd.sjoin_nearest(points[["geometry"]], targets[["geometry"]], how="left", distance_col="d")
    return near[~near.index.duplicated()]["d"]


def build_points(osm, official, lga):
    """Every OSM and council point, with the council it lies in and whether the label counts it."""
    g_osm, g_off = to_gdf(osm), to_gdf(official)
    g_osm["council"] = gpd.sjoin(g_osm, lga, how="left", predicate="within").pipe(
        lambda j: j[~j.index.duplicated()]["lganame"])
    g_osm["counted"] = ~(nearest_m(g_osm, g_off) <= MATCH_M)
    points = pd.concat([g_osm, g_off.assign(counted=True)], ignore_index=True)
    points["hex_id"] = [h3.latlng_to_cell(a, b, 9) for a, b in zip(points.lat, points.lng)]
    return pd.DataFrame(points[POINT_COLUMNS])


def coverage(points):
    """Per council layer: how many council points have an OSM fountain within MATCH_M, and the reverse."""
    g = to_gdf(points)
    osm = g[g.source == "osm"]
    rows = []
    for stem, council in OFFICIAL.items():
        off = g[g.source == stem]
        osm_in = osm[osm.council == council]
        off_matched = nearest_m(off, osm) <= MATCH_M
        rows.append(dict(source=stem, council=council, official=len(off), official_with_osm_50m=int(off_matched.sum()),
                         share=off_matched.mean(), osm_in_council=len(osm_in),
                         osm_with_official_50m=int((nearest_m(osm_in, off) <= MATCH_M).sum())))
    return pd.DataFrame(rows)


def hex_labels(points, hexes, lga):
    """One row per hexagon: its council (by centre) and its OSM, council and union counts.

    `hexes` has hex_id and area columns.
    """
    centres = [Point(lng, lat) for lat, lng in (h3.cell_to_latlng(h) for h in hexes.hex_id)]
    hg = gpd.GeoDataFrame(hexes[["hex_id"]], geometry=centres, crs=4326).to_crs(CRS)
    hg = gpd.sjoin(hg, lga, how="left", predicate="within")
    hg = hg[~hg.index.duplicated()]
    labels = hexes.assign(lga=hg["lganame"].fillna("OUTSIDE_NSW_LGA").to_numpy())
    for name, mask in [("bubbler_osm", points.source == "osm"), ("bubbler_official", points.source != "osm"),
                       (LABEL, points.counted)]:
        labels[name] = labels.hex_id.map(points[mask].hex_id.value_counts()).fillna(0).astype(int)
    return labels[LABEL_COLUMNS]
