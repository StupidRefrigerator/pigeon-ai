"""Projected v1 features for a planned area, built from zoning, planned stations and projections.

Data shape: a *surface* is a GeoDataFrame of polygons (EPSG:7856), each carrying per-m2 densities
(pop_m2, shop_m2, food_m2, bus_m2). Every count/population feature is the expected value of the
repo's definition: sum over surface pieces of density x area(piece & zone), where zone is the hex
(inside) or a 250/500 m circle around the hex centroid (osm.py / population.py). Stations are points
and parks are polygons, handled exactly as osm.py does.
"""
import sys

import geopandas as gpd
import h3
import numpy as np
import pandas as pd
import shapely
from shapely.geometry import Polygon, box

sys.path.insert(0, "/tmp/pigeon-eval/future")
from fetch import ABS_SA2, ZONING, arcgis_envelope
from zones import CRS, zoning_roles

DPHI = "/tmp/pigeon-eval/future/downloads/dphi_2024_sa2.xlsx"
V1 = ["population_est", "shop_inside", "shop_250m", "shop_500m", "food_inside", "food_250m", "food_500m",
      "bus_stop_inside", "bus_stop_250m", "bus_stop_500m", "train_station_inside", "train_station_250m",
      "train_station_500m", "park_area_inside_m2", "park_area_250m_m2", "park_area_500m_m2",
      "distance_nearest_park_m", "population_250m", "population_500m"]

# Relative residents per hectare by role when spreading a projection unit's total over zoned land.
POP_WEIGHT = {"centre": 1.0, "residential": 1.0, "low_residential": 0.1, "rural": 0.01}
AERO_MU_CORE_M = 600       # Bradfield site ~114 ha ~ a 600 m circle: retail core of the Aerotropolis MU zone.
AERO_MU_HOUSING_M = 1000   # Precinct Plan LU7: MU housing within 1 km walk of a Metro station.


def hex_grid(bbox):
    """Res-9 cells whose centroid lies in bbox (lon/lat)."""
    minx, miny, maxx, maxy = bbox
    poly = h3.LatLngPoly([(miny, minx), (miny, maxx), (maxy, maxx), (maxy, minx)])
    cells = sorted(h3.polygon_to_cells(poly, 9))
    geoms = [Polygon([(lng, lat) for lat, lng in h3.cell_to_boundary(c)]) for c in cells]
    return gpd.GeoDataFrame({"hex_id": cells}, geometry=geoms, crs=4326).to_crs(CRS)


def hexes_from_ids(ids):
    geoms = [Polygon([(lng, lat) for lat, lng in h3.cell_to_boundary(c)]) for c in ids]
    return gpd.GeoDataFrame({"hex_id": list(ids)}, geometry=geoms, crs=4326).to_crs(CRS)


def load_zoning(bbox, tag):
    z = zoning_roles(arcgis_envelope(ZONING, bbox, out_fields="EPI_NAME,LGA_NAME,SYM_CODE,LAY_CLASS,LABEL", tag=tag))
    return z[z.geometry.notna() & ~z.is_empty]


def split_aero_mu(zoning, metro):
    """Aerotropolis 'MU' zone: centre within 600 m of a Metro station, 'mu_fringe' beyond.
    Also flags MU land beyond 1 km of a station as non-residential (LU7)."""
    zoning = zoning.copy()
    zoning["housing_ok"] = True
    mu = zoning[zoning.SYM_CODE == "MU"]
    if mu.empty or metro.empty:
        return zoning
    core = metro.buffer(AERO_MU_CORE_M).union_all()
    housing = metro.buffer(AERO_MU_HOUSING_M).union_all()
    pieces = []
    for _, row in mu.iterrows():
        for geom, role in ((row.geometry.intersection(core), "centre"),
                           (row.geometry.difference(core), "mu_fringe")):
            for g, ok in ((geom.intersection(housing), True), (geom.difference(housing), False)):
                if not g.is_empty and g.area > 1:
                    pieces.append({**row.drop("geometry").to_dict(), "role": role, "housing_ok": ok, "geometry": g})
    return pd.concat([zoning[zoning.SYM_CODE != "MU"], gpd.GeoDataFrame(pieces, crs=CRS)], ignore_index=True)


def projection_units(bbox, year):
    """2021 SA2 polygons with their DPHI 2024 projection-unit total for `year`."""
    sa2 = arcgis_envelope(ABS_SA2, bbox, out_fields="sa2_code_2021,sa2_name_2021", tag="sa2", order_by="objectid").to_crs(CRS)
    totals = pd.read_excel(DPHI, "Total population", header=6)
    collapsed = pd.read_excel(DPHI, "Collapsed SA2s", header=6)
    unit_of = dict(zip(collapsed.SA2_NAME_2021.str.strip(), collapsed["Collapsed SA2"].str.strip()))
    sa2["unit"] = sa2.sa2_name_2021.map(lambda n: unit_of.get(n, n))
    total = dict(zip(totals.SA2.str.strip(), totals[year]))
    sa2["unit_total"] = sa2.unit.map(total)
    return sa2.dissolve("unit", aggfunc={"unit_total": "first"}).reset_index()


