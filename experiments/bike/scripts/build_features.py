"""Bike-relevant hex features from the PBF extract, the DEM tiles and the bike label's neighbours.

Usage: python -I build_features.py EXTRACT_DIR DEM_DIR
Writes experiments/bike/data/bike_features.csv (16,228 study hexes).
Columns prefixed `ring_` are built from the bike label around the hex and are leak tests, not inputs
for the clean models. One res-9 ring is about 300 m between centres, so k=2 is about 600 m and k=3 about 900 m.
"""
import sys
from pathlib import Path

import h3
import matplotlib.image as mpimg
import numpy as np
import pandas as pd
import shapely
from sklearn.neighbors import KDTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_labels import osm_class
from hexgeo import BIKE_DATA, TO_MGA, count_points_by_hex, disk_sum, line_length_by_hex, study_hexes

CBD = (-33.8731, 151.2065)  # Sydney Town Hall
ROAD_GROUPS = {
    "major": {"motorway", "trunk", "primary", "motorway_link", "trunk_link", "primary_link"},
    "mid": {"secondary", "tertiary", "secondary_link", "tertiary_link"},
    "local": {"residential", "unclassified", "living_street"},
    "service": {"service"},
    "path": {"footway", "path", "pedestrian", "steps", "bridleway", "track"},
}
ZOOM = 12


def road_group(hw):
    return next((g for g, s in ROAD_GROUPS.items() if hw in s), None)


def dem_sampler(folder):
    tiles = {}
    for path in folder.glob(f"{ZOOM}_*_*.png"):
        _, x, y = path.stem.split("_")
        rgb = np.round(mpimg.imread(path)[:, :, :3] * 255)
        tiles[(int(x), int(y))] = rgb[:, :, 0] * 256 + rgb[:, :, 1] + rgb[:, :, 2] / 256 - 32768

    def sample(lat, lon):
        n = 2 ** ZOOM * 256
        px = (lon + 180) / 360 * n
        py = (1 - np.arcsinh(np.tan(np.radians(lat))) / np.pi) / 2 * n
        tx, ty = int(px // 256), int(py // 256)
        return max(float(tiles[(tx, ty)][int(py % 256), int(px % 256)]), 0.0)  # tiles carry bathymetry
    return sample


def terrain(hexes, sample):
    cache = {}

    def elev(h):
        if h not in cache:
            cache[h] = sample(*h3.cell_to_latlng(h))
        return cache[h]

    rows = []
    for h in hexes:
        z = elev(h)
        slopes = [abs(elev(n) - z) / h3.great_circle_distance(h3.cell_to_latlng(h), h3.cell_to_latlng(n), unit="m")
                  for n in h3.grid_ring(h, 1)]
        disk = [elev(n) for n in h3.grid_disk(h, 2)]
        rows.append((z, 100 * np.mean(slopes), 100 * np.max(slopes), max(disk) - min(disk)))
    return pd.DataFrame(rows, columns=["elevation_m", "slope_mean_pct", "slope_max_pct", "relief_600m_m"])


def nearest_m(hexes, lon, lat):
    tree = KDTree(np.column_stack(TO_MGA.transform(lon, lat)))
    centres = np.array([h3.cell_to_latlng(h) for h in hexes])
    d, _ = tree.query(np.column_stack(TO_MGA.transform(centres[:, 1], centres[:, 0])), k=1)
    return d[:, 0]


def main(extract_dir, dem_dir):
    hexes = study_hexes()
    out = pd.DataFrame({"hex_id": hexes})

    ways = pd.read_csv(extract_dir / "ways.csv.gz", dtype=str, keep_default_na=False)

    # Eval only, never an input: cycleways OSM marks as proposed or under construction.
    planned = ways[((ways["highway"] == "construction") & (ways["construction"] == "cycleway"))
                   | ((ways["highway"] == "proposed") & (ways["proposed"] == "cycleway"))
                   | ways["proposed:highway"].eq("cycleway") | ways["construction:highway"].eq("cycleway")]
    pl = line_length_by_hex(shapely.from_wkt(planned["wkt"].to_numpy())).set_index("hex_id")["length_m"].to_dict()
    out["eval_planned_cycleway_m"] = [pl.get(h, 0.0) for h in hexes]
    print(f"planned/under-construction cycleway ways: {len(planned)}, "
          f"study hexes with >=20 m: {(out['eval_planned_cycleway_m'] >= 20).sum()}")

    ways["group"] = ways["highway"].map(road_group)
    # Paths that carry the bike label are not counted as paths, so path length cannot copy the label.
    is_bike = np.array([osm_class(t) is not None for t in ways.to_dict("records")])
    ways = ways[ways["group"].notna() & ~(is_bike & (ways["group"] == "path"))]
    lengths = line_length_by_hex(shapely.from_wkt(ways["wkt"].to_numpy()), ways["group"].to_numpy())
    wide = lengths.pivot_table(index="hex_id", columns="group", values="length_m", aggfunc="sum", fill_value=0)
    wide["drivable"] = wide[["major", "mid", "local"]].sum(axis=1)
    for g in ["major", "mid", "local", "service", "path", "drivable"]:
        values = wide[g].to_dict()
        out[f"road_{g}_m"] = [values.get(h, 0.0) for h in hexes]
        if g in ("major", "mid", "drivable", "path"):
            out[f"road_{g}_600m_m"] = disk_sum(values, hexes, 2)

    junctions = pd.read_csv(extract_dir / "junctions.csv.gz")
    jc = count_points_by_hex(junctions["lon"], junctions["lat"]).to_dict()
    out["junctions_inside"] = [jc.get(h, 0) for h in hexes]
    out["junctions_600m"] = disk_sum(jc, hexes, 2)

    pois = pd.read_csv(extract_dir / "pois.csv.gz")
    for kind in ["school", "university"]:
        p = pois[pois["kind"] == kind]
        counts = count_points_by_hex(p["lon"], p["lat"]).to_dict()
        out[f"{kind}_600m"] = disk_sum(counts, hexes, 2)
        out[f"{kind}_900m"] = disk_sum(counts, hexes, 3)
        out[f"distance_nearest_{kind}_m"] = nearest_m(hexes, p["lon"].to_numpy(), p["lat"].to_numpy())
    st = pois[pois["kind"] == "station"]
    out["distance_nearest_station_m"] = nearest_m(hexes, st["lon"].to_numpy(), st["lat"].to_numpy())
    out["distance_cbd_km"] = [h3.great_circle_distance(h3.cell_to_latlng(h), CBD, unit="km") for h in hexes]

    out = pd.concat([out, terrain(hexes, dem_sampler(dem_dir))], axis=1)

    # Leak tests: bike length in the rings around the hex (self excluded) and in the disk (self included).
    bike = pd.read_csv(BIKE_DATA / "bike_lengths_all_hexes.csv").set_index("hex_id")["bike_len_m"].to_dict()
    out["ring_bike_300m_m"] = disk_sum(bike, hexes, 1, include_self=False)
    out["ring_bike_600m_m"] = disk_sum(bike, hexes, 2, include_self=False)
    out["ring_bike_900m_m"] = disk_sum(bike, hexes, 3, include_self=False)
    out["disk_bike_600m_m"] = disk_sum(bike, hexes, 2, include_self=True)

    out.round(3).to_csv(BIKE_DATA / "bike_features.csv", index=False)
    print(out.describe().T[["mean", "min", "max"]].to_string())


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]))
