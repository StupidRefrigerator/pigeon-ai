"""Seed-mean study scores, the growth-suburbs test and the future-area top 10s for one target.

The same method as the toilet runs in experiments/v2/combos (study_cv.py, growth.py, future.py, model M1):
  study   five-fold spatial CV on the V12 inputs, seeds 0-2
  growth  train on every study hexagon with the V1 inputs plus the 17 V12 OSM columns (the growth
          and future feature files have no accessibility columns), predict the 1,108 growth hexagons
  future  the same model on Bradfield (Aerotropolis) and Leppington as planned
          (scenario dphi2041|shops_mid|bus_calibrated, OSM columns planned_re1); top 10 per area, seed 0

Usage: PYTHONPATH=src python experiments/bubblers/growth_future.py [--target bubblers] [--out-dir DIR]
--target toilets reproduces the committed toilet numbers, as a check of the method.
Needs experiments/future/aero_features.csv and aero_predictions.csv (DATA.md, Experiment outputs).
"""
from pathlib import Path
import argparse

import numpy as np
import pandas as pd
import shap
from sklearn.metrics import average_precision_score, mean_poisson_deviance

from pigeon_ai import model
from pigeon_ai.paths import PROCESSED, ROOT
from pigeon_ai.recreation import RECREATION_FEATURES

HERE = Path(__file__).resolve().parent
V1_SCEN = "dphi2041|shops_mid|bus_calibrated"
F_SCEN = "planned_re1"
FUTURE = {"aerotropolis": "aero", "leppington": "leppington"}


def score(y, p):
    p = np.clip(p, model.MIN_PREDICTION, None)
    top = np.argsort(-p, kind="stable")
    return dict(deviance=mean_poisson_deviance(y, p), pr_auc=average_precision_score(y > 0, p),
                top100=int((y[top[:100]] > 0).sum()), top1000=int((y[top[:1000]] > 0).sum()),
                pred_total=p.sum(), actual_total=int(y.sum()), hexes_with=int((y > 0).sum()))


def with_mean(rows):
    df = pd.DataFrame(rows)
    return pd.concat([df, df.drop(columns="seed").mean().to_frame().T.assign(seed="mean")], ignore_index=True)


def growth_hexes(target, study_ids):
    g = pd.read_csv(PROCESSED / "sydney_growth_features.csv")
    g = g[~g.hex_id.isin(study_ids)].reset_index(drop=True)
    g = g.merge(pd.read_csv(PROCESSED / "sydney_growth_recreation_features.csv"), on="hex_id", how="left", validate="1:1")
    if target.label_file is not None:
        labels = pd.read_csv(target.label_file).query("area == 'growth'")[["hex_id", target.label]]
        g = g.merge(labels, on="hex_id", how="left", validate="1:1")
    assert len(g) == 1108 and g[target.label].notna().all()
    return g


def future_features(key):
    v1 = pd.read_csv(ROOT / f"experiments/future/{key}_features.csv")
    v1 = v1[v1.scenario == V1_SCEN].drop(columns="scenario").set_index("hex_id")
    f = pd.read_csv(ROOT / "experiments/v2/data/new_features_future_planned.csv")
    X = v1.join(f[f.scenario == F_SCEN].set_index("hex_id")[RECREATION_FEATURES])
    assert X[RECREATION_FEATURES].notna().all().all()
    where = pd.read_csv(ROOT / f"experiments/future/{key}_predictions.csv")
    where = where[(where.scenario == V1_SCEN) & (where.model == "baseline")].set_index("hex_id")
    return X, where[["zone", "role", "nearest_station", "station_dist_m"]]


def main(target_name, out_dir):
    target = model.TARGETS[target_name]
    label = target.label
    out_dir.mkdir(parents=True, exist_ok=True)
    study = model.load_data(label_file=target.label_file)
    y = study[label].to_numpy()

    v12 = target.feature_sets["v12"]
    rows = []
    for seed in model.SEEDS:
        pred, _, _ = model.cross_validate(study, v12, label, seed)
        rows.append(dict(seed=seed, **score(y, pred)))
        print("study", seed, {k: round(v, 3) for k, v in rows[-1].items()}, flush=True)
    study_metrics = with_mean(rows)
    study_metrics["mean_everywhere_deviance"] = mean_poisson_deviance(y, np.full(len(y), y.mean()))
    study_metrics.to_csv(out_dir / "study_metrics.csv", index=False)

    growth_features = model.TARGETS["toilets"].feature_sets["v1"] + RECREATION_FEATURES
    growth = growth_hexes(target, set(study.hex_id))
    gy = growth[label].to_numpy()
    forests, rows = {}, []
    preds = pd.DataFrame({"hex_id": growth.hex_id, label: gy})
    for seed in model.SEEDS:
        forests[seed] = model.make_forest(seed).fit(study[growth_features].to_numpy(), y)
        preds[f"M1_s{seed}"] = forests[seed].predict(growth[growth_features].to_numpy())
        rows.append(dict(seed=seed, **score(gy, preds[f"M1_s{seed}"].to_numpy())))
        print("growth", seed, {k: round(v, 3) for k, v in rows[-1].items()}, flush=True)
    with_mean(rows).to_csv(out_dir / "growth_metrics.csv", index=False)
    preds.to_csv(out_dir / "growth_predictions.csv", index=False)

    tops = []
    for area, key in FUTURE.items():
        X, where = future_features(key)
        top = pd.Series(forests[0].predict(X[growth_features].to_numpy()), index=X.index).nlargest(10)
        sv = shap.TreeExplainer(forests[0]).shap_values(X.loc[top.index, growth_features].to_numpy())
        for i, (h, v) in enumerate(top.items()):
            idx = np.argsort(-np.abs(sv[i]), kind="stable")[:3]
            tops.append(dict(area=area, rank=i + 1, hex_id=h, pred=v, **where.loc[h].to_dict(),
                             drivers="; ".join(f"{growth_features[j]} {sv[i][j]:+.2f}" for j in idx)))
    future = pd.DataFrame(tops)
    future.to_csv(out_dir / "future_top10.csv", index=False)
    print(future[["area", "rank", "hex_id", "pred", "zone", "nearest_station"]].round(3).to_string(index=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--target", default="bubblers", choices=list(model.TARGETS))
    parser.add_argument("--out-dir", type=Path, default=HERE / "out")
    args = parser.parse_args()
    main(args.target, args.out_dir)
