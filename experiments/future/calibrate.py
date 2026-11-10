"""Shops / food / bus-stop densities per hectare of zone role, measured on real Sydney suburbs.

Output: calibration_by_suburb.csv (one row per suburb x role) and calibration.csv (scenario densities).
"""
import sys

import geopandas as gpd
import numpy as np
import pandas as pd

sys.path.insert(0, "/tmp/pigeon-eval/future")
from fetch import ABS_SAL, ZONING, arcgis_envelope, overpass
from zones import CRS, poi_query, pois_from_overpass, zoning_roles

OUT = "/tmp/pigeon-eval/future"
GROWTH = ["Oran Park", "Gregory Hills", "Marsden Park", "Edmondson Park", "Leppington",
          "Rouse Hill", "Schofields", "Box Hill (NSW)", "Jordan Springs", "Gledswood Hills"]
ESTABLISHED = ["Parramatta", "Penrith", "Liverpool", "Campbelltown (NSW)", "Blacktown",
               "Castle Hill (NSW)", "Bankstown", "Hornsby", "Chatswood", "Burwood (NSW)"]
# Infrastructure (SP2) is left out: its bus stops sit on road reserves, and the planned area has 1,700 ha
# of SP2 airport land that would otherwise inherit a road-reserve bus density.
ROLES = ["centre", "enterprise", "residential", "low_residential", "park", "rural"]


def suburb_polygons():
    names = ",".join(f"'{n}'" for n in GROWTH + ESTABLISHED)
    sal = arcgis_envelope(ABS_SAL, (150.4, -34.3, 151.4, -33.4), out_fields="sal_name_2021,state_code_2021",
                          where=f"sal_name_2021 IN ({names}) AND state_code_2021='1'", tag="sal", order_by="objectid")
    assert set(sal.sal_name_2021) == set(GROWTH + ESTABLISHED), set(GROWTH + ESTABLISHED) - set(sal.sal_name_2021)
    return sal.to_crs(CRS)


def measure(name, poly_metric, poly_ll):
    bbox = tuple(poly_ll.bounds)
    zoning = zoning_roles(arcgis_envelope(ZONING, bbox, out_fields="EPI_NAME,SYM_CODE,LAY_CLASS", tag="zoning_cal"))
    zoning["geometry"] = zoning.intersection(poly_metric)
    zoning = zoning[~zoning.is_empty]
    pois = pois_from_overpass(overpass(poi_query(bbox), tag="cal"))
    pois = pois[pois.within(poly_metric)]
    rows = []
    for role, group in zoning.groupby("role"):
        shape = group.geometry.union_all()
        inside = pois[pois.within(shape)]
        rows.append(dict(suburb=name, role=role, ha=shape.area / 1e4,
                         shops=int(inside.is_shop.sum()), food=int(inside.is_food.sum()),
                         bus=int(inside.is_bus_stop.sum())))
    return rows


def scenario_densities(t, exclude=()):
    """Per-ha densities by role for low/mid/high scenarios. Slivers < 2 ha are ignored.

    Centre shops/food: low = 25th pct of growth suburbs, mid = growth median, high = established median.
    Other roles: low = 0, mid = high = pooled growth-suburb rate. Bus: low = 0 (the 'no buses'
    scenario), mid = high = pooled growth-suburb rate for the role.
    """
    usable = t[(t.ha >= 2) & ~t.suburb.isin(exclude)]
    centre = usable[usable.role == "centre"]
    out = []
    for c in ("shops", "food"):
        g = centre[centre.group == "growth"][f"{c}_per_ha"]
        e = centre[centre.group == "established"][f"{c}_per_ha"]
        out.append(dict(variable=c, role="centre", low=g.quantile(0.25), mid=g.median(), high=e.median()))
    growth = usable[usable.group == "growth"]
    for role in ROLES:
        r = growth[growth.role == role]
        for c in ("shops", "food", "bus"):
            if c != "bus" and role == "centre":
                continue
            rate = r[c].sum() / r.ha.sum() if len(r) else 0.0
            out.append(dict(variable=c, role=role, low=0.0, mid=rate, high=rate))
    return pd.DataFrame(out)


def main():
    sal = suburb_polygons()
    sal_ll = sal.to_crs(4326)
    rows = []
    for i in range(len(sal)):
        name = sal.sal_name_2021.iloc[i]
        rows += measure(name, sal.geometry.iloc[i], sal_ll.geometry.iloc[i])
        print("measured", name, flush=True)
    t = pd.DataFrame(rows)
    t["group"] = np.where(t.suburb.isin(GROWTH), "growth", "established")
    for c in ("shops", "food", "bus"):
        t[f"{c}_per_ha"] = t[c] / t.ha
    t.to_csv(f"{OUT}/calibration_by_suburb.csv", index=False)

    cal = scenario_densities(t)
    cal.to_csv(f"{OUT}/calibration.csv", index=False)
    print(t[t.role == "centre"].round(2).to_string())
    print(cal.round(3).to_string())


if __name__ == "__main__":
    main()
