"""Regression checks for allocation, age normalization and approved V7 NaNs."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely import box

from pigeon_ai.demographics import AGE_FEATURES, AGE_GROUPS, calculate_demographics
from pigeon_ai.paths import CRS


class DemographicTests(unittest.TestCase):
    def setUp(self):
        self.boundaries = gpd.GeoDataFrame(
            {"sa1_code": ["a", "b"], "population": [100.0, 300.0]},
            geometry=[box(0, 0, 10, 10), box(10, 0, 20, 10)], crs=CRS,
        )
        self.grid = gpd.GeoDataFrame(
            {"hex_id": ["hex"]}, geometry=[box(5, 0, 20, 10)], crs=CRS,
        )
        self.source = pd.DataFrame({
            "age_0_17": [10.0, 90.0], "age_18_25": [20.0, 30.0],
            "age_26_64": [60.0, 150.0], "age_65plus": [10.0, 30.0],
            "households_total": [20.0, 80.0],
            "seifa_irsd_score": [800.0, 1200.0], "irsd_excluded": [False, False],
        }, index=["a", "b"])

    def test_area_counts_and_population_weighted_score(self):
        result, _ = calculate_demographics(self.grid, self.boundaries, self.source)
        np.testing.assert_allclose(result.loc["hex", AGE_FEATURES], np.array([95, 40, 180, 35]) / 350 * 100)
        self.assertEqual(result.loc["hex", "households_total"], 90)
        self.assertAlmostEqual(result.loc["hex", "seifa_irsd_score"], (50 * 800 + 300 * 1200) / 350)

    def test_normalizes_age_counts_despite_published_population_discrepancy(self):
        self.source[list(AGE_GROUPS)] *= 2
        result, _ = calculate_demographics(self.grid, self.boundaries, self.source)
        self.assertAlmostEqual(result[AGE_FEATURES].iloc[0].sum(), 100)
        self.assertAlmostEqual(result.loc["hex", "age_0_17_pct"], 95 / 350 * 100)

    def test_partial_irsd_is_missing_without_reweighting(self):
        self.source.loc["b", ["seifa_irsd_score", "irsd_excluded"]] = [np.nan, True]
        result, report = calculate_demographics(self.grid, self.boundaries, self.source)
        self.assertTrue(pd.isna(result.loc["hex", "seifa_irsd_score"]))
        self.assertEqual(report["resident_weight_from_unscored_SA1"], 1)
        self.assertFalse(result[AGE_FEATURES].isna().any().any())

    def test_zero_population_masks_even_positive_published_ages(self):
        self.boundaries["population"] = 0
        result, report = calculate_demographics(self.grid, self.boundaries, self.source)
        self.assertTrue(result[AGE_FEATURES + ["seifa_irsd_score"]].isna().all().all())
        self.assertEqual(report["zero_population"], 1)
        self.assertEqual(result.loc["hex", "households_total"], 90)

    def test_positive_population_with_zero_age_counts_stays_missing(self):
        self.source[list(AGE_GROUPS)] = 0
        result, report = calculate_demographics(self.grid, self.boundaries, self.source)
        self.assertTrue(result[AGE_FEATURES].isna().all().all())
        self.assertEqual(report["positive_population_without_age_counts"], 1)
        self.assertTrue(pd.notna(result.loc["hex", "seifa_irsd_score"]))

    def test_unscored_zero_resident_weight_does_not_mask_known_score(self):
        self.boundaries.loc[1, "population"] = 0
        self.source.loc["b", ["seifa_irsd_score", "irsd_excluded"]] = [np.nan, True]
        result, _ = calculate_demographics(self.grid, self.boundaries, self.source)
        self.assertEqual(result.loc["hex", "seifa_irsd_score"], 800)

    def test_unexplained_source_gap_is_an_error(self):
        self.source.loc["b", "seifa_irsd_score"] = np.nan
        with self.assertRaisesRegex(ValueError, "ABS Table 6"):
            calculate_demographics(self.grid, self.boundaries, self.source)


if __name__ == "__main__":
    unittest.main()
