#!/usr/bin/env python3
"""Build the water fountain (bubbler) labels from the downloads in data/raw/bubblers/.

The downloads are untrusted data, so run this with python -I:
  python -I scripts/build_bubblers.py
Writes data/processed/bubbler_points.csv (every point, with source and whether it counts),
data/processed/bubbler_labels.csv (one row per study and growth hexagon), and the
coverage check and OSM tag counts to experiments/bubblers/.
"""
from pathlib import Path
import argparse
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import geopandas as gpd
import pandas as pd

from pigeon_ai.bubblers import (
    LABEL, LABELS_FILE, POINTS_FILE, RAW_DIR, build_points, coverage, hex_labels, load_official, load_osm,
)
from pigeon_ai.paths import CRS, PROCESSED, ROOT

REPORT_DIR = ROOT / "experiments/bubblers"


def study_and_growth_hexes():
    study = pd.read_csv(PROCESSED / "sydney_extended_features.csv", usecols=["hex_id"]).hex_id
    growth = pd.read_csv(PROCESSED / "sydney_growth_features.csv", usecols=["hex_id"]).hex_id
    growth = growth[~growth.isin(set(study))]
    return pd.concat([pd.DataFrame({"hex_id": study, "area": "study"}),
                      pd.DataFrame({"hex_id": growth, "area": "growth"})], ignore_index=True)


def main(raw_dir):
    osm, tag_counts = load_osm(raw_dir / "osm/drinking_water.json")
    official = load_official(raw_dir / "official")
    lga = gpd.read_file(raw_dir / "lga/lga.geojson")[["lganame", "geometry"]].to_crs(CRS)
    points = build_points(osm, official, lga)
    labels = hex_labels(points, study_and_growth_hexes(), lga)
    cov = coverage(points)

    points.to_csv(POINTS_FILE, index=False)
    labels.to_csv(LABELS_FILE, index=False)
    cov.to_csv(REPORT_DIR / "coverage.csv", index=False, float_format="%.4f")
    tag_counts.to_csv(REPORT_DIR / "osm_tag_counts.csv", index=False)
    print(cov.to_string(index=False))
    for area, rows in labels.groupby("area", sort=False):
        print(f"{area}: {rows[LABEL].sum():,} fountains in {(rows[LABEL] > 0).sum():,} of {len(rows):,} hexagons")
    print(f"points: {len(points):,} ({int(points.counted.sum()):,} counted); wrote {POINTS_FILE.name} and {LABELS_FILE.name}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--raw-dir", type=Path, default=RAW_DIR)
    main(parser.parse_args().raw_dir)
