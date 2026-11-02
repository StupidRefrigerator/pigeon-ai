#!/usr/bin/env python3
"""Append V6 to the extended master, preserving every other existing value."""
import hashlib
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import geopandas as gpd
import numpy as np
import pandas as pd

from pigeon_ai.accessibility import (
    ACCESSIBILITY_FEATURES, calculate_accessibility, extract_walking_network,
    load_walking_network,
)
from pigeon_ai.experiments import EXTENDED_FEATURES, load_experiment
from pigeon_ai.paths import PROCESSED


def main():
    protected = [PROCESSED / f"sydney_{name}_features.csv" for name in ("hex", "growth", "all")]
    hashes = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in protected}
    versions = ("V1", "V2", "V3", "V4", "V5", "V9", "V10")
    before = {version: load_experiment(version) for version in versions}
    path = PROCESSED / "sydney_extended_features.csv"
    original = pd.read_csv(path).set_index("hex_id")
    old_columns = [c for c in original if c not in ACCESSIBILITY_FEATURES]
    assert set(EXTENDED_FEATURES + ["toilet_count"]) <= set(old_columns)
    pd.testing.assert_frame_equal(original[before["V1"][0].columns], before["V1"][0], check_exact=True)
    geometry = gpd.read_file(PROCESSED / "sydney_hex_features.gpkg").set_index("hex_id")
    grid = geometry.loc[original.index, ["geometry"]].reset_index()
    print("Extract public walking network from the existing NSW PBF", flush=True)
    network_path, coverage = extract_walking_network(grid)
    ways = load_walking_network(network_path)
    print(f"Calculate V6 for {len(grid):,} hexagons", flush=True)
    added = calculate_accessibility(grid, ways, coverage)
    # Keep original CSV text, including float precision, for every retained column.
    text = pd.read_csv(path, dtype=str).set_index("hex_id")[old_columns]
    output = text.join(added)
    temporary = path.with_suffix(".csv.tmp")
    try:
        output.reset_index().to_csv(temporary, index=False)
        saved = pd.read_csv(temporary).set_index("hex_id")
        pd.testing.assert_frame_equal(saved[old_columns], original[old_columns], check_exact=True)
        assert np.isfinite(saved[ACCESSIBILITY_FEATURES].to_numpy()).all()
        assert saved.walkable_junctions_500m.mod(1).eq(0).all()
        temporary.replace(path)
        for version, (old_X, old_y) in before.items():
            X, y = load_experiment(version)
            pd.testing.assert_frame_equal(X, old_X, check_exact=True)
            pd.testing.assert_series_equal(y, old_y, check_exact=True)
        X, y = load_experiment("V6")
        assert X.shape == (len(original), 23)
        pd.testing.assert_frame_equal(X[before["V1"][0].columns], before["V1"][0], check_exact=True)
        pd.testing.assert_series_equal(y, before["V1"][1], check_exact=True)
        assert X.index.is_unique and X.index.equals(y.index)
        assert set(X) == set(before["V1"][0]) | set(ACCESSIBILITY_FEATURES)
        print(added.describe().round(2).to_string(), flush=True)
        # Reproducible geographic checks: closest cell to Town Hall, and a
        # low-density cell (among the lowest population-density decile).
        cbd = gpd.GeoSeries(gpd.points_from_xy([151.2069], [-33.8732]), crs=4326).to_crs(grid.crs).iloc[0]
        cbd_index = grid.centroid.distance(cbd).idxmin()
        low_ids = original.index[original.population_density <= original.population_density.quantile(0.1)]
        low_id = added.loc[low_ids, "walkable_length_500m"].idxmin()
        for label, hex_id in (("Town Hall", grid.loc[cbd_index, "hex_id"]), ("Low-density", low_id)):
            point = geometry.loc[[hex_id]].centroid.to_crs(4326).iloc[0]
            print(f"{label}: {hex_id}, ({point.y:.5f}, {point.x:.5f}), population density={original.loc[hex_id, 'population_density']:.2f}", flush=True)
            print(added.loc[hex_id].to_dict(), flush=True)
        print("V6 saved; V1–V5/V9/V10 and all existing extended columns unchanged", flush=True)
    finally:
        for source, digest in hashes.items():
            assert hashlib.sha256(source.read_bytes()).hexdigest() == digest, f"Protected dataset changed: {source}"


if __name__ == "__main__":
    main()
