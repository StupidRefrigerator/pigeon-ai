#!/usr/bin/env python3
"""Build V5/V9/V10 master CSVs without writing any baseline outputs."""
import argparse
import hashlib
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely import area, buffer, intersects_xy

from pigeon_ai.experiments import EXPERIMENTS, EXTENDED_FEATURES, load_experiment
from pigeon_ai.geography import (
    add_toilet_counts, build_expanded_study_area, build_grid, load_population_boundaries,
)
from pigeon_ai.osm import add_osm_counts, add_park_features, load_osm, prepare_osm
from pigeon_ai.paths import INTERIM, PROCESSED, RAW
from pigeon_ai.population import add_population_buffers, add_population_features
from pigeon_ai.validation import COLUMNS, FEATURES, validate_features


def check_overlap(current, baseline):
    """Require baseline coverage/labels; report effects of wider OSM coverage."""
    assert baseline.index.isin(current.index).all(), "Original hexagons are missing"
    overlap = current.loc[baseline.index, baseline.columns]
    pd.testing.assert_series_equal(overlap.toilet_count, baseline.toilet_count)
    for column in FEATURES:
        difference = (overlap[column] - baseline[column]).abs()
        changed = ~np.isclose(overlap[column], baseline[column], rtol=1e-10, atol=1e-6)
        if changed.any():
            print(f"  Overlap {column}: {changed.sum():,} changed; max |difference|={difference.max():.6g}", flush=True)
        if column.startswith("population"):
            np.testing.assert_allclose(overlap[column], baseline[column], rtol=1e-10, atol=1e-6)


