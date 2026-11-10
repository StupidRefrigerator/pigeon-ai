"""V12 features from cached Overpass tiles: sports grounds, playgrounds, beaches and OSM toilets.

The tiles live in data/raw/osm_overpass_v12/ (see DATA.md); scripts/fetch_overpass.py refreshes them.
Conventions match osm.py: EPSG:7856, representative points taken before projection,
`within` for inside counts, `intersects` with 16-segment centroid circles for buffer counts,
8-segment circles for areas, and distances to all features in the download.
"""
import json

import geopandas as gpd
import h3
import pandas as pd
from shapely import area, buffer, intersection
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import polygonize, unary_union

from .paths import CRS, RAW

OVERPASS_DIR = RAW / "osm_overpass_v12"
SPORTS = {"pitch", "sports_centre", "stadium", "track"}
RADII = (250, 500, 1000)
PUBLIC = {"yes", "permissive", "public"}
PRIVATE = {"customers", "private", "no"}

RECREATION_FEATURES = [
    "sports_inside", "sports_250m", "sports_500m", "sports_1000m", "sports_area_inside_m2",
    "sports_area_500m_m2", "playground_inside", "playground_250m", "playground_500m", "playground_1000m",
    "beach_inside", "beach_250m", "beach_500m", "beach_1000m", "distance_nearest_beach_m",
    "distance_nearest_sports_m", "distance_nearest_playground_m",
]
# Near-copies of the label: used after the model, never as inputs.
OSM_TOILET_COLUMNS = ["osm_toilets_public", "osm_toilets_public_tagged", "osm_toilets_private"]
TOILET_POINT_COLUMNS = ["lat", "lng", "access", "fee", "name", "operator", "osm_type", "osm_id", "hex_id",
                        "is_public", "is_public_tagged", "is_private"]


# Parsing

def _ring(coords):
    return [(c["lon"], c["lat"]) for c in coords if c is not None]


def _geometry(element):
    if element["type"] == "node":
        return Point(element["lon"], element["lat"])
    if element["type"] == "way":
        points = _ring(element.get("geometry", []))
        if len(points) >= 4 and points[0] == points[-1]:
            return Polygon(points)
        return LineString(points) if len(points) >= 2 else None
    lines = {"outer": [], "inner": []}
    for member in element.get("members", []):
        if member["type"] == "way" and member.get("geometry"):
            points = _ring(member["geometry"])
            if len(points) >= 2:
                lines["inner" if member.get("role") == "inner" else "outer"].append(LineString(points))
    outer = unary_union(list(polygonize(unary_union(lines["outer"])))) if lines["outer"] else None
    if outer is None or outer.is_empty:
        return None
    if lines["inner"]:
        outer = outer.difference(unary_union(list(polygonize(unary_union(lines["inner"])))))
    return outer


def load_elements(folder=OVERPASS_DIR):
    """Every Overpass element once, keyed by (type, id); tiles overlap on their edges."""
    paths = sorted(p for p in folder.glob("overpass_*.json") if not p.name.endswith(".meta.json"))
    if not paths:
        raise FileNotFoundError(f"No overpass_*.json in {folder}; see DATA.md")
    seen, rows = set(), []
    for path in paths:
        for element in json.loads(path.read_text())["elements"]:
            key = (element["type"], element["id"])
            if key in seen:
                continue
            seen.add(key)
            geometry = _geometry(element)
            if geometry is None or geometry.is_empty:
                continue
            rows.append({"osm_type": element["type"], "osm_id": element["id"],
                         **element.get("tags", {}), "geometry": geometry})
    elements = gpd.GeoDataFrame(rows, geometry="geometry", crs=4326)
    elements["geometry"] = elements.geometry.make_valid()
    for tag in ("leisure", "natural", "emergency", "club", "amenity", "name", "access", "fee",
                "operator", "sport", "highway"):
        if tag not in elements:
            elements[tag] = None
    return elements


def is_surf_club(elements):
    name = elements["name"].fillna("")
    named = name.str.contains(r"surf\s*life\s*saving|\bSLSC\b", case=False, regex=True)
    # Bus stops, defibrillators, car parks and toilets named after a club are not the club.
    noise = (elements["highway"].notna() | (elements["emergency"] == "defibrillator")
             | elements["amenity"].isin(["parking", "toilets"]) | name.str.contains("parking|opp ", case=False))
    club = elements["club"].fillna("").str.contains("surf|lifesaving", case=False)
    lifeguard = elements["emergency"].isin(["lifeguard", "lifeguard_base", "lifeguard_tower"])
    amenity = elements["amenity"].isin(["lifeguard", "surf_life_saving_club"])
    sport = elements["sport"].fillna("").str.contains("life_?saving", case=False)
    return (named & ~noise) | club | lifeguard | amenity | sport


