"""Bradfield / Aerotropolis and Leppington: v1-family models trained on all study hexes, applied to the
planned-scenario features (v1 part: experiments/future, scenario dphi2041|shops_mid|bus_calibrated;
F part: pigeon-v2/data/new_features_future_planned.csv)."""
import numpy as np
import pandas as pd
import shap

from common import MODELS, OUT, REPO, SEEDS, V2, F, features, label, load_study, make_forest

V1_SCEN = "dphi2041|shops_mid|bus_calibrated"
F_SCENS = ("planned_re1", "planned_re1_enz", "current_osm")
BRADFIELD = "89be0856407ffff"
VARIANTS = ["M0", "M1", "M2", "M3"]

study = load_study()
fp = pd.read_csv(V2 / "data/new_features_future_planned.csv")
today_v1 = pd.read_csv(REPO / "data/processed/sydney_all_features.csv").set_index("hex_id")
models = {}
for name in VARIANTS:
    with_f, lab = MODELS[name]
    feats = features("v1", with_f)
    for seed in SEEDS:
        models[name, seed] = (feats, make_forest(seed).fit(study[feats].to_numpy(), label(study, lab)))

summary, tops = [], []
for area, key in (("aerotropolis", "aero"), ("leppington", "leppington")):
    v1 = pd.read_csv(REPO / f"experiments/future/{key}_features.csv")
    v1 = v1[v1.scenario == V1_SCEN].drop(columns="scenario").set_index("hex_id")
    lab = pd.read_csv(REPO / f"experiments/future/{key}_predictions.csv")
    lab = lab[(lab.scenario == V1_SCEN) & (lab.model == "baseline")].set_index("hex_id")[
        ["zone", "role", "nearest_station", "station_dist_m"]]
    for fs in F_SCENS + ("today",):
        if fs == "today":
            X = today_v1.loc[v1.index].join(fp[(fp.scenario == "current_osm")].set_index("hex_id")[F])
        else:
            X = v1.join(fp[(fp.scenario == fs)].set_index("hex_id")[F])
        assert X[F].notna().all().all() and len(X) == len(v1)
        for name in VARIANTS:
            if fs != "planned_re1" and fs != "today" and not MODELS[name][0]:
                continue  # F scenario only matters for +F models
            totals, firsts = [], []
            for seed in SEEDS:
                feats, m = models[name, seed]
                p = pd.Series(m.predict(X[feats].to_numpy()), index=X.index)
                totals.append(p.sum())
                firsts.append(p.idxmax())
                if seed == 0:
                    p0 = p
            rank_b = int((p0 > p0.get(BRADFIELD, np.nan)).sum() + 1) if BRADFIELD in p0.index else None
            summary.append(dict(area=area, f_scenario=fs, model=name, total_s0=p0.sum(), total_mean=np.mean(totals),
                                total_min=min(totals), total_max=max(totals), hexes_ge1=int((p0 >= 1).sum()),
                                top1_hex=p0.idxmax(), top1_is_bradfield=p0.idxmax() == BRADFIELD,
                                bradfield_rank=rank_b, bradfield_pred=p0.get(BRADFIELD, np.nan),
                                top1_bradfield_all_seeds=all(h == BRADFIELD for h in firsts)))
            if fs in ("planned_re1", "planned_re1_enz") or (fs == "planned_re1" and not MODELS[name][0]):
                feats, m = models[name, 0]
                top = p0.nlargest(10)
                sv = shap.TreeExplainer(m).shap_values(X.loc[top.index, feats].to_numpy())
                for i, (h, v) in enumerate(top.items()):
                    idx = np.argsort(-np.abs(sv[i]), kind="stable")[:3]
                    tops.append(dict(area=area, f_scenario=fs, model=name, rank=i + 1, hex_id=h, pred=v,
                                     **lab.loc[h].to_dict(),
                                     drivers="; ".join(f"{feats[j]} {sv[i][j]:+.2f}" for j in idx)))
s = pd.DataFrame(summary)
s.to_csv(OUT / "future_summary.csv", index=False)
pd.DataFrame(tops).to_csv(OUT / "future_top10.csv", index=False)
print(s.round(2).to_string())
