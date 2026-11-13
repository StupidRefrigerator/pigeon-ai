"""Build the data behind the internal Tracking (/app/stats) and Tests (/app/tests) pages.

Run from anywhere:  /tmp/pigeon-env/bin/python app/scripts/build_data.py

Writes, all committed:
  src/data/tracking.json  version history V1-V12 and the V12 headline (bundled)
  src/data/stats.json     the four answers on the Tests page (bundled)
  public/heatmap.json     per-hex results for the Tracking-page map (fetched at runtime)

Model numbers are V12 (M1 in experiments/v2/combos): seed-mean metrics from
experiments/v2/combos/out, per-hex values from data/model (seed 0). The default
list is ranked by gap only, with no weighting.
"""
import json
import math
from pathlib import Path

import h3
import numpy as np
import pandas as pd

APP = Path(__file__).resolve().parents[1]
REPO = APP.parent
V2 = REPO / "experiments/v2/combos/out"


def r(x, n=3):
    return None if pd.isna(x) else round(float(x), n)


def ratio(x, y):
    return {"x": int(x), "y": int(y), "pct": round(100 * x / y)}


def parse_ratio(s):
    x, y = (int(v) for v in s.split("/"))
    return ratio(x, y)


# ---------- V12 metrics (mean of seeds 0-2) ----------
sm = pd.read_csv(V2 / "study_metrics.csv", header=[0, 1], index_col=[0, 1, 2])


def study(model):
    row = sm.loc[("official", "all", model)]
    return {k: row[(k, "mean")] for k in ["pr_auc", "top100", "top1000", "deviance", "pred_total", "actual_total"]}


m0, m1 = study("M0"), study("M1")
assert (r(m0["pr_auc"]), r(m1["pr_auc"])) == (0.52, 0.569)
summ = pd.read_csv(V2 / "summary_table.csv").set_index(["model", "post-processing"])
v12 = summ.loc[("M1 +F", "P0 none")]
chosen = summ.loc[("M1, OSM fix after model", "P0 none")]  # the default list: OSM fix, gap only

hexes = pd.read_csv(REPO / "data/model/hex_predictions.csv")
recs = pd.read_csv(REPO / "data/model/recommendations.csv").sort_values("rank")
assert len(hexes) == 16228 and len(recs) == 100
assert (recs.priority == recs.gap).all(), "the default list must be ranked by gap only"
n_hex = len(hexes)
toilet_hexes = int((hexes.toilet_count > 0).sum())
base_rate = toilet_hexes / n_hex

# ---------- the default list's top 120 (seed 0) ----------
picks = pd.read_csv(V2 / "picks_top120_seed0.csv")
picks = picks[(picks.model == "M1+postL") & (picks.post == "P0")]
assert len(picks) == 120 and set(recs.hex_id) <= set(picks.hex_id)
poor = int(picks.seifa_decile.between(1, 3).sum())
rich = int(picks.seifa_decile.between(8, 10).sum())
pick_counts = {
    "listed": int((picks.gap >= 1).sum()),
    "osmAlready": ratio((picks.osm_toilets_public > 0).sum(), 120),
    "nearPlanned": ratio(picks.near_planned.sum(), 120),
    "poorest30": ratio(poor, 120),
    "richest30": ratio(rich, 120),
}
assert pick_counts["listed"] == len(recs) == parse_ratio(chosen["picks gap ≥ 1"])["x"]
assert pick_counts["osmAlready"] == parse_ratio(chosen["OSM toilet already"])
assert pick_counts["nearPlanned"] == parse_ratio(chosen["near planned site"])
assert chosen["deciles 1–3 / 8–10"] == f"{poor} / {rich}"

# ---------- tracking.json ----------
jimmy = json.load(open(APP / "scripts/curated_stats.json"))["versions_jimmy"]
versions = [
    {"id": v, "description": d, "hexes": h, "features": f, "deviance": dev, "prAuc": pa, "top100": t,
     "status": "pending" if pa is None else "done"}
    for v, d, h, f, dev, pa, t in jimmy["rows"]
] + [
    {"id": "V11", "description": "V5 + V6 combined: baseline, 1 km surroundings and accessibility", "hexes": n_hex, "features": 28,
     "deviance": r(m0["deviance"], 4), "prAuc": r(m0["pr_auc"], 4), "top100": round(m0["top100"]), "status": "done"},
    {"id": "V12", "description": "V11 + sports fields, playgrounds and beaches", "hexes": n_hex, "features": 45,
     "deviance": r(m1["deviance"], 4), "prAuc": r(m1["pr_auc"], 4), "top100": round(m1["top100"]), "status": "current"},
]
tracking = {
    "versions": versions,
    "current": {
        "id": "V12",
        "prAuc": {"value": r(m1["pr_auc"]), "was": r(m0["pr_auc"]), "random": r(base_rate)},
        "deviance": {"value": r(m1["deviance"]), "was": r(m0["deviance"])},
        "top1000": {"x": round(m1["top1000"]), "y": 1000, "pct": round(m1["top1000"] / 10, 1)},
        "council": parse_ratio(v12["council top 10%"]),
        "predictedTotal": round(m1["pred_total"]), "actualTotal": int(m1["actual_total"]),
        "picks": pick_counts,
    },
}

# ---------- stats.json: the four Tests-page answers ----------
gm = pd.read_csv(V2 / "growth_metrics.csv", header=[0, 1], index_col=[0, 1]).loc[("official", "M1")]
growth_pred = pd.read_csv(V2 / "growth_predictions.csv")
assert int(gm[("toilet_hexes", "mean")]) == int((growth_pred.toilet_count > 0).sum())
g_hexes, g_toilet_hexes = len(growth_pred), int(gm[("toilet_hexes", "mean")])
assert parse_ratio(v12["growth found"]) == ratio(round(gm[("found_top100", "mean")]), g_toilet_hexes)

