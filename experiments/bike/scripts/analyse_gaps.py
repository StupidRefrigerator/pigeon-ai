"""Gap lists and checks for the bike models, from the held-out predictions of run_experiments.py.

Usage: python -I analyse_gaps.py BEST_LENGTH_MODEL BEST_CLASSIFIER
  e.g. python -I analyse_gaps.py rf_len_bike rf_cls_bike
Writes experiments/bike/out/: best_predictions.csv (map-ready, every study hex), top100_gaps.csv,
gap_checks.csv, cross_source.csv, stability.csv, feature_importance.csv.
"""
import sys
from pathlib import Path

import h3
import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_experiments import (FEATURE_SETS, GAP_M, LABEL, OUT, cross_validate, cv_generic, hgb_poisson, load, rf_classifier,
                             missing_link, spatial_folds)

LANE_M = 20  # a hex "has a lane" with at least 20 m


def top_gap_checks(name, df, gap, n_list=(100, 500)):
    """What sits in a model's largest gaps (hexes with no lane in either source only)."""
    no_lane = (df["existing_m"] < LANE_M).to_numpy()
    planned = (df["eval_planned_cycleway_m"] >= LANE_M).to_numpy()
    rows = []
    for n in n_list:
        order = np.argsort(-np.where(no_lane, gap, -np.inf), kind="stable")[:n]
        rows.append(dict(
            model=name, top_n=n,
            planned_cycleway=int(planned[order].sum()),
            missing_link=int(df["missing_link"].to_numpy()[order].sum()),
            mean_population_500m=float(df["population_500m"].to_numpy()[order].mean()),
            seifa_deciles_1_3=int(pd.Series(df["seifa_decile"].to_numpy()[order]).between(1, 3).sum()),
            seifa_deciles_8_10=int(pd.Series(df["seifa_decile"].to_numpy()[order]).between(8, 10).sum()),
            within_10km_cbd=int((df["distance_cbd_km"].to_numpy()[order] <= 10).sum()),
        ))
    return rows


