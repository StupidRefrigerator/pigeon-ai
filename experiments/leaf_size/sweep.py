"""Leaf-size sweep for the V12 forest: same data, inputs, folds and seed as the real run.

Run from the project root: python experiments/leaf_size/sweep.py
Writes experiments/leaf_size/results.csv. Takes about 5 minutes.
"""
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import average_precision_score, mean_poisson_deviance

from pigeon_ai import model

LEAF_SIZES = [1, 5, 10, 20, 50, 100, 500]
OUT = Path(__file__).with_name("results.csv")


def forest(leaf, seed=0):
    return RandomForestRegressor(n_estimators=300, min_samples_leaf=leaf, max_features=0.5, n_jobs=-1,
                                 random_state=seed)


def main():
    target = model.TARGETS["toilets"]
    features, label = target.feature_sets[model.DEFAULT_FEATURES], target.label
    df = model.load_data()
    y = df[label].to_numpy()
    rows = []
    for leaf in LEAF_SIZES:
        # cross_validate builds its forests with model.make_forest; swap in this leaf size.
        model.make_forest = lambda seed, leaf=leaf: forest(leaf, seed)
        pred, _, _ = model.cross_validate(df, features, label)
        full = forest(leaf).fit(df[features].to_numpy(), y)
        fit = full.predict(df[features].to_numpy())
        rows.append({
            "min_samples_leaf": leaf,
            "deviance_unseen": mean_poisson_deviance(y, np.maximum(pred, model.MIN_PREDICTION)),
            "deviance_trained": mean_poisson_deviance(y, np.maximum(fit, model.MIN_PREDICTION)),
            "pr_auc": average_precision_score(y > 0, pred),
            "top_1000_hits": model.top_hits(pred, y, 1000),
            "median_tree_depth": int(np.median([t.get_depth() for t in full.estimators_])),
        })
        print(rows[-1], flush=True)
    pd.DataFrame(rows).round(4).to_csv(OUT, index=False)


if __name__ == "__main__":
    main()
