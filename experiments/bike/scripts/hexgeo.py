"""Shared hex helpers: line length per res-9 hex, point counts, disk sums, the study hex list."""
from pathlib import Path

import h3
import numpy as np
import pandas as pd
import shapely
from pyproj import Transformer

REPO = Path(__file__).resolve().parents[3]
STUDY_FILE = REPO / "data/processed/sydney_extended_features.csv"
BIKE_DATA = REPO / "experiments/bike/data"
RES = 9
PIECE_M = 10
TO_MGA = Transformer.from_crs(4326, 7856, always_xy=True)
TO_WGS = Transformer.from_crs(7856, 4326, always_xy=True)


def study_hexes():
    return pd.read_csv(STUDY_FILE, usecols=["hex_id"])["hex_id"]


def line_length_by_hex(geoms_wgs, groups=None):
    """Metres of each line inside each res-9 hex, split into 10 m pieces assigned by midpoint.

    geoms_wgs: array of shapely LineStrings in lon/lat. groups: optional label per line.
    Returns a DataFrame with hex_id, group and length_m.
    """
    geoms = shapely.transform(np.asarray(geoms_wgs), lambda xy: np.column_stack(TO_MGA.transform(xy[:, 0], xy[:, 1])))
    geoms = shapely.segmentize(geoms, PIECE_M)
    coords, idx = shapely.get_coordinates(geoms, return_index=True)
    same = idx[1:] == idx[:-1]
    a, b, line = coords[:-1][same], coords[1:][same], idx[:-1][same]
    length = np.hypot(*(b - a).T)
    lon, lat = TO_WGS.transform((a[:, 0] + b[:, 0]) / 2, (a[:, 1] + b[:, 1]) / 2)
    cells = [h3.latlng_to_cell(y, x, RES) for x, y in zip(lon, lat)]
    out = pd.DataFrame({"hex_id": cells, "group": "all" if groups is None else np.asarray(groups)[line],
                        "length_m": length})
    return out.groupby(["hex_id", "group"], as_index=False)["length_m"].sum()


def count_points_by_hex(lon, lat):
    cells = [h3.latlng_to_cell(y, x, RES) for x, y in zip(lon, lat)]
    return pd.Series(cells).value_counts()


def disk_sum(values, hexes, k, include_self=True):
    """Sum of a per-hex value over grid_disk(h, k) for each hex. One ring of res-9 is about 300 m."""
    get = values.get
    out = []
    for h in hexes:
        cells = h3.grid_disk(h, k)
        total = sum(get(c, 0.0) for c in cells)
        if not include_self:
            total -= get(h, 0.0)
        out.append(total)
    return np.array(out, dtype=float)