def main(best_len, best_cls):
    df = load()
    preds = pd.read_csv(OUT / "all_oof_predictions.csv.gz")
    assert (preds["hex_id"] == df["hex_id"]).all()
    df["existing_m"] = np.maximum(df[LABEL], df["tfnsw_len_m"])
    df["missing_link"] = missing_link(df["hex_id"].tolist(), (df["existing_m"] >= LANE_M).astype(int).tolist())
    seifa = df["seifa_irsd_score"]
    df["seifa_decile"] = np.nan
    df.loc[seifa.notna(), "seifa_decile"] = pd.qcut(seifa[seifa.notna()], 10, labels=range(1, 11)).astype(int)
    no_lane = df["existing_m"] < LANE_M
    planned = df["eval_planned_cycleway_m"] >= LANE_M
    print(f"no-lane hexes {no_lane.sum()}; planned cycleway hexes {planned.sum()}, "
          f"of which no lane today {(planned & no_lane).sum()}; missing-link hexes {df['missing_link'].sum()}")

    # Gap checks: length models rank by predicted − existing metres; classifiers by P(lane).
    checks = []
    base = (planned & no_lane).sum() / no_lane.sum()
    checks.append(dict(model="random no-lane hexes (expected)", top_n=100, planned_cycleway=round(100 * base, 1)))
    for col in preds.columns:
        if col in ("hex_id", "fold"):
            continue
        score = preds[col].to_numpy()
        gap = score - df["existing_m"].to_numpy() if not col.startswith("rf_cls") else score
        checks += top_gap_checks(col, df, gap)
    pop_rank = df["population_500m"].to_numpy().astype(float)
    checks += top_gap_checks("baseline population_500m", df, pop_rank)
    checks += top_gap_checks("baseline road length 600 m", df, df["road_drivable_600m_m"].to_numpy())
    checks += top_gap_checks("baseline closeness to CBD", df, -df["distance_cbd_km"].to_numpy())
    # Network-aware: only hexes that would join two separate groups of lane neighbours, ranked by P(lane)
    ml = df["missing_link"].to_numpy()
    checks += top_gap_checks(f"missing link ranked by {best_cls}", df, np.where(ml, preds[best_cls], -1.0))
    pd.DataFrame(checks).to_csv(OUT / "gap_checks.csv", index=False)

    # Second source: of the top-100 hexes with no OSM lane, how many TfNSW already has (the toilets'
    # "OSM toilet already in the hex" check). Then the candidate count once both sources count as existing.
    rows = []
    no_osm = (df[LABEL] < LANE_M).to_numpy()
    has_tf = (df["tfnsw_len_m"] >= LANE_M).to_numpy()
    rows.append(dict(rule="random no-OSM-lane hex (expected per 100)", top100_with_tfnsw_lane=100 * has_tf[no_osm].mean()))
    for col in dict.fromkeys([best_len, best_cls, "rf_len_bike", "hgb_poisson_bike", "rf_len_toilet_v12"]):
        top = np.argsort(-np.where(no_osm, preds[col], -np.inf), kind="stable")[:100]
        rows.append(dict(rule=f"{col}: top 100 no-OSM-lane hexes", top100_with_tfnsw_lane=int(has_tf[top].sum())))
    for name, existing in [("existing = OSM only", df[LABEL]), ("existing = max(OSM, TfNSW)", df["existing_m"])]:
        rows.append(dict(rule=f"{best_len}: candidates (gap >= {GAP_M} m), {name}",
                         candidates=int((preds[best_len].to_numpy() - existing.to_numpy() >= GAP_M).sum())))
    # Held-out predictions (trained on the OSM label) scored against the TfNSW label
    for col in [best_len, best_cls]:
        rows.append(dict(rule=f"{col}: PR-AUC vs OSM label",
                         pr_auc=average_precision_score(df["has_bike"], preds[col])))
        rows.append(dict(rule=f"{col}: PR-AUC vs TfNSW label",
                         pr_auc=average_precision_score(df["tfnsw_len_m"] >= LANE_M, preds[col])))
    rows.append(dict(rule="TfNSW label as a ranking of the OSM label (agreement ceiling)",
                     pr_auc=average_precision_score(df["has_bike"], df["tfnsw_len_m"])))
    pd.DataFrame(rows).to_csv(OUT / "cross_source.csv", index=False)

    # Stability of each leading model's top-100 gap list (no-lane hexes only) across seeds 0-2
    folds = spatial_folds(df)

    def refit(name, seed):
        fs = name.split("_", 2)[-1]
        if name.startswith("hgb_poisson"):
            return cv_generic(df, FEATURE_SETS[fs], lambda: hgb_poisson(seed), LABEL, folds)
        if name.startswith("rf_cls"):
            return cv_generic(df, FEATURE_SETS[fs], lambda: rf_classifier(seed), "has_bike", folds, proba=True)
        return cross_validate(df, FEATURE_SETS[fs], LABEL, seed, folds=folds)[0]

    def top100(name, p):
        g = p - df["existing_m"].to_numpy() if not name.startswith("rf_cls") else p
        return set(np.argsort(-np.where(no_lane, g, -np.inf), kind="stable")[:100])
    stab = []
    for name in dict.fromkeys([best_len, best_cls, "rf_len_bike", "hgb_poisson_bike"]):
        ref = top100(name, preds[name].to_numpy())
        stab += [dict(model=name, seed=seed, top100_in_common_with_seed0=len(ref & top100(name, refit(name, seed))))
                 for seed in (1, 2)]
    pd.DataFrame(stab).to_csv(OUT / "stability.csv", index=False)
    features = FEATURE_SETS["bike"]

    # Importance in metres from the RF length model on the same features (mean |SHAP|, held-out rows)
    _, _, shap_values = cross_validate(df, features, LABEL, 0, with_shap=True, folds=folds)
    imp = pd.DataFrame({"feature": features, "mean_abs_shap_m": np.abs(shap_values).mean(axis=0)})
    imp.sort_values("mean_abs_shap_m", ascending=False).round(2).to_csv(OUT / "feature_importance.csv", index=False)

    # Map-ready file for every study hex, and the top 100 gaps
    lat, lng = zip(*[h3.cell_to_latlng(h) for h in df["hex_id"]])
    best = pd.DataFrame({
        "hex_id": df["hex_id"], "lat": np.round(lat, 5), "lng": np.round(lng, 5), "fold": folds,
        "osm_bike_m": df[LABEL], "osm_separated_m": df["bike_separated_m"], "osm_shared_path_m": df["bike_shared_path_m"],
        "osm_painted_m": df["bike_painted_m"], "tfnsw_bike_m": df["tfnsw_len_m"], "existing_m": df["existing_m"],
        "predicted_m": preds[best_len], "p_lane": preds[best_cls], "hgb_predicted_m": preds["hgb_poisson_bike"],
        "gap_m": (preds[best_len] - df["existing_m"]).clip(lower=0),
        "missing_link": df["missing_link"], "planned_cycleway_m": df["eval_planned_cycleway_m"],
        "seifa_decile": df["seifa_decile"],
    })
    best["is_candidate"] = best["gap_m"] >= GAP_M
    best.round(3).to_csv(OUT / "best_predictions.csv", index=False)
    top = best[no_lane.to_numpy()].sort_values("gap_m", ascending=False, kind="stable").head(100)
    top.insert(0, "rank", range(1, 101))
    top.round(3).to_csv(OUT / "top100_gaps.csv", index=False)
    print(pd.DataFrame(checks).round(2).to_string(index=False))
    print(pd.DataFrame(rows).round(3).to_string(index=False))
    print(pd.DataFrame(stab).to_string(index=False))
    print(imp.sort_values("mean_abs_shap_m", ascending=False).head(15).round(2).to_string(index=False))
    print(f"candidates (gap >= {GAP_M} m, existing = max of sources): {int(best['is_candidate'].sum())}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
