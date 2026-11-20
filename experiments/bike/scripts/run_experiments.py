"""Bike-lane transfer experiments. Every number is from held-out predictions on the toilet model's folds.

Usage: python -I run_experiments.py
Reads data/processed (toilet features) and experiments/bike/data; writes experiments/bike/out/.
"""
import sys
from pathlib import Path

import h3
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestClassifier
from sklearn.metrics import average_precision_score, mean_poisson_deviance

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))
from hexgeo import BIKE_DATA
from pigeon_ai.model import N_FOLDS, POPULATION_ONLY, TARGETS, cross_validate, load_data, spatial_folds, top_hits

OUT = BIKE_DATA.parent / "out"
LABEL = "bike_len_m"
HAS = "has_bike"
GAP_M = 200  # a candidate needs at least 200 m more predicted lane than exists (a hex is about 300 m across)
WALK = ["walkable_length_500m", "walkable_junctions_500m", "distance_nearest_footpath_m"]
V12 = TARGETS["toilets"].feature_sets["v12"]
V12_NOWALK = [f for f in V12 if f not in WALK]
BIKE_EXTRA = [
    "road_major_m", "road_major_600m_m", "road_mid_m", "road_mid_600m_m", "road_local_m", "road_service_m",
    "road_path_m", "road_path_600m_m", "road_drivable_m", "road_drivable_600m_m",
    "junctions_inside", "junctions_600m", "school_600m", "school_900m", "distance_nearest_school_m",
    "university_600m", "university_900m", "distance_nearest_university_m", "distance_nearest_station_m",
    "elevation_m", "slope_mean_pct", "slope_max_pct", "relief_600m_m",
]
FEATURE_SETS = {
    "toilet_v12": V12,
    "toilet_v12_nowalk": V12_NOWALK,
    "bike": V12_NOWALK + BIKE_EXTRA,
    "bike_cbd": V12_NOWALK + BIKE_EXTRA + ["distance_cbd_km"],
    "bike_ring": V12_NOWALK + BIKE_EXTRA + ["ring_bike_600m_m", "ring_bike_900m_m"],
    "bike_disk": V12_NOWALK + BIKE_EXTRA + ["disk_bike_600m_m"],
}


def load():
    df = load_data()
    labels = pd.read_csv(BIKE_DATA / "bike_labels.csv")
    feats = pd.read_csv(BIKE_DATA / "bike_features.csv")
    df = df.merge(labels, on="hex_id", validate="1:1").merge(feats, on="hex_id", validate="1:1").copy()
    df["log_bike"] = np.log1p(df[LABEL])
    df["bike_km"] = df[LABEL] / 1000
    return df


def cv_generic(df, features, make, fit_target, folds, proba=False):
    """Same folds as cross_validate, for models that are not the toilet forest."""
    X, y = df[features].to_numpy(), df[fit_target].to_numpy()
    pred = np.zeros(len(df))
    for k in range(N_FOLDS):
        tr, te = folds != k, folds == k
        model = make().fit(X[tr], y[tr])
        pred[te] = model.predict_proba(X[te])[:, 1] if proba else model.predict(X[te])
    return pred


def rf_classifier(seed=0):
    return RandomForestClassifier(n_estimators=300, min_samples_leaf=20, max_features=0.5, n_jobs=-1,
                                  random_state=seed)


def hgb_poisson(seed=0):
    return HistGradientBoostingRegressor(loss="poisson", max_iter=400, learning_rate=0.05,
                                         min_samples_leaf=40, l2_regularization=1.0, random_state=seed)


