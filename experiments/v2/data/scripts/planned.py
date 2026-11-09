"""Planned-scenario features for the future areas (Aerotropolis, Leppington).

Undeveloped RE1 (Public Recreation) land near the future hexes is filled with sports and playground
features at the rates measured on RE1 land in 10 established Sydney suburbs. Counts become expected
values: density_per_m2 x area(undeveloped RE1 piece & zone), added to today's OSM counts.
Writes new_features_future_planned.csv and re1_calibration.csv.
"""
import glob
import json

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely import area, buffer, intersection

from features import RADII
from hexsets import CRS, OUT, grid, hex_ids
from osm_layers import layers

Z = f"{OUT}/downloads/zoning"
ESTABLISHED = ["Parramatta", "Penrith", "Liverpool", "Campbelltown (NSW)", "Blacktown",
               "Castle Hill (NSW)", "Bankstown", "Hornsby", "Chatswood", "Burwood (NSW)"]
MIN_EXPECTED_FOR_DISTANCE = 0.5  # an undeveloped RE1 parcel counts as "has a feature" for distance if E[count] >= 0.5


def read_zoning(pattern):
    z = pd.concat([gpd.read_file(f) for f in sorted(glob.glob(f"{Z}/{pattern}"))], ignore_index=True)
    z = gpd.GeoDataFrame(z, geometry="geometry", crs=4326).to_crs(CRS)
    z["geometry"] = z.geometry.make_valid()
    return z[z.geometry.notna() & ~z.is_empty]


def parcels(z, codes):
    """Dissolve zone polygons with SYM_CODE in codes into contiguous parcels."""
    u = z[z.SYM_CODE.isin(codes)].geometry.union_all()
    p = gpd.GeoDataFrame(geometry=[u], crs=CRS).explode(index_parts=False).reset_index(drop=True)
    return p[p.geom_type == "Polygon"]


def calibrate(L):
    sal = gpd.read_file(f"{Z}/arcgis_sal_d85ccc8971ed.geojson").to_crs(CRS)
    zcal = read_zoning("arcgis_zoning_cal_*.geojson")
    re1 = zcal[zcal.SYM_CODE == "RE1"].geometry.union_all()
    pitch = L["sports"][(L["sports"].leisure == "pitch") & L["sports"].geom_type.isin(["Polygon", "MultiPolygon"])].geometry.union_all()
    sports = L["sports"][L["sports"].geom_type.isin(["Polygon", "MultiPolygon"])].geometry.union_all()
    rows = []
    for name in ESTABLISHED:
        poly = sal[sal.sal_name_2021 == name].geometry.union_all()
        r = re1.intersection(poly)
        rows.append(dict(
            suburb=name, re1_ha=r.area / 1e4,
            pitch_ha=r.intersection(pitch).area / 1e4, sports_ha=r.intersection(sports).area / 1e4,
            sports_n=int(L["sports"]["point"].within(r).sum()),
            playground_n=int(L["playground"]["point"].within(r).sum()),
            playground_n_suburb=int(L["playground"]["point"].within(poly).sum()),
            sports_n_suburb=int(L["sports"]["point"].within(poly).sum())))
    t = pd.DataFrame(rows)
    t["pitch_share"] = t.pitch_ha / t.re1_ha
    t["sports_share"] = t.sports_ha / t.re1_ha
    t["sports_per_ha"] = t.sports_n / t.re1_ha
    t["playground_per_ha"] = t.playground_n / t.re1_ha
    tot = t[["re1_ha", "pitch_ha", "sports_ha", "sports_n", "playground_n"]].sum()
    pooled = dict(pitch_share=tot.pitch_ha / tot.re1_ha, sports_share=tot.sports_ha / tot.re1_ha,
                  sports_per_ha=tot.sports_n / tot.re1_ha, playground_per_ha=tot.playground_n / tot.re1_ha,
                  re1_ha=tot.re1_ha)
    t = pd.concat([t, pd.DataFrame([{"suburb": "POOLED (ratio of sums)", **tot.to_dict(), **pooled}])], ignore_index=True)
    t.to_csv(f"{OUT}/re1_calibration.csv", index=False)
    return pooled, t