def density_table(cal, level):
    """role -> per-ha density for shops/food/bus at a scenario level ('low'/'mid'/'high')."""
    d = {}
    for _, r in cal.iterrows():
        d.setdefault(r.role, {})[r.variable] = r[level]
    d["mu_fringe"] = {"shops": d["enterprise"]["shops"], "food": d["enterprise"]["food"],
                      "bus": d["residential"]["bus"]}
    return d


def build_surface(zoning, units, shops_food, bus, override=None):
    """Cut zoning by projection unit and attach densities.

    shops_food, bus: role -> {'shops','food','bus'} per-ha tables (from density_table).
    override: optional (polygon, residents). Land inside the polygon takes `residents` spread by the
    same role weights; land outside keeps its DPHI-unit share (so the unit total is not conserved).
    """
    pieces = gpd.overlay(zoning[["role", "SYM_CODE", "housing_ok", "geometry"]],
                         units[["unit", "unit_total", "geometry"]], how="intersection", keep_geom_type=True)
    pieces["in_override"] = False
    if override is not None:
        poly = override[0]
        a, b = pieces.copy(), pieces.copy()
        a["geometry"], b["geometry"] = pieces.intersection(poly), pieces.difference(poly)
        a["in_override"] = True
        pieces = pd.concat([a, b], ignore_index=True)
        pieces = pieces[~pieces.is_empty & (pieces.area > 1)].copy()
    pieces["w"] = pieces.role.map(POP_WEIGHT).fillna(0.0) * pieces.housing_ok.astype(float)
    pieces["warea"] = pieces.w * pieces.area
    per_unit = pieces.groupby("unit").warea.sum()
    pieces["pop_m2"] = (pieces.unit_total * pieces.w / pieces.unit.map(per_unit)).fillna(0.0)
    if override is not None:
        sel = pieces.in_override
        pieces.loc[sel, "pop_m2"] = override[1] * pieces.w[sel] / pieces.warea[sel].sum()
    for col, table, key in (("shop_m2", shops_food, "shops"), ("food_m2", shops_food, "food"), ("bus_m2", bus, "bus")):
        pieces[col] = pieces.role.map(lambda r: table.get(r, {}).get(key, 0.0)) / 1e4
    return pieces


def _weighted_sum(zones, surface, cols):
    hits = gpd.overlay(zones[["hex_id", "geometry"]], surface[cols + ["geometry"]], how="intersection",
                       keep_geom_type=True)
    a = hits.area
    out = pd.DataFrame({c: hits[c] * a for c in cols})
    out["hex_id"] = hits.hex_id.values
    return out.groupby("hex_id").sum()


def features(hexes, surface, stations, parks):
    """The 19 v1 columns, using the repo's definitions (osm.py, population.py)."""
    f = pd.DataFrame(index=pd.Index(hexes.hex_id, name="hex_id"))
    cols = ["pop_m2", "shop_m2", "food_m2", "bus_m2"]
    names = {"pop_m2": "population", "shop_m2": "shop", "food_m2": "food", "bus_m2": "bus_stop"}
    centres = hexes.geometry.centroid
    inside = _weighted_sum(hexes, surface, cols).reindex(f.index).fillna(0)
    f["population_est"] = inside.pop_m2
    for c in ("shop_m2", "food_m2", "bus_m2"):
        f[f"{names[c]}_inside"] = inside[c]
    for radius in (250, 500):
        zones = gpd.GeoDataFrame({"hex_id": hexes.hex_id.values}, geometry=centres.buffer(radius).values, crs=CRS)
        ring = _weighted_sum(zones, surface, cols).reindex(f.index).fillna(0)
        f[f"population_{radius}m"] = ring.pop_m2
        for c in ("shop_m2", "food_m2", "bus_m2"):
            f[f"{names[c]}_{radius}m"] = ring[c]
    # Stations: points within the hex; points intersecting 250/500 m circles (16 segments, as osm.py).
    pts = stations.geometry
    f["train_station_inside"] = [int(pts.within(g).sum()) for g in hexes.geometry]
    for radius in (250, 500):
        f[f"train_station_{radius}m"] = [int(pts.intersects(c.buffer(radius)).sum()) for c in centres]
    # Parks: union area inside the hex and in 8-segment circles; nearest park distance from centroid.
    union = parks.union_all()
    f["park_area_inside_m2"] = shapely.area(shapely.intersection(hexes.geometry.array, union))
    for radius in (250, 500):
        f[f"park_area_{radius}m_m2"] = shapely.area(shapely.intersection(shapely.buffer(centres.array, radius), union))
    f["distance_nearest_park_m"] = [union.distance(c) for c in centres]
    return f[V1]


def station_points(payload):
    """Rail stations (railway=station) plus Metro stations under construction (construction:railway=station)."""
    rows = []
    for e in payload["elements"]:
        t = e.get("tags", {})
        c = e.get("center", e)
        if "lat" in c and "station" in (t.get("railway"), t.get("construction:railway")):
            rows.append(dict(osm_id=e["id"], name=t.get("name"), lat=c["lat"], lon=c["lon"],
                             planned=t.get("construction:railway") == "station"))
    df = pd.DataFrame(rows)
    return gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df.lon, df.lat), crs=4326).to_crs(CRS)
