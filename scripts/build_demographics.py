#!/usr/bin/env python3
"""Append V7 demographics, retaining approved NaNs and all existing values."""
import hashlib
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import geopandas as gpd
import pandas as pd

from pigeon_ai.accessibility import ACCESSIBILITY_FEATURES
from pigeon_ai.demographics import (
    DEMOGRAPHIC_FEATURES, calculate_demographics, load_sa1_demographics,
)
from pigeon_ai.experiments import EXTENDED_FEATURES, load_experiment
from pigeon_ai.geography import load_population_boundaries
from pigeon_ai.paths import PROCESSED, RAW


def main():
    versions = ("V1", "V2", "V3", "V4", "V5", "V6", "V9", "V10")
    before = {version: load_experiment(version) for version in versions}
    protected = [PROCESSED / f"sydney_{name}_features.csv" for name in ("hex", "growth", "all")]
    census = RAW / "census_2021/2021 Census GCP Statistical Area 1 for NSW"
    protected += [census / f"2021Census_{table}_NSW_SA1.csv" for table in ("G04A", "G04B", "G35")]
    protected.append(RAW / "SEIFA_2021_SA1.xlsx")
    hashes = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in protected}
    path = PROCESSED / "sydney_extended_features.csv"
    original = pd.read_csv(path).set_index("hex_id")
    old_columns = [column for column in original if column not in DEMOGRAPHIC_FEATURES]
    assert set(EXTENDED_FEATURES + ACCESSIBILITY_FEATURES + ["toilet_count"]) <= set(old_columns)
    pd.testing.assert_frame_equal(original[before["V1"][0].columns], before["V1"][0], check_exact=True)
    pd.testing.assert_series_equal(original.toilet_count.gt(0).astype(int).rename("has_toilet"), before["V1"][1])
    temporary = path.with_suffix(".csv.tmp")
    try:
        print("Read local G04A/G04B, G35 and SEIFA Table 2/Table 6", flush=True)
        source = load_sa1_demographics()
        boundaries = load_population_boundaries()
        geometry = gpd.read_file(PROCESSED / "sydney_hex_features.gpkg").set_index("hex_id")
        grid = geometry.loc[original.index, ["population_est", "geometry"]].reset_index()
        print(f"Allocate demographics to {len(grid):,} baseline hexagons", flush=True)
        added, report = calculate_demographics(grid, boundaries, source)
        assert added.index.equals(original.index) and added.index.is_unique
        # Preserve previous numeric text exactly, including any future NaNs.
        text = pd.read_csv(path, dtype=str).set_index("hex_id")[old_columns]
        text.join(added).reset_index().to_csv(temporary, index=False, na_rep="")
        saved = pd.read_csv(temporary).set_index("hex_id")
        pd.testing.assert_frame_equal(saved[old_columns], original[old_columns], check_exact=True)
        pd.testing.assert_frame_equal(saved[DEMOGRAPHIC_FEATURES], added, rtol=1e-12, atol=1e-10)
        temporary.replace(path)
        for version, (old_X, old_y) in before.items():
            X, y = load_experiment(version)
            pd.testing.assert_frame_equal(X, old_X, check_exact=True)
            pd.testing.assert_series_equal(y, old_y, check_exact=True)
        X, y = load_experiment("V7")
        assert X.shape == (len(original), 26)
        assert X.index.equals(y.index) and X.index.is_unique and X.index.notna().all()
        pd.testing.assert_frame_equal(X[before["V1"][0].columns], before["V1"][0], check_exact=True)
        pd.testing.assert_series_equal(y, before["V1"][1], check_exact=True)
        assert set(X) == set(before["V1"][0]) | set(DEMOGRAPHIC_FEATURES)
        print(added.describe().round(3).to_string(), flush=True)
        print(f"Missing-data audit: {report}", flush=True)
        print(f"Extended master: {len(saved):,} rows, {len(saved.columns) - 1} predictors", flush=True)
        print("V7 saved with NaNs retained; existing experiments, raw sources and protected CSVs unchanged", flush=True)
    finally:
        for source_path, digest in hashes.items():
            assert hashlib.sha256(source_path.read_bytes()).hexdigest() == digest, f"Protected source changed: {source_path}"
        if temporary.exists():
            temporary.unlink()


if __name__ == "__main__":
    main()
