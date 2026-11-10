#!/usr/bin/env python3
"""Build the V12 OSM features (sports, playgrounds, beaches, OSM toilets) from cached Overpass tiles."""
from pathlib import Path
import argparse
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pandas as pd

from pigeon_ai.paths import PROCESSED
from pigeon_ai.recreation import (
    OSM_TOILET_COLUMNS, OVERPASS_DIR, RECREATION_FEATURES, TOILET_POINT_COLUMNS, build_features,
    load_layers, toilet_points,
)

STUDY_OUT = "sydney_recreation_features.csv"
GROWTH_OUT = "sydney_growth_recreation_features.csv"
TOILETS_OUT = "osm_toilets.csv"


def main(overpass_dir, out_dir):
    study = pd.read_csv(PROCESSED / "sydney_extended_features.csv", usecols=["hex_id"]).hex_id
    growth = pd.read_csv(PROCESSED / "sydney_growth_features.csv", usecols=["hex_id"]).hex_id.drop_duplicates()
    print(f"Parse Overpass tiles in {overpass_dir}", flush=True)
    layers = load_layers(overpass_dir)
    print({name: len(layer) for name, layer in layers.items()}, flush=True)
    points = toilet_points(layers["toilets"])

    print(f"Calculate features for {len(set(study) | set(growth)):,} hexagons", flush=True)
    features = build_features(sorted(set(study) | set(growth)), layers, points).set_index("hex_id")
    assert list(features.columns) == RECREATION_FEATURES + OSM_TOILET_COLUMNS
    assert features.notna().all().all()

    out_dir.mkdir(parents=True, exist_ok=True)
    points[TOILET_POINT_COLUMNS].to_csv(out_dir / TOILETS_OUT, index=False)
    features.loc[study].reset_index().to_csv(out_dir / STUDY_OUT, index=False)
    features.loc[growth].reset_index().to_csv(out_dir / GROWTH_OUT, index=False)
    print(f"Saved {len(study):,} study rows, {len(growth):,} growth rows and {len(points):,} OSM toilets "
          f"to {out_dir}", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--overpass-dir", type=Path, default=OVERPASS_DIR)
    parser.add_argument("--out-dir", type=Path, default=PROCESSED)
    args = parser.parse_args()
    main(args.overpass_dir, args.out_dir)
