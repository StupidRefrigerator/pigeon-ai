"""Shared data loading for the combination experiments (PIGEON-AI v2)."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path("/Users/summitsetia/Desktop/University/26T3/PIGEON-AI-DATASET")
V2 = Path("/Users/summitsetia/Desktop/University/26T3/pigeon-v2")
OUT = V2 / "combos/out"
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(V2 / "postprocess"))
from pigeon_ai.model import TARGETS, cross_validate, make_forest, is_candidate  # noqa: E402,F401

LATEST = TARGETS["toilets"].feature_sets["latest"]
V1 = TARGETS["toilets"].feature_sets["v1"]
F = ["sports_inside", "sports_250m", "sports_500m", "sports_1000m", "sports_area_inside_m2",
     "sports_area_500m_m2", "playground_inside", "playground_250m", "playground_500m", "playground_1000m",
     "beach_inside", "beach_250m", "beach_500m", "beach_1000m", "distance_nearest_beach_m",
     "distance_nearest_sports_m", "distance_nearest_playground_m"]
OSM = ["osm_toilets_public", "osm_toilets_public_tagged", "osm_toilets_private"]
SEEDS = (0, 1, 2)
# name -> (uses F, label version: None | "public" | "tagged")
MODELS = {"M0": (False, None), "M1": (True, None), "M2": (False, "public"), "M3": (True, "public"),
          "M2t": (False, "tagged"), "M3t": (True, "tagged")}
DESC = {"M0": "base", "M1": "+F", "M2": "+L", "M3": "+F+L", "M2t": "+L (tagged only)", "M3t": "+F+L (tagged only)"}
OSM_COL = {"public": "osm_toilets_public", "tagged": "osm_toilets_public_tagged"}


def features(family, with_f):
    base = LATEST if family == "latest" else V1
    return base + F if with_f else list(base)


def label(df, version):
    if version is None:
        return df["toilet_count"].to_numpy()
    return np.maximum(df["toilet_count"].to_numpy(), df[OSM_COL[version]].to_numpy())


def load_study():
    df = pd.read_csv(REPO / "data/processed/sydney_extended_features.csv")
    nf = pd.read_csv(V2 / "data/new_features_study.csv")
    out = df.merge(nf, on="hex_id", how="left", validate="1:1")
    assert len(out) == 16228 and out[F + OSM].notna().all().all()
    return out


def load_growth():
    """Growth-suburb hexes only (not in the study grid), v1 columns + F + OSM."""
    study_ids = set(pd.read_csv(REPO / "data/processed/sydney_extended_features.csv", usecols=["hex_id"]).hex_id)
    g = pd.read_csv(REPO / "data/processed/sydney_growth_features.csv")
    g = g[~g.hex_id.isin(study_ids)].reset_index(drop=True)
    nf = pd.read_csv(V2 / "data/new_features_growth.csv")
    g = g.merge(nf, on="hex_id", how="left", validate="1:1")
    assert len(g) == 1108 and g[F + OSM].notna().all().all()
    return g