def evaluate(name, df, score, length_pred=None, folds=None):
    """Ranking metrics on has_bike for every model; length metrics when the model predicts metres."""
    actual = df[HAS].to_numpy()
    row = dict(model=name, pr_auc=average_precision_score(actual, score),
               top100=top_hits(score, actual, 100), top1000=top_hits(score, actual, 1000),
               spearman_len=spearmanr(score, df[LABEL]).statistic)
    if folds is not None:
        per = [average_precision_score(actual[folds == k], score[folds == k]) for k in range(N_FOLDS)]
        row.update(pr_auc_fold_min=min(per), pr_auc_fold_max=max(per))
    if length_pred is not None:
        lp = np.clip(length_pred, 1e-6, None)
        row.update(pred_km=lp.sum() / 1000, actual_km=df[LABEL].sum() / 1000,
                   deviance_km=mean_poisson_deviance(df["bike_km"], lp / 1000),
                   candidates=int(((lp - df[LABEL]) >= GAP_M).sum()))
    return row


def missing_link(hexes, has):
    """A hex with no lane whose lane-bearing neighbours are on two separate sides: it would join them."""
    lane = dict(zip(hexes, has))
    out = []
    for h, own in zip(hexes, has):
        if own:
            out.append(False)
            continue
        on = [bool(lane.get(n, 0)) for n in h3.grid_ring(h, 1)]  # the 6 neighbours, in order around the hex
        runs = sum(1 for i in range(6) if on[i] and not on[i - 1])  # separate groups of lane neighbours
        out.append(runs >= 2)
    return np.array(out)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    df = load()
    folds = spatial_folds(df)
    actual = df[HAS].to_numpy()
    print(f"hexes {len(df)}, with lane {actual.sum()} ({actual.mean():.3f}), total km {df[LABEL].sum() / 1000:.0f}")

    rows, preds = [], {}

    # Baselines
    pop_pred, _, _ = cross_validate(df, POPULATION_ONLY, LABEL, 0, folds=folds)
    rows.append(evaluate("baseline: forest on population only", df, pop_pred, pop_pred, folds))
    for name, score in [("baseline: rank by population_500m", df["population_500m"]),
                        ("baseline: rank by road length within 600 m", df["road_drivable_600m_m"]),
                        ("baseline: rank by closeness to CBD", -df["distance_cbd_km"])]:
        rows.append(evaluate(name, df, score.to_numpy(), folds=folds))

    # (a) the toilet recipe as is: RF regression on length, and on log length
    for fs in ["toilet_v12", "toilet_v12_nowalk", "bike", "bike_cbd", "bike_ring", "bike_disk"]:
        p, _, _ = cross_validate(df, FEATURE_SETS[fs], LABEL, 0, folds=folds)
        preds[f"rf_len_{fs}"] = p
        rows.append(evaluate(f"(a) RF length, {fs}", df, p, p, folds))
    for fs in ["bike", "bike_cbd"]:
        p, _, _ = cross_validate(df, FEATURE_SETS[fs], "log_bike", 0, folds=folds)
        preds[f"rf_loglen_{fs}"] = np.expm1(p)
        rows.append(evaluate(f"(a) RF log length, {fs}", df, p, np.expm1(p), folds))

    # (b) classification: any lane in the hex
    for fs in ["toilet_v12", "bike", "bike_cbd", "bike_ring"]:
        p = cv_generic(df, FEATURE_SETS[fs], rf_classifier, HAS, folds, proba=True)
        preds[f"rf_cls_{fs}"] = p
        rows.append(evaluate(f"(b) RF classifier, {fs}", df, p, folds=folds))

    # (c1) Poisson gradient boosting on length (log link, so it cannot predict negative metres)
    for fs in ["bike", "bike_cbd"]:
        p = cv_generic(df, FEATURE_SETS[fs], hgb_poisson, LABEL, folds)
        preds[f"hgb_poisson_{fs}"] = p
        rows.append(evaluate(f"(c) HGB Poisson length, {fs}", df, p, p, folds))

    metrics = pd.DataFrame(rows)
    metrics.to_csv(OUT / "metrics.csv", index=False)
    pd.DataFrame(preds).assign(hex_id=df["hex_id"], fold=folds).to_csv(OUT / "all_oof_predictions.csv.gz",
                                                                       index=False, float_format="%.4f")
    print(metrics.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