def load_layers(folder=OVERPASS_DIR):
    """sports, playground, beach and toilets layers in EPSG:7856, each with a projected `point`."""
    e = load_elements(folder)
    layers = {
        "sports": e[e.leisure.isin(SPORTS)],
        "playground": e[e.leisure == "playground"],
        "beach": e[(e.natural == "beach") | (e.leisure == "beach_resort") | is_surf_club(e)],
        "toilets": e[e.amenity == "toilets"],
    }
    out = {}
    for name, layer in layers.items():
        layer = layer.copy()
        layer["point"] = gpd.GeoSeries(layer.geometry.representative_point(), crs=4326).to_crs(CRS)
        out[name] = layer.to_crs(CRS)
    return out


# Per-hex features

def hex_grid(hex_ids):
    geometry = [Polygon([(lng, lat) for lat, lng in h3.cell_to_boundary(c)]) for c in hex_ids]
    return gpd.GeoDataFrame({"hex_id": list(hex_ids)}, geometry=geometry, crs=4326).to_crs(CRS)


def counts(grid, layer, prefix):
    points = gpd.GeoDataFrame(geometry=layer["point"].values, crs=grid.crs)
    out = pd.DataFrame({"hex_id": grid.hex_id})
    inside = gpd.sjoin(points, grid[["hex_id", "geometry"]], how="inner", predicate="within")
    out[f"{prefix}_inside"] = out.hex_id.map(inside.groupby("hex_id").size()).fillna(0).astype(int).values
    centres = grid.geometry.centroid
    for radius in RADII:
        zones = gpd.GeoDataFrame({"hex_id": grid.hex_id}, geometry=centres.buffer(radius), crs=grid.crs)
        matches = gpd.sjoin(zones, points, how="left", predicate="intersects")
        found = matches.groupby("hex_id")["index_right"].count()
        out[f"{prefix}_{radius}m"] = out.hex_id.map(found).fillna(0).astype(int).values
    return out.set_index("hex_id")


def areas(grid, layer, prefix):
    """Area of the union of polygons, so a pitch inside a stadium counts once."""
    union = layer[layer.geom_type.isin(["Polygon", "MultiPolygon"])].geometry.union_all()
    out = pd.DataFrame(index=grid.hex_id.values)
    out[f"{prefix}_area_inside_m2"] = area(intersection(grid.geometry.array, union))
    out[f"{prefix}_area_500m_m2"] = area(intersection(buffer(grid.geometry.centroid.array, 500), union))
    return out


def nearest(grid, layer, column):
    centres = gpd.GeoDataFrame({"hex_id": grid.hex_id}, geometry=grid.geometry.centroid, crs=grid.crs)
    joined = gpd.sjoin_nearest(centres, layer[["geometry"]], how="left", distance_col="d")
    return joined.groupby("hex_id")["d"].min().rename(column)


def toilet_points(toilets):
    """One row per OSM toilet with its H3 cell and access group."""
    t = toilets.copy()
    lonlat = t["point"].to_crs(4326)
    t["lat"], t["lng"] = lonlat.y.values, lonlat.x.values
    t["hex_id"] = [h3.latlng_to_cell(a, b, 9) for a, b in zip(t.lat, t.lng)]
    t["is_public"] = t["access"].isna() | t["access"].isin(PUBLIC)
    t["is_public_tagged"] = t["access"].isin(PUBLIC)
    t["is_private"] = t["access"].isin(PRIVATE)
    return t


def toilet_counts(hex_ids, points):
    grouped = points.groupby("hex_id")
    out = pd.DataFrame(index=pd.Index(hex_ids, name="hex_id"))
    for column, flag in zip(OSM_TOILET_COLUMNS, ("is_public", "is_public_tagged", "is_private")):
        out[column] = out.index.map(grouped[flag].sum()).fillna(0).astype(int)
    return out


def build_features(hex_ids, layers, points):
    grid = hex_grid(hex_ids)
    parts = [counts(grid, layers["sports"], "sports"), areas(grid, layers["sports"], "sports"),
             counts(grid, layers["playground"], "playground"), counts(grid, layers["beach"], "beach"),
             nearest(grid, layers["beach"], "distance_nearest_beach_m"),
             nearest(grid, layers["sports"], "distance_nearest_sports_m"),
             nearest(grid, layers["playground"], "distance_nearest_playground_m"),
             toilet_counts(grid.hex_id.tolist(), points)]
    features = pd.concat(parts, axis=1)
    features.index.name = "hex_id"
    return features.loc[grid.hex_id].reset_index()
