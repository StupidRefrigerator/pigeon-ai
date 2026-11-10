"""Spot-check five known places: hex features plus the OSM features within 300 m and the nearest of each layer."""
import geopandas as gpd
import h3
import pandas as pd
from shapely.geometry import Point

from features import build, toilet_points
from hexsets import CRS, OUT, REPO, grid
from osm_layers import layers

PLACES = [  # (label, lat, lng, source of the coordinate)
    ("Ken Birdsey Park (planned_sites BL01)", -33.7000656, 150.8920516, "experiments/gov/planned_sites.csv"),
    ("Anthony Skarratt Reserve, Box Hill (TH01)", -33.6643108, 150.9072856, "experiments/gov/planned_sites.csv"),
    ("Bondi Beach", -33.89231, 151.27531, "OSM natural=beach 'Bondi Beach' representative point"),
    ("Centennial Park playground (Ian Potter Wild Play Garden)", -33.89772, 151.23939, "OSM leisure=playground"),
    ("Sydney Olympic Park (Accor Stadium)", -33.84711, 151.06338, "OSM leisure=stadium 'Accor Stadium'"),
]


def label(row):
    kind = next((row[c] for c in ("leisure", "natural", "amenity") if isinstance(row[c], str)), "?")
    return f"{row['name']} ({kind})" if isinstance(row["name"], str) else f"({kind})"


def main():
    L = layers()
    toilets = toilet_points(L["toilets"])
    study = pd.read_csv(f"{OUT}/new_features_study.csv").set_index("hex_id")
    growth = pd.read_csv(f"{OUT}/new_features_growth.csv").set_index("hex_id")
    lab = pd.read_csv(f"{REPO}/data/processed/sydney_extended_features.csv",
                      usecols=["hex_id", "toilet_count"]).set_index("hex_id").toilet_count
    rows = []
    for name, lat, lng, src in PLACES:
        hid = h3.latlng_to_cell(lat, lng, 9)
        where = "study" if hid in study.index else "growth" if hid in growth.index else "none"
        # Same code as the CSVs, run for this one hex; asserted identical when the hex is in a set.
        f = build(grid([hid]), L, toilets).iloc[0].drop("hex_id").to_dict()
        if where != "none":
            ref = (study if where == "study" else growth).loc[hid]
            assert all(abs(ref[k] - v) < 1e-6 for k, v in f.items()), hid
        p = gpd.GeoSeries([Point(lng, lat)], crs=4326).to_crs(CRS).iloc[0]
        row = {"place": name, "lat": lat, "lng": lng, "coord_source": src, "hex_id": hid, "set": where,
               "toilet_count_official": lab.get(hid), **f}
        near = []
        for k in ("sports", "playground", "beach", "toilets"):
            d = L[k].geometry.distance(p)
            near += [f"{k}:{label(r)}" for _, r in L[k][d <= 300].iterrows()]
            row[f"nearest_{k}"] = f"{label(L[k].loc[d.idxmin()])} @ {d.min():.0f} m"
        row["osm_within_300m"] = "; ".join(near)
        rows.append(row)
    df = pd.DataFrame(rows)
    df.to_csv(f"{OUT}/spot_checks.csv", index=False)
    pd.set_option("display.width", 250, "display.max_colwidth", 200)
    print(df.T.to_string())


if __name__ == "__main__":
    main()
