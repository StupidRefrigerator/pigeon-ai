#!/usr/bin/env python3
"""Append V8 planning scenarios without changing existing master values."""
import hashlib
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import geopandas as gpd
import pandas as pd

from pigeon_ai.experiments import load_experiment
from pigeon_ai.geography import load_population_boundaries
from pigeon_ai.paths import PROCESSED, RAW
from pigeon_ai.projections import (
    PROJECTION_FEATURES, PROJECTION_PATH, calculate_projections,
    load_projection_tables, map_projection_units,
)


def main():
    versions = [f"V{number}" for number in range(1, 8)] + ["V9", "V10"]
    before = {version: load_experiment(version) for version in versions}
    protected = [PROCESSED / f"sydney_{name}_features.csv" for name in ("hex", "growth", "all")]
    protected += [PROJECTION_PATH, RAW / "abs_sa1_2021/SA1_2021_AUST_GDA2020.shp"]
    protected.append(RAW / "census_2021/2021 Census GCP Statistical Area 1 for NSW/2021Census_G01_NSW_SA1.csv")
    hashes = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in protected}
    path = PROCESSED / "sydney_extended_features.csv"
    original = pd.read_csv(path).set_index("hex_id")
    old_columns = [column for column in original if column not in PROJECTION_FEATURES]
    pd.testing.assert_frame_equal(original[before["V1"][0].columns], before["V1"][0], check_exact=True)
    pd.testing.assert_series_equal(original.toilet_count.gt(0).astype(int).rename("has_toilet"), before["V1"][1])
    temporary = path.with_suffix(".csv.tmp")
    try:
        print("Validate native NSW SA2 and collapsed-unit workbook mappings", flush=True)
        boundaries = load_population_boundaries()
        nsw = boundaries[boundaries.STE_CODE21.eq("1")].copy()
        # The two non-spatial 'no usual address' / migratory categories have
        # no polygons or projection rows; they cannot intersect any hexagon.
        spatial = nsw.geometry.notna() & ~nsw.geometry.is_empty
        totals, collapsed = load_projection_tables()
        mapping = map_projection_units(nsw.loc[spatial], totals, collapsed)
        geometry = gpd.read_file(PROCESSED / "sydney_hex_features.gpkg").set_index("hex_id")
        grid = geometry.loc[original.index, ["population_est", "geometry"]].reset_index()
        print(f"Scale Census contributions for {len(grid):,} hexagons", flush=True)
        added, report = calculate_projections(grid, nsw, mapping)
        assert added.index.equals(original.index) and added.index.is_unique
        text = pd.read_csv(path, dtype=str).set_index("hex_id")[old_columns]
        text.join(added).reset_index().to_csv(temporary, index=False, na_rep="")
        saved = pd.read_csv(temporary).set_index("hex_id")
        pd.testing.assert_frame_equal(saved[old_columns], original[old_columns], check_exact=True)
        pd.testing.assert_frame_equal(saved[PROJECTION_FEATURES], added, rtol=1e-12, atol=1e-10)
        temporary.replace(path)
        for version, (old_X, old_y) in before.items():
            X, y = load_experiment(version)
            pd.testing.assert_frame_equal(X, old_X, check_exact=True)
            pd.testing.assert_series_equal(y, old_y, check_exact=True)
        X, y = load_experiment("V8")
        assert X.shape == (len(original), 24)
        assert X.index.equals(y.index) and X.index.is_unique and X.index.notna().all()
        pd.testing.assert_frame_equal(X[before["V1"][0].columns], before["V1"][0], check_exact=True)
        pd.testing.assert_series_equal(y, before["V1"][1], check_exact=True)
        assert set(X) == set(before["V1"][0]) | set(PROJECTION_FEATURES)
        print(added.describe().round(3).to_string(), flush=True)
        print(f"Missing values: {added.isna().sum().to_dict()}", flush=True)
        print(f"Geographic mapping: {report}", flush=True)
        print(f"Extended master: {len(saved):,} rows, {len(saved.columns) - 1} predictors", flush=True)
        print("V8 planning scenario saved; all earlier values/experiments and protected sources unchanged", flush=True)
    finally:
        for source, digest in hashes.items():
            assert hashlib.sha256(source.read_bytes()).hexdigest() == digest, f"Protected source changed: {source}"
        if temporary.exists():
            temporary.unlink()


if __name__ == "__main__":
    main()