fair = pd.read_csv(REPO / "data/model/fairness.csv")
fair = fair[fair.group != "unknown"].assign(decile=lambda d: d.group.astype(int)).set_index("decile")
feat = pd.read_csv(REPO / "data/processed/sydney_extended_features.csv",
                   usecols=["hex_id", "toilet_count", "population_est", "seifa_irsd_score"])
known = feat.seifa_irsd_score.notna()
feat.loc[known, "decile"] = pd.qcut(feat.loc[known, "seifa_irsd_score"], 10, labels=False) + 1  # 1 = most disadvantaged
by_dec = feat.groupby("decile").agg(hexes=("hex_id", "size"), toilets=("toilet_count", "sum"), pop=("population_est", "sum"))
by_dec.index = by_dec.index.astype(int)
assert (by_dec.hexes == fair.hexes).all() and (by_dec.toilets == fair.actual_toilets).all(), "deciles differ from fairness.csv"

stats = {
    "find": {
        "hexes": n_hex, "toiletHexes": toilet_hexes,
        "top100": ratio(round(m1["top100"]), 100),
        "top1000": tracking["current"]["top1000"],
        "prAuc": r(m1["pr_auc"]), "random": r(base_rate),
    },
    "council": {"top10": tracking["current"]["council"], "random": round(0.1 * tracking["current"]["council"]["y"])},
    "growth": {
        "hexes": g_hexes, "toiletHexes": g_toilet_hexes,
        "top100": parse_ratio(v12["growth found"]),
        "randomTop100": round(100 * g_toilet_hexes / g_hexes),
        "prAuc": r(gm[("pr_auc", "mean")]), "random": r(g_toilet_hexes / g_hexes),
        "predicted": round(gm[("pred_total", "mean")]), "actual": int(gm[("actual_total", "mean")]),
    },
    "reach": {
        "poorest30": pick_counts["poorest30"], "richest30": pick_counts["richest30"],
        "deciles": [
            {"decile": d, "real": int(fair.loc[d, "actual_toilets"]), "predicted": round(float(fair.loc[d, "predicted_toilets"])),
             "per10k": r(by_dec.loc[d, "toilets"] / by_dec.loc[d, "pop"] * 1e4, 2)}
            for d in range(1, 11)
        ],
    },
}
assert stats["reach"]["deciles"][0]["real"] == 274 and stats["reach"]["deciles"][0]["per10k"] == 4.1
assert stats["growth"]["predicted"] == round(float(v12["growth predicted (39)"]))

# ---------- public/heatmap.json ----------
places = json.load(open(REPO / "data/reference/sydney_places.json"))["places"]
p_names = [n.replace(" (NSW)", "") for n in places]
p_ll = np.radians(np.array(list(places.values())))


def nearest_place(ids):
    """Index into p_names of the place nearest each hex centre."""
    ll = np.radians(np.array([h3.cell_to_latlng(h) for h in ids]))
    k = np.cos(ll[:, :1])
    d = (ll[:, None, 0] - p_ll[None, :, 0]) ** 2 + ((ll[:, None, 1] - p_ll[None, :, 1]) * k) ** 2
    return d.argmin(axis=1).tolist()


feats, feat_ix = [], {}


def enc_drivers(s):
    """'shop_250m +0.12; food_inside -0.02' -> '3:0.12,7:-0.02' with names in `feats`."""
    if not isinstance(s, str) or not s:
        return ""
    out = []
    for part in s.split(";"):
        f, v = part.strip().rsplit(" ", 1)
        if f not in feat_ix:
            feat_ix[f] = len(feats)
            feats.append(f)
        out.append(f"{feat_ix[f]}:{float(v):g}")
    return ",".join(out)


today = [[h.hex_id, int(h.toilet_count), r(h.predicted_toilets), r(h.p_any_toilet), enc_drivers(h.top_drivers), pl]
         for h, pl in zip(hexes.itertuples(), nearest_place(hexes.hex_id))]
rec_rows = [[h.hex_id, int(h.rank), r(h.gap), int(h.osm_toilets_public)] for h in recs.itertuples()]
growth = [[h.hex_id, int(h.toilet_count), r(h.M1_s0), r(1 - math.exp(-h.M1_s0)), pl]
          for h, pl in zip(growth_pred.itertuples(), nearest_place(growth_pred.hex_id))]
fut = pd.read_csv(V2 / "future_top10.csv")
fut = fut[(fut.model == "M1") & (fut.f_scenario == "planned_re1")].sort_values(["area", "rank"])
assert fut.groupby("area").size().to_dict() == {"aerotropolis": 10, "leppington": 10}
future = [[f.area, int(f.rank), f.hex_id, r(f.pred), r(1 - math.exp(-f.pred)), f.zone, f.nearest_station, int(f.station_dist_m),
           enc_drivers(f.drivers)] for f in fut.itertuples()]
heatmap = {"feats": feats, "places": p_names, "today": today, "recs": rec_rows, "growth": growth, "future": future}

out = {
    APP / "src/data/tracking.json": json.dumps(tracking, indent=1, ensure_ascii=False),
    APP / "src/data/stats.json": json.dumps(stats, indent=1, ensure_ascii=False),
    APP / "public/heatmap.json": json.dumps(heatmap, separators=(",", ":"), ensure_ascii=False),
}
for path, text in out.items():
    path.write_text(text)
    print(f"{path.relative_to(APP)}: {path.stat().st_size / 1024:.0f} KB")
