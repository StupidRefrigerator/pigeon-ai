"""Small topology/access regressions; run with unittest discover -s tests."""
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import geopandas as gpd
from shapely import LineString, box

from pigeon_ai.accessibility import (
    calculate_accessibility, eligible_way, walking_junctions,
)
from pigeon_ai.paths import CRS


def ways(records):
    return gpd.GeoDataFrame([
        {"nodes": ids, "geometry": LineString(coords), "dedicated": True,
         "roundabout": ring}
        for ids, coords, ring in records
    ], crs=CRS)


class AccessibilityTests(unittest.TestCase):
    def test_access_policy(self):
        for highway in ["footway", "path", "pedestrian", "steps", "residential", "track"]:
            self.assertTrue(eligible_way({"highway": highway}))
        for tags in [
            {"highway": "motorway", "foot": "yes"},
            {"highway": "footway", "access": "private", "foot": "yes"},
            {"highway": "path", "foot": "no"},
            {"highway": "residential", "foot": "use_sidepath"},
            {"highway": "residential", "sidewalk:left": "separate"},
            {"highway": "pedestrian", "area": "yes"},
            {"highway": "cycleway"},
        ]:
            self.assertFalse(eligible_way(tags), tags)
        self.assertTrue(eligible_way({"highway": "cycleway", "foot": "yes"}))
        self.assertTrue(eligible_way({"highway": "residential", "sidewalk": "no"}))

    def test_split_nodes_and_duplicate_edges_are_not_junctions(self):
        network = ways([
            ([1, 2], [(0, 0), (100, 0)], False),
            ([2, 3], [(100, 0), (200, 0)], False),
            ([2, 1], [(100, 0), (0, 0)], False),
        ])
        self.assertEqual(len(walking_junctions(network)), 0)

    def test_shared_node_creates_junction_but_crossing_lines_do_not(self):
        crossing = ways([
            ([1, 2, 3], [(-100, 0), (0, 0), (100, 0)], False),
            ([4, 5, 6], [(0, -100), (0, 0), (0, 100)], False),
        ])
        self.assertEqual(len(walking_junctions(crossing)), 0)
        crossing.at[1, "nodes"] = [4, 2, 6]
        self.assertEqual(len(walking_junctions(crossing)), 1)

    def test_disconnected_nearby_junctions_are_not_merged(self):
        network = ways([
            ([1, 2, 3], [(-100, 0), (0, 0), (100, 0)], False),
            ([2, 4], [(0, 0), (0, 100)], False),
            ([5, 6, 7], [(-100, 1), (0, 1), (100, 1)], False),
            ([6, 8], [(0, 1), (0, -100)], False),
        ])
        self.assertEqual(len(walking_junctions(network)), 2)

    def test_connected_complex_junctions_merge(self):
        network = ways([
            ([1, 2, 3], [(-100, 0), (0, 0), (5, 0)], False),
            ([2, 4], [(0, 0), (0, 100)], False),
            ([3, 5], [(5, 0), (100, 0)], False),
            ([3, 6], [(5, 0), (5, -100)], False),
        ])
        self.assertEqual(len(walking_junctions(network)), 1)

    def test_roundabout_is_one_junction(self):
        network = ways([
            ([1, 2, 3, 4, 1], [(0, 0), (100, 0), (100, 100), (0, 100), (0, 0)], True),
            ([1, 5], [(0, 0), (-100, 0)], False),
            ([2, 6], [(100, 0), (200, 0)], False),
            ([3, 7], [(100, 100), (200, 100)], False),
        ])
        self.assertEqual(len(walking_junctions(network)), 1)

    def test_clipping_deduplication_and_uncapped_nearest(self):
        network = ways([
            ([1, 2], [(-1000, 0), (1000, 0)], False),
            ([2, 1], [(1000, 0), (-1000, 0)], False),
        ])
        grid = gpd.GeoDataFrame({"hex_id": ["test"]}, geometry=[box(-1, -1, 1, 1)], crs=CRS)
        result = calculate_accessibility(grid, network, box(-5000, -5000, 5000, 5000))
        self.assertAlmostEqual(result.loc["test", "walkable_length_500m"], 1000)
        self.assertEqual(result.loc["test", "distance_nearest_footpath_m"], 0)
        network["geometry"] = network.geometry.translate(yoff=1000)
        result = calculate_accessibility(grid, network, box(-5000, -5000, 5000, 5000))
        self.assertEqual(result.loc["test", "walkable_length_500m"], 0)
        self.assertEqual(result.loc["test", "distance_nearest_footpath_m"], 1000)
        with self.assertRaisesRegex(ValueError, "too small"):
            calculate_accessibility(grid, network, box(-600, -600, 600, 600))


if __name__ == "__main__":
    unittest.main()
