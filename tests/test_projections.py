"""V8 mapping and allocation regressions; no model training."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely import box

from pigeon_ai.paths import CRS
from pigeon_ai.projections import calculate_projections, map_projection_units


class ProjectionTests(unittest.TestCase):
    def setUp(self):
        self.boundaries = gpd.GeoDataFrame({
            "sa1_code": ["a1", "b1"], "SA2_CODE21": ["a", "b"],
            "SA2_NAME21": ["Alpha", "Beta"], "population": [100.0, 300.0],
        }, geometry=[box(0, 0, 10, 10), box(10, 0, 20, 10)], crs=CRS)
        self.totals = pd.DataFrame({
            "SA2": ["Alpha", "Beta"], 2021: [1000, 600],
            2031: [2000, 900], 2041: [3000, 1200],
        })
        self.collapsed = pd.DataFrame(columns=["SA2_NAME_2021", "Collapsed SA2"])
        self.grid = gpd.GeoDataFrame(
            {"hex_id": ["hex"], "population_est": [350.0]},
            geometry=[box(5, 0, 20, 10)], crs=CRS,
        )

    def mapping(self):
        return map_projection_units(self.boundaries, self.totals, self.collapsed)

    def test_cross_boundary_census_scaling_not_centroid_or_erp_calibration(self):
        result, report = calculate_projections(self.grid, self.boundaries, self.mapping())
        np.testing.assert_allclose(result.iloc[0], [550, 750, 200, 200 / 350 * 100])
        self.assertEqual(report["crossing_projection_units"], 1)

    def test_collapsed_unit_has_shared_ratio_without_inventing_member_totals(self):
        self.totals = pd.DataFrame({"SA2": ["Combined"], 2021: [1000], 2031: [1500], 2041: [2000]})
        self.collapsed = pd.DataFrame({"SA2_NAME_2021": ["Alpha", "Beta"], "Collapsed SA2": ["Combined", "Combined"]})
        result, report = calculate_projections(self.grid, self.boundaries, self.mapping())
        np.testing.assert_allclose(result.iloc[0], [525, 700, 175, 50])
        self.assertEqual(report["crossing_native_SA2s"], 1)
        self.assertEqual(report["crossing_projection_units"], 0)

    def test_zero_census_population_is_zero_counts_and_undefined_percentage(self):
        self.boundaries["population"] = 0.0
        self.grid["population_est"] = 0.0
        result, _ = calculate_projections(self.grid, self.boundaries, self.mapping())
        np.testing.assert_array_equal(result.iloc[0, :3], [0, 0, 0])
        self.assertTrue(pd.isna(result.iloc[0, 3]))

    def test_declines_are_valid_negative_growth(self):
        self.totals[2031] = self.totals[2021] / 2
        result, _ = calculate_projections(self.grid, self.boundaries, self.mapping())
        np.testing.assert_allclose(result.iloc[0, [0, 2, 3]], [175, -175, -50])

    def test_duplicate_workbook_rows_fail_even_after_whitespace_normalization(self):
        extra = self.totals.iloc[[0]].copy()
        extra["SA2"] = "Alpha "
        self.totals = pd.concat([self.totals, extra])
        with self.assertRaisesRegex(ValueError, "Duplicate projection-unit"):
            self.mapping()

    def test_native_name_shared_by_different_codes_is_ambiguous(self):
        self.boundaries["SA2_NAME21"] = "Alpha"
        with self.assertRaisesRegex(ValueError, "Ambiguous native"):
            self.mapping()

    def test_native_code_with_different_names_is_ambiguous(self):
        self.boundaries["SA2_CODE21"] = "a"
        with self.assertRaisesRegex(ValueError, "Ambiguous native"):
            self.mapping()

    def test_conflicting_or_duplicate_collapsed_membership_fails(self):
        self.collapsed = pd.DataFrame({"SA2_NAME_2021": ["Alpha", "Alpha"], "Collapsed SA2": ["One", "Two"]})
        with self.assertRaisesRegex(ValueError, "ambiguous collapsed"):
            self.mapping()

    def test_standalone_and_collapsed_match_is_ambiguous(self):
        self.totals.loc[len(self.totals)] = ["Combined", 1600, 2900, 4200]
        self.collapsed = pd.DataFrame({"SA2_NAME_2021": ["Alpha"], "Collapsed SA2": ["Combined"]})
        with self.assertRaisesRegex(ValueError, "standalone and collapsed"):
            self.mapping()

    def test_unmatched_name_fails_without_fuzzy_matching(self):
        self.totals.loc[0, "SA2"] = "ALPHA"
        with self.assertRaisesRegex(ValueError, "lack a projection row"):
            self.mapping()

    def test_zero_source_baseline_fails(self):
        self.totals.loc[0, 2021] = 0
        with self.assertRaisesRegex(ValueError, "Zero projection-unit"):
            self.mapping()

    def test_invalid_projection_values_fail(self):
        for invalid in [np.nan, np.inf, -1]:
            with self.subTest(invalid=invalid):
                totals = self.totals.astype({2031: float})
                totals.loc[0, 2031] = invalid
                with self.assertRaisesRegex(ValueError, "Missing, negative or infinite"):
                    map_projection_units(self.boundaries, totals, self.collapsed)


if __name__ == "__main__":
    unittest.main()
