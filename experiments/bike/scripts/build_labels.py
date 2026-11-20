"""Per-hex bike infrastructure length from the Overpass download, and the same from TfNSW for comparison.

Usage: python -I build_labels.py OVERPASS_DIR TFNSW_SHP
Writes experiments/bike/data/bike_labels.csv (study hexes only) and bike_lengths_all_hexes.csv
(every res-9 hex touched, used for the neighbour-ring features).
"""
import json
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import shapely

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hexgeo import BIKE_DATA, line_length_by_hex, study_hexes

TRACK = {"track", "opposite_track", "separate_track"}
LANE = {"lane", "opposite_lane", "buffered_lane"}
SIDE_KEYS = ["cycleway", "cycleway:both", "cycleway:left", "cycleway:right"]
OFFROAD = {"path", "footway", "pedestrian", "track", "bridleway"}
SKIP_HIGHWAY = {"construction", "proposed", "abandoned", "disused", "razed"}

# TfNSW `facility` -> our classes. Mixed traffic, parking lanes, shoulders and motor-only
# segments are signed routes on ordinary roads, not dedicated infrastructure.
TFNSW_CLASS = {
    "Bicycle Path": "separated", "Separated Path": "separated", "Shared Use Path": "shared_path",
    "Bicycle Lane": "painted", "Contra-flow Permitted": "painted",
    "Quietway": "quiet", "Shared Zone": "quiet",
}


def osm_class(tags):
    """separated | shared_path | painted | quiet | None. One class per way, best facility wins."""
    hw = tags.get("highway", "")
    if hw in SKIP_HIGHWAY:
        return None
    if hw == "cycleway":
        # Sydney maps most shared paths as cycleway + foot=designated + segregated=no.
        walkers = tags.get("foot") in ("designated", "yes") and tags.get("segregated") != "yes"
        return "shared_path" if walkers else "separated"
    if hw in OFFROAD and tags.get("bicycle") == "designated":
        return "shared_path"
    sides = {tags.get(k, "") for k in SIDE_KEYS}
    if sides & TRACK:
        return "separated"
    if sides & LANE:
        return "painted"
    if hw and (tags.get("bicycle") == "designated" or tags.get("bicycle_road") == "yes"):
        return "quiet"
    return None


def load_overpass(folder):
    rows = {}
    for path in sorted(folder.glob("bike_tile_*.json")):
        for el in json.loads(path.read_text())["elements"]:
            if el["type"] == "way" and "geometry" in el and len(el["geometry"]) > 1:
                rows[el["id"]] = el
    ways = pd.DataFrame({
        "osm_id": list(rows),
        "cls": [osm_class(e.get("tags", {})) for e in rows.values()],
        "geometry": [shapely.LineString([(p["lon"], p["lat"]) for p in e["geometry"]]) for e in rows.values()],
    })
    return ways


def per_hex(lengths, prefix):
    wide = lengths.pivot_table(index="hex_id", columns="group", values="length_m", aggfunc="sum", fill_value=0)
    for c in ["separated", "shared_path", "painted", "quiet"]:
        if c not in wide:
            wide[c] = 0.0
    wide = wide[["separated", "shared_path", "painted", "quiet"]].add_prefix(prefix).add_suffix("_m")
    wide[f"{prefix}len_m"] = wide[[f"{prefix}separated_m", f"{prefix}shared_path_m", f"{prefix}painted_m"]].sum(axis=1)
    return wide


def main(overpass_dir, tfnsw_shp):
    ways = load_overpass(overpass_dir)
    kept = ways[ways["cls"].notna()]
    print("OSM ways:", len(ways), "classified:", kept["cls"].value_counts().to_dict())
    osm = per_hex(line_length_by_hex(kept["geometry"].to_numpy(), kept["cls"].to_numpy()), "bike_")

    tf = gpd.read_file(tfnsw_shp).to_crs(4326)
    tf = tf[tf.geometry.notna()].explode(index_parts=False)
    tf["cls"] = tf["facility"].map(TFNSW_CLASS)
    tf = tf[tf["cls"].notna()]
    tfnsw = per_hex(line_length_by_hex(tf.geometry.to_numpy(), tf["cls"].to_numpy()), "tfnsw_")

    allhex = osm.join(tfnsw, how="outer").fillna(0.0)
    BIKE_DATA.mkdir(parents=True, exist_ok=True)
    allhex.round(1).rename_axis("hex_id").reset_index().to_csv(BIKE_DATA / "bike_lengths_all_hexes.csv", index=False)
    labels = allhex.reindex(study_hexes()).fillna(0.0).rename_axis("hex_id").reset_index()
    labels["has_bike"] = (labels["bike_len_m"] >= 20).astype(int)
    labels.round(1).to_csv(BIKE_DATA / "bike_labels.csv", index=False)
    s = labels
    print(f"study hexes {len(s)}; OSM bike_len km {s.bike_len_m.sum() / 1000:.0f} "
          f"(separated {s.bike_separated_m.sum() / 1000:.0f}, shared {s.bike_shared_path_m.sum() / 1000:.0f}, "
          f"painted {s.bike_painted_m.sum() / 1000:.0f}); hexes with >=20 m: {s.has_bike.sum()}; "
          f"TfNSW km {s.tfnsw_len_m.sum() / 1000:.0f}, hexes {(s.tfnsw_len_m >= 20).sum()}")


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]))
