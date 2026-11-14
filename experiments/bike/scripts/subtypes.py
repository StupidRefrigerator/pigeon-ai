"""Does the recipe work per facility type? RF length and RF classifier on painted lanes and on off-road paths.

Usage: python -I subtypes.py   (writes experiments/bike/out/subtypes.csv)
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_experiments import FEATURE_SETS, OUT, cross_validate, cv_generic, load, rf_classifier, spatial_folds, top_hits

SUBTYPES = {
    "painted lanes (OSM)": "bike_painted_m",
    "off-road: separated + shared paths (OSM)": ["bike_separated_m", "bike_shared_path_m"],
    "all dedicated (OSM, the main label)": "bike_len_m",
    "all dedicated (TfNSW)": "tfnsw_len_m",
}


def main():
    df = load()
    folds = spatial_folds(df)
    features = FEATURE_SETS["bike"]
    rows = []
    for name, cols in SUBTYPES.items():
        df["y_len"] = df[cols].sum(axis=1) if isinstance(cols, list) else df[cols]
        df["y_has"] = (df["y_len"] >= 20).astype(int)
        y = df["y_has"].to_numpy()
        p_len, _, _ = cross_validate(df, features, "y_len", 0, folds=folds)
        p_cls = cv_generic(df, features, rf_classifier, "y_has", folds, proba=True)
        rows.append(dict(target=name, hexes_with=int(y.sum()), random_pr_auc=y.mean(), km=df["y_len"].sum() / 1000,
                         rf_length_pr_auc=average_precision_score(y, p_len),
                         rf_classifier_pr_auc=average_precision_score(y, p_cls),
                         rf_length_top100=top_hits(p_len, y), rf_length_pred_km=np.clip(p_len, 0, None).sum() / 1000))
    out = pd.DataFrame(rows)
    out.to_csv(OUT / "subtypes.csv", index=False)
    print(out.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