def build(versions):
    baseline_path = PROCESSED / "sydney_hex_features.csv"
    original_hash = hashlib.sha256(baseline_path.read_bytes()).hexdigest()
    baseline = pd.read_csv(baseline_path).set_index("hex_id")
    original_experiments = {v: load_experiment(v) for v in ("V1", "V2", "V3", "V4")}
    try:
        print("Load Census and full-NSW OSM sources (separate experiment intermediates)", flush=True)
        boundaries = load_population_boundaries()
        osm_path = prepare_osm(INTERIM / "osm_experiments", full_nsw=True)
        objects, parks = load_osm(osm_path)
        for version in versions:
            print(f"Build {version}", flush=True)
            if version == "V5":
                # Use committed baseline attributes verbatim; only compute new columns.
                geometry = gpd.read_file(PROCESSED / "sydney_hex_features.gpkg")
                geometry = geometry.set_index("hex_id").loc[baseline.index, ["geometry"]]
                grid = gpd.GeoDataFrame(baseline.join(geometry), geometry="geometry", crs=geometry.crs).reset_index()
                grid = add_osm_counts(grid, objects, (1000,))
                grid = add_park_features(grid, parks, (1000,))
                grid = add_population_buffers(grid, boundaries, (1000,))
                new_columns = EXTENDED_FEATURES[len(FEATURES):]
                # The functions also calculate inside/nearest features; keep their
                # original baseline values rather than replacing them with wider OSM.
                added = grid.set_index("hex_id")[new_columns]
                result = baseline.join(added)
                features = gpd.GeoDataFrame(result.join(geometry), geometry="geometry", crs=geometry.crs).reset_index()
                validate_features(features[COLUMNS])
                pd.testing.assert_frame_equal(result[baseline.columns], baseline, check_exact=True)
                assert np.isfinite(added.to_numpy()).all() and (added >= 0).all().all()
                for category in ("population", "shop", "food", "bus_stop", "train_station", "park_area"):
                    suffix = "_m2" if category == "park_area" else ""
                    small, large = f"{category}_500m{suffix}", f"{category}_1000m{suffix}"
                    assert (result[large] + 1e-6 >= result[small]).all(), f"Non-nested {category} buffers"
                    if category not in ("population", "park_area"):
                        assert result[large].mod(1).eq(0).all()
                assert (result.park_area_1000m_m2 <= area(buffer(features.centroid.array, 1000)) + 1e-6).all()
            else:
                study = build_expanded_study_area(boundaries, include_rural=version == "V10")
                assert study["population"].notna().all(), "Missing Census population"
                print(f"  {len(study):,} SA1s; generate resolution-9 grid", flush=True)
                grid = add_toilet_counts(build_grid(study))
                print(f"  {len(grid):,} hexagons; allocate cell populations", flush=True)
                grid = add_population_features(grid, boundaries)
                print("  Count OSM destinations", flush=True)
                grid = add_osm_counts(grid, objects)
                print("  Calculate park intersections and nearest distances", flush=True)
                grid = add_park_features(grid, parks)
                print("  Allocate 250 m and 500 m populations", flush=True)
                grid = add_population_buffers(grid, boundaries)
                features = grid[COLUMNS].sort_values("hex_id").reset_index(drop=True)
                validate_features(features)
                result = features.drop(columns="geometry").set_index("hex_id")
                check_overlap(result, baseline)
                if version == "V10":
                    growth_ids = set(build_grid(build_expanded_study_area(boundaries))["hex_id"])
                    assert growth_ids <= set(result.index), "V10 is missing V9 hexagons"
                    growth_path = PROCESSED / EXPERIMENTS["V9"]["dataset"]
                    if growth_path.exists():
                        growth = pd.read_csv(growth_path).set_index("hex_id")
                        assert set(growth.index) == growth_ids, "Existing V9 has a different study area"
                        check_overlap(result, growth)
                    city = gpd.read_file(RAW / "abs_boundaries/GCCSA_2026_AUST_GDA2020.shp")
                    city = city[city["GCC_NAME26"] == "Greater Sydney"].to_crs(features.crs)
                    # Allow 1 m for the 2021/2026 boundary precision difference;
                    # keep whole cells, but ensure their centres stay in Sydney.
                    city_shape = city.geometry.union_all().buffer(1)
                    centres = features.centroid
                    assert intersects_xy(city_shape, centres.x, centres.y).all(), (
                        "V10 cell centres extend outside Greater Sydney"
                    )

            assert result.index.is_unique and result.index.notna().all()
            path = PROCESSED / EXPERIMENTS[version]["dataset"]
            if version == "V5" and path.exists():
                existing = pd.read_csv(path).set_index("hex_id")
                assert existing.index.equals(result.index), "Extended master hexagons differ"
                extra_columns = [column for column in existing if column not in result]
                # Rebuilding 1 km context must retain V6/V7 and future columns.
                result = result.join(existing[extra_columns])
            result.reset_index().to_csv(path, index=False)
            X, y = load_experiment(version)
            assert X.index.equals(result.index) and X.index.equals(y.index)
            assert list(X.columns) == EXPERIMENTS[version]["features"]
            assert not {"hex_id", "toilet_count", "has_toilet", "geometry"} & set(X.columns)
            pd.testing.assert_series_equal(y, result.toilet_count.gt(0).astype(int).rename("has_toilet"))
            if version == "V5":
                pd.testing.assert_frame_equal(
                    X[FEATURES], original_experiments["V1"][0], check_exact=True,
                )
            print(
                f"{version}: {len(result):,} rows, {len(X.columns)} predictors, "
                f"{len(result) - len(baseline):,} additional hexagons, "
                f"{y.sum():,} occupied ({y.mean():.2%}); saved {path.name}", flush=True,
            )
        for version, (old_X, old_y) in original_experiments.items():
            X, y = load_experiment(version)
            pd.testing.assert_frame_equal(X, old_X)
            pd.testing.assert_series_equal(y, old_y)
        print("V1–V4 unchanged; all requested experiment checks passed", flush=True)
    finally:
        assert hashlib.sha256(baseline_path.read_bytes()).hexdigest() == original_hash, "Baseline CSV changed"
        print(f"Baseline SHA-256 unchanged: {original_hash}", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--versions", nargs="+", choices=("V5", "V9", "V10"), default=["V5", "V9", "V10"])
    build(parser.parse_args().versions)
