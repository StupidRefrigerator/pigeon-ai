"""Per-hex feature functions, mirroring src/pigeon_ai/osm.py conventions (EPSG:7856, centroid buffers)."""
import geopandas as gpd
import h3
import pandas as pd
import shapely
from shapely import area, buffer, intersection

RADII = (250, 500, 1000)


def counts(grid, layer, prefix):
    """<prefix>_inside: representative point within hex; <prefix>_<r>m: points intersecting a centroid circle."""
    pts = gpd.GeoDataFrame(geometry=layer["point"].values, crs=grid.crs)
    out = pd.DataFrame({"hex_id": grid.hex_id})
    inside = gpd.sjoin(pts, grid[["hex_id", "geometry"]], how="inner", predicate="within")
    out[f"{prefix}_inside"] = out.hex_id.map(inside.groupby("hex_id").size()).fillna(0).astype(int).values
    centres = grid.geometry.centroid
    for r in RADII:
        zones = gpd.GeoDataFrame({"hex_id": grid.hex_id}, geometry=centres.buffer(r), crs=grid.crs)
        m = gpd.sjoin(zones, pts, how="left", predicate="intersects")
        out[f"{prefix}_{r}m"] = out.hex_id.map(m.groupby("hex_id")["index_right"].count()).fillna(0).astype(int).values
    return out.set_index("hex_id")


def polygon_union(layer):
    polys = layer[layer.geom_type.isin(["Polygon", "MultiPolygon"])].geometry
    return polys.union_all()


def areas(grid, union, prefix, radii=(500,)):
    out = pd.DataFrame(index=grid.hex_id.values)
    out[f"{prefix}_area_inside_m2"] = area(intersection(grid.geometry.array, union))
    centres = grid.geometry.centroid
    for r in radii:
        # Same as park areas: shapely.buffer default (8 segments/quadrant).
        out[f"{prefix}_area_{r}m_m2"] = area(intersection(buffer(centres.array, r), union))
    return out


def nearest(grid, layer, col):
    """Distance from hex centroid to nearest feature geometry (polygon edge/inside = 0), as for parks."""
    pts = gpd.GeoDataFrame({"hex_id": grid.hex_id}, geometry=grid.geometry.centroid, crs=grid.crs)
    j = gpd.sjoin_nearest(pts, layer[["geometry"]], how="left", distance_col="d")
    return j.groupby("hex_id")["d"].min().rename(col)


PUBLIC = {"yes", "permissive", "public"}
PRIVATE = {"customers", "private", "no"}


def toilet_points(toilets):
    t = toilets.copy()
    ll = t["point"].to_crs(4326)
    t["lat"], t["lng"] = ll.y.values, ll.x.values
    t["hex_id"] = [h3.latlng_to_cell(a, b, 9) for a, b in zip(t.lat, t.lng)]
    acc = t["access"]
    t["is_public"] = acc.isna() | acc.isin(PUBLIC)
    t["is_public_tagged"] = acc.isin(PUBLIC)
    t["is_private"] = acc.isin(PRIVATE)
    return t


def toilet_counts(hex_ids, t):
    g = t.groupby("hex_id")
    out = pd.DataFrame(index=pd.Index(hex_ids, name="hex_id"))
    for col, flag in (("osm_toilets_public", "is_public"), ("osm_toilets_public_tagged", "is_public_tagged"),
                      ("osm_toilets_private", "is_private")):
        out[col] = out.index.map(g[flag].sum()).fillna(0).astype(int)
    return out


def build(grid, L, toilets):
    parts = [counts(grid, L["sports"], "sports"),
             areas(grid, polygon_union(L["sports"]), "sports"),
             counts(grid, L["playground"], "playground"),
             counts(grid, L["beach"], "beach"),
             nearest(grid, L["beach"], "distance_nearest_beach_m"),
             nearest(grid, L["sports"], "distance_nearest_sports_m"),
             nearest(grid, L["playground"], "distance_nearest_playground_m"),
             toilet_counts(grid.hex_id.tolist(), toilets)]
    df = pd.concat(parts, axis=1)
    df.index.name = "hex_id"
    return df.loc[grid.hex_id].reset_index()
