"""Zone code -> planning role, plus OSM POI loading with the repo's category flags."""
import geopandas as gpd
import pandas as pd
from shapely.geometry import Point

CRS = "EPSG:7856"

ROLE = {
    **{c: "centre" for c in ["B1", "B2", "B3", "B4", "E1", "E2", "MU1", "MU"]},
    **{c: "enterprise" for c in ["B5", "B6", "B7", "E3", "E4", "E5", "IN1", "IN2", "IN3", "ENT"]},
    **{c: "residential" for c in ["R1", "R2", "R3", "R4"]},
    **{c: "low_residential" for c in ["R5", "C4", "RU6", "RU5"]},
    **{c: "park" for c in ["RE1", "PRR", "ENZ"]},
    "RE2": "private_recreation",
    **{c: "infrastructure" for c in ["SP1", "SP2", "SP3", "SP4", "SP5"]},
    **{c: "rural" for c in ["RU1", "RU2", "RU3", "RU4", "AGB"]},
    **{c: "conservation" for c in ["C1", "C2", "C3", "W1", "W2", "W3", "W4"]},
}


def role_of(code):
    return ROLE.get(code, "other")


def zoning_roles(zoning):
    """Dissolve zoning to one (multi)polygon per role, in metric CRS."""
    z = zoning.to_crs(CRS).copy()
    z["geometry"] = z.geometry.make_valid()
    z["role"] = z["SYM_CODE"].map(role_of)
    return z


def pois_from_overpass(payload):
    rows = []
    for e in payload["elements"]:
        tags = e.get("tags", {})
        c = e.get("center", e)
        if "lat" not in c:
            continue
        rows.append(dict(
            geometry=Point(c["lon"], c["lat"]),
            is_shop=("shop" in tags) and tags["shop"] != "vacant",
            is_food=tags.get("amenity") in ("cafe", "restaurant"),
            is_bus_stop=tags.get("highway") == "bus_stop",
            is_train_station=tags.get("railway") == "station",
        ))
    return gpd.GeoDataFrame(pd.DataFrame(rows), geometry="geometry", crs=4326).to_crs(CRS)


def poi_query(bbox):
    s, w, n, e = bbox[1], bbox[0], bbox[3], bbox[2]
    b = f"({s},{w},{n},{e})"
    return (f'[out:json][timeout:180];(nwr["shop"]{b};nwr["amenity"~"^(cafe|restaurant)$"]{b};'
            f'nwr["highway"="bus_stop"]{b};);out center tags;')
