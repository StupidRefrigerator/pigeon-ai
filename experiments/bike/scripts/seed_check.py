"""Seeds 0-2 for the leading clean models, to see which differences beat seed noise.

Usage: python -I seed_check.py   (writes experiments/bike/out/seed_check.csv)
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_experiments import (FEATURE_SETS, HAS, LABEL, OUT, cross_validate, cv_generic, evaluate, hgb_poisson,
                             load, rf_classifier, spatial_folds)


def main():
    df = load()
    folds = spatial_folds(df)
    rows = []
    for seed in (0, 1, 2):
        for fs in ["bike", "bike_cbd"]:
            p, _, _ = cross_validate(df, FEATURE_SETS[fs], LABEL, seed, folds=folds)
            rows.append(dict(seed=seed, **evaluate(f"(a) RF length, {fs}", df, p, p)))
            p = cv_generic(df, FEATURE_SETS[fs], lambda: rf_classifier(seed), HAS, folds, proba=True)
            rows.append(dict(seed=seed, **evaluate(f"(b) RF classifier, {fs}", df, p)))
            p = cv_generic(df, FEATURE_SETS[fs], lambda: hgb_poisson(seed), LABEL, folds)
            rows.append(dict(seed=seed, **evaluate(f"(c) HGB Poisson length, {fs}", df, p, p)))
    out = pd.DataFrame(rows)
    out.to_csv(OUT / "seed_check.csv", index=False)
    summary = out.groupby("model")[["pr_auc", "top100", "top1000", "pred_km", "deviance_km"]].agg(["mean", "min", "max"])
    print(summary.round(3).to_string())


if __name__ == "__main__":
    main()