def undeveloped(p, L):
    """RE1 parcels with no OSM sports or playground feature (rep point) inside: treated as not yet built."""
    pts = pd.concat([L["sports"]["point"], L["playground"]["point"]])
    pts = gpd.GeoDataFrame(geometry=pts.values, crs=CRS)
    hit = gpd.sjoin(p, pts, how="inner", predicate="contains").index.unique()
    p = p.copy()
    p["developed"] = p.index.isin(hit)
    return p


def planned(base, g, und, rate, scenario):
    """Add expected RE1-derived features to current OSM features `base` (indexed by hex_id)."""
    df = base.copy()
    U = und.geometry.union_all()
    centres = g.geometry.centroid.array
    sizes = {"inside": area(intersection(g.geometry.array, U))}
    for r in RADII:
        sizes[f"{r}m"] = area(intersection(buffer(centres, r, quad_segs=16), U))
    sizes["500m_area"] = area(intersection(buffer(centres, 500), U))
    for prefix, per_ha in (("sports", rate["sports_per_ha"]), ("playground", rate["playground_per_ha"])):
        for k in ["inside"] + [f"{r}m" for r in RADII]:
            df[f"{prefix}_{k}"] = df[f"{prefix}_{k}"].to_numpy() + per_ha * sizes[k] / 1e4
    df["sports_area_inside_m2"] += rate["sports_share"] * sizes["inside"]
    df["sports_area_500m_m2"] += rate["sports_share"] * sizes["500m_area"]
    pts = gpd.GeoDataFrame({"hex_id": g.hex_id}, geometry=g.geometry.centroid, crs=CRS)
    ha = und.geometry.area / 1e4
    for prefix, per_ha, col in (("sports", rate["sports_per_ha"], "distance_nearest_sports_m"),
                                ("playground", rate["playground_per_ha"], "distance_nearest_playground_m")):
        cand = und[ha * per_ha >= MIN_EXPECTED_FOR_DISTANCE]
        if len(cand):
            d = gpd.sjoin_nearest(pts, cand[["geometry"]], distance_col="d").groupby("hex_id")["d"].min()
            df[col] = np.minimum(df[col].to_numpy(), d.reindex(df.index).fillna(np.inf).to_numpy())
    df.insert(0, "scenario", scenario)
    return df


def main():
    L = layers()
    rate, table = calibrate(L)
    print(table.round(3).to_string())
    _, _, future = hex_ids()
    g = grid(future.hex_id.tolist())
    current = pd.read_csv(f"{OUT}/new_features_future.csv").set_index("hex_id").loc[g.hex_id]
    base = current.drop(columns=["area"])
    zf = read_zoning("arcgis_zoning_[al]e*.geojson")  # aero + leppington
    reach = g.geometry.centroid.buffer(max(RADII) + 50).union_all()
    zf = zf[zf.intersects(reach)]
    out, info = [], {}
    sc = base.copy(); sc.insert(0, "scenario", "current_osm"); out.append(sc)
    for scenario, codes in (("planned_re1", ["RE1"]), ("planned_re1_enz", ["RE1", "ENZ"])):
        p = undeveloped(parcels(zf, codes), L)
        und = p[~p.developed]
        info[scenario] = dict(parcels=int(len(p)), developed=int(p.developed.sum()),
                              undeveloped_ha=float(und.area.sum() / 1e4), developed_ha=float(p[p.developed].area.sum() / 1e4))
        out.append(planned(base, g, und, rate, scenario))
    res = pd.concat(out).reset_index()
    res.insert(2, "area", np.tile(future.area.values, 3))
    res.to_csv(f"{OUT}/new_features_future_planned.csv", index=False)
    summ = res.groupby(["scenario", "area"])[["sports_500m", "sports_area_500m_m2", "playground_500m",
                                               "distance_nearest_sports_m", "distance_nearest_playground_m"]].mean()
    print(summ.round(2).to_string())
    json.dump({"rates": rate, "re1": info, "summary": summ.round(3).reset_index().to_dict("records")},
              open(f"{OUT}/planned_checks.json", "w"), indent=1)
    print(json.dumps(info, indent=1))


if __name__ == "__main__":
    main()
