"""Shared feature selections and master datasets for PIGEON-AI."""

import pandas as pd

from .paths import PROCESSED
from .validation import FEATURES
from .accessibility import ACCESSIBILITY_FEATURES
from .demographics import DEMOGRAPHIC_FEATURES
from .projections import PROJECTION_FEATURES

EXTENDED_FEATURES = FEATURES + [
    "population_1000m", "shop_1000m", "food_1000m",
    "bus_stop_1000m", "train_station_1000m", "park_area_1000m_m2",
]

EXPERIMENTS = {
    "V1": {
        "description": "Baseline: all current predictors",
        "features": list(FEATURES),
    },
    "V2": {
        "description": "Population only",
        "features": [
            "population_est", "population_density",
            "population_250m", "population_500m",
        ],
    },
    "V3": {
        "description": "Amenities only: all existing OSM predictors",
        "features": [
            "shop_inside", "shop_250m", "shop_500m",
            "food_inside", "food_250m", "food_500m",
            "bus_stop_inside", "bus_stop_250m", "bus_stop_500m",
            "train_station_inside", "train_station_250m", "train_station_500m",
            "park_area_inside_m2", "park_area_250m_m2", "park_area_500m_m2",
            "distance_nearest_park_m",
        ],
    },
    "V4": {
        "description": "Local only: inside-hex and 250 m population/OSM features",
        "features": [
            # Both describe the cell itself, including density per square km.
            "population_est", "population_density",
            "shop_inside", "shop_250m",
            "food_inside", "food_250m",
            "bus_stop_inside", "bus_stop_250m",
            "train_station_inside", "train_station_250m",
            "park_area_inside_m2", "park_area_250m_m2",
            "population_250m",
            # Nearest-park distance searches all parks, so is not local-only.
        ],
    },
    "V5": {
        "description": "Baseline study area with additional 1,000 m context",
        "dataset": "sydney_extended_features.csv",
        "features": EXTENDED_FEATURES,
    },
    "V6": {
        "description": "Baseline plus public pedestrian accessibility (no 1 km features)",
        "dataset": "sydney_extended_features.csv",
        "features": FEATURES + ACCESSIBILITY_FEATURES,
    },
    "V7": {
        "description": "Baseline plus demographics; undefined values remain NaN",
        "dataset": "sydney_extended_features.csv",
        "features": FEATURES + DEMOGRAPHIC_FEATURES,
    },
    "V8": {
        "description": "Future-planning scenario using 2024-release projections; not a historical benchmark",
        "dataset": "sydney_extended_features.csv",
        "features": FEATURES + PROJECTION_FEATURES,
    },
    "V9": {
        "description": "Original pre-growth-exclusion study area",
        "dataset": "sydney_growth_features.csv",
        "features": list(FEATURES),
    },
    "V10": {
        "description": "All Greater Sydney, including growth and rural areas",
        "dataset": "sydney_all_features.csv",
        "features": list(FEATURES),
    },
}


def load_experiment(version):
    """Return (X, y) from the master CSV, preserving row order.

    X and y share a hex_id index (retrieve with X.index). The binary target
    is named has_toilet: 1 when toilet_count > 0, otherwise 0.
    V7 retains approved demographic NaNs; handle them in future training code.
    V8 is a planning scenario; growth percentages are NaN for zero population.
    """
    if version not in EXPERIMENTS:
        raise ValueError(
            f"Unknown experiment {version!r}; choose {', '.join(EXPERIMENTS)}"
        )

    feature_names = EXPERIMENTS[version]["features"]
    dataset = EXPERIMENTS[version].get("dataset", "sydney_hex_features.csv")
    path = PROCESSED / dataset
    if not path.exists():
        raise FileNotFoundError(
            f"Missing master dataset: {path}. For V5/V9/V10, run "
            "python scripts/build_experiments.py; then scripts/build_accessibility.py "
            "for V6, scripts/build_demographics.py for V7, or "
            "scripts/build_projections.py for V8 (using Python)."
        )
    data = pd.read_csv(path)
    required = ["hex_id", "toilet_count"] + feature_names
    missing = [column for column in required if column not in data.columns]
    if missing:
        raise ValueError(f"Missing required columns for {version}: {', '.join(missing)}")
    if data["hex_id"].isna().any() or not data["hex_id"].is_unique:
        raise ValueError("hex_id must be present and unique for every row")

    counts = data["toilet_count"]
    if counts.isna().any() or not counts.ge(0).all() or not counts.mod(1).eq(0).all():
        raise ValueError("toilet_count must contain non-negative integer counts")

    data = data.set_index("hex_id")
    X = data.loc[:, feature_names].copy()
    y = data["toilet_count"].gt(0).astype(int).rename("has_toilet")
    return X, y
