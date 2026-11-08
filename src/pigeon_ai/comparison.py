"""Held-out (spatial cross-validated) predictions for named feature sets."""
import numpy as np
import pandas as pd

from .experiments import EXPERIMENTS, load_experiment
from .model import DATA_FILE, TARGETS, cross_validate, metrics_row

LATEST = "latest"


def held_out_predictions(X, y, seed=0, with_shap=False):
    """Predict every hex with a forest that never saw its res-6 block.

    X and y share a hex_id index. With with_shap, the mean |SHAP| of each
    feature over the held-out rows is stored in `frame.attrs["mean_abs_shap"]`.
    """
    df = X.assign(hex_id=X.index, toilet_count=y)
    pred, fold, shap_values = cross_validate(df, list(X.columns), "toilet_count", seed, with_shap)
    frame = pd.DataFrame({"toilet_count": y.to_numpy(), "predicted_toilets": pred, "fold": fold},
                         index=X.index)
    if with_shap:
        frame.attrs["mean_abs_shap"] = dict(zip(X.columns, np.abs(shap_values).mean(axis=0)))
    return frame


def load_model_data(name):
    """(X, y) for "V1".."V10", or "latest", the production feature set."""
    if name != LATEST:
        return load_experiment(name)
    target = TARGETS["toilets"]
    data = pd.read_csv(DATA_FILE).set_index("hex_id")
    return data[target.feature_sets[LATEST]], data[target.label]


def run_comparison(versions, out_dir, seed=0):
    """Write {version}_predictions.csv and comparison.csv; return a short report."""
    versions = list(versions or EXPERIMENTS)
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for version in versions:
        X, y = load_model_data(version)
        print(f"{version}: {len(X):,} hexes, {len(X.columns)} features", flush=True)
        frame = held_out_predictions(X, y, seed)
        frame.to_csv(out_dir / f"{version}_predictions.csv", index_label="hex_id")
        actual, pred = frame["toilet_count"].to_numpy(), frame["predicted_toilets"].to_numpy()
        rows.append({**metrics_row(version, actual, pred, pred),
                     "hexes": len(X), "features": len(X.columns)})
    table = pd.DataFrame(rows).astype({"top100_hits": "Int64", "candidates": "Int64"})
    table.to_csv(out_dir / "comparison.csv", index=False)
    text = table.to_string(index=False, float_format=lambda v: f"{v:.4f}")
    if {"V9", "V10"} & set(versions):
        text += ("\n\nV9 and V10 use different hex sets from V1-V8, so their numbers are "
                 "not comparable to V1-V8.")
    return text
