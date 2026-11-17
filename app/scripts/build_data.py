"""Build the data behind the map (/app), Tracking (/app/stats) and Tests (/app/tests) pages.

Run from anywhere:  python app/scripts/build_data.py --target toilets|bubblers

Writes, all committed, for the target layer (default toilets):
  src/data/infra/<target>/tracking.json  version history and the current model's headline (bundled)
  src/data/infra/<target>/stats.json     the answers on the Tests page (bundled)
  public/infra/<target>/heatmap.json     per-hex results for the maps (fetched at runtime)

Toilets are V12 (M1 in experiments/v2/combos): seed-mean metrics from experiments/v2/combos/out,
per-hex values from data/model (seed 0). Water fountains are B1, the same model on their own label:
seed-mean metrics, growth and future areas from experiments/bubblers/out, per-hex values from
data/model/bubblers (seed 0). Each list is every hexagon short of at least one unit, ranked by gap only.
"""
import argparse
import json
import math
import sys
from pathlib import Path

import h3
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from pigeon_ai.postprocess import seifa_disadvantage  # noqa: E402

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


places = json.load(open(REPO / "data/reference/sydney_places.json"))["places"]
p_names = [n.replace(" (NSW)", "") for n in places]
p_ll = np.radians(np.array(list(places.values())))


def nearest_place(ids):
    """Index into p_names of the place nearest each hex centre."""
    ll = np.radians(np.array([h3.cell_to_latlng(h) for h in ids]))
    k = np.cos(ll[:, :1])
    d = (ll[:, None, 0] - p_ll[None, :, 0]) ** 2 + ((ll[:, None, 1] - p_ll[None, :, 1]) * k) ** 2
    return d.argmin(axis=1).tolist()


class DriverCodes:
    """Driver strings packed against one shared list of feature names, in first-seen order."""

    def __init__(self):
        self.feats, self.index = [], {}

    def encode(self, s):
        """'shop_250m +0.12; food_inside -0.02' -> '3:0.12,7:-0.02' with names in `feats`."""
        if not isinstance(s, str) or not s:
            return ""
        out = []
        for part in s.split(";"):
            f, v = part.strip().rsplit(" ", 1)
            if f not in self.index:
                self.index[f] = len(self.feats)
                self.feats.append(f)
            out.append(f"{self.index[f]}:{float(v):g}")
        return ",".join(out)


def build_toilets():
    """V12 toilets: the four Tests-page answers, council sites and the OSM-corrected growth test."""
    codes = DriverCodes()
    # V12 metrics (mean of seeds 0-2)
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

    # the suggested list (seed 0)
    # The list is every hexagon where the model expects at least one more toilet than exist,
    # counting official-map and OpenStreetMap toilets as existing. It is not capped at a fixed length.
    assert (recs.existing_toilets == recs[["toilet_count", "osm_toilets_public"]].max(axis=1)).all()
    assert (recs.gap >= 1).all() and np.allclose(recs.gap, recs.predicted_toilets - recs.existing_toilets, atol=1e-3)
    # Cross-check against the saved top 120 of the same run: exactly the listed hexagons have gap >= 1.
    picks = pd.read_csv(V2 / "picks_top120_seed0.csv")
    picks = picks[(picks.model == "M1+postL") & (picks.post == "P0")]
    assert len(picks) == 120 and set(picks[picks.gap >= 1].hex_id) == set(recs.hex_id)
    assert parse_ratio(chosen["picks gap ≥ 1"])["x"] == len(recs)
    listed = picks[picks.hex_id.isin(recs.hex_id)].set_index("hex_id").loc[recs.hex_id]
    assert (listed.seifa_decile.fillna(0).to_numpy() == recs.seifa_decile.fillna(0).to_numpy()).all()
    n_list = len(recs)
    has_one = recs[recs.existing_toilets > 0]
    assert (has_one.existing_toilets == 1).all() and (has_one.predicted_toilets >= 2).all()
    pick_counts = {
        "listed": n_list,
        "alreadyOne": ratio(len(has_one), n_list),
        "nearPlanned": ratio(listed.near_planned.sum(), n_list),
        "poorest30": ratio(recs.seifa_decile.between(1, 3).sum(), n_list),
        "richest30": ratio(recs.seifa_decile.between(8, 10).sum(), n_list),
        "noSeifa": int(recs.seifa_decile.isna().sum()),
    }

    # tracking.json
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

    # stats.json: the four Tests-page answers
    growth_metrics = pd.read_csv(V2 / "growth_metrics.csv", header=[0, 1], index_col=[0, 1])
    gm = growth_metrics.loc[("official", "M1")]
    gm_osm = growth_metrics.loc[("osm_corrected", "M1")]  # OpenStreetMap toilets count as real too
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
            "withOsm": {
                "toiletHexes": int(gm_osm[("toilet_hexes", "mean")]),
                "top100": ratio(round(gm_osm[("found_top100", "mean")]), gm_osm[("toilet_hexes", "mean")]),
                "prAuc": r(gm_osm[("pr_auc", "mean")]), "random": r(gm_osm[("toilet_hexes", "mean")] / g_hexes),
                "actual": int(gm_osm[("actual_total", "mean")]),
            },
        },
        "reach": {
            "listed": n_list, "poorest30": pick_counts["poorest30"], "richest30": pick_counts["richest30"], "noSeifa": pick_counts["noSeifa"],
            "deciles": [
                {"decile": d, "real": int(fair.loc[d, "actual_toilets"]), "predicted": round(float(fair.loc[d, "predicted_toilets"])),
                 "per10k": r(by_dec.loc[d, "toilets"] / by_dec.loc[d, "pop"] * 1e4, 2)}
                for d in range(1, 11)
            ],
        },
    }
    assert stats["reach"]["deciles"][0]["real"] == 274 and stats["reach"]["deciles"][0]["per10k"] == 4.1
    assert stats["growth"]["predicted"] == round(float(v12["growth predicted (39)"]))
    assert stats["growth"]["withOsm"]["top100"]["x"] == 31 and stats["growth"]["withOsm"]["toiletHexes"] == 48

    # heatmap.json
    today = [[h.hex_id, int(h.toilet_count), r(h.predicted_toilets), r(h.p_any_toilet), codes.encode(h.top_drivers), pl]
             for h, pl in zip(hexes.itertuples(), nearest_place(hexes.hex_id))]
    rec_rows = [[h.hex_id, int(h.rank), r(h.gap), int(h.osm_toilets_public)] for h in recs.itertuples()]
    growth = [[h.hex_id, int(h.toilet_count), r(h.M1_s0), r(1 - math.exp(-h.M1_s0)), pl]
              for h, pl in zip(growth_pred.itertuples(), nearest_place(growth_pred.hex_id))]
    fut = pd.read_csv(V2 / "future_top10.csv")
    fut = fut[(fut.model == "M1") & (fut.f_scenario == "planned_re1")].sort_values(["area", "rank"])
    assert fut.groupby("area").size().to_dict() == {"aerotropolis": 10, "leppington": 10}
    future = [[f.area, int(f.rank), f.hex_id, r(f.pred), r(1 - math.exp(-f.pred)), f.zone, f.nearest_station, int(f.station_dist_m),
               codes.encode(f.drivers)] for f in fut.itertuples()]
    heatmap = {"feats": codes.feats, "places": p_names, "today": today, "recs": rec_rows, "growth": growth, "future": future}
    return tracking, stats, heatmap


def seifa_deciles(hex_ids):
    """SEIFA IRSD decile per hexagon (1 = most disadvantaged), cut over the study hexagons as the model's fairness audit does."""
    feat = pd.read_csv(REPO / "data/processed/sydney_extended_features.csv", usecols=["hex_id", "seifa_irsd_score", "population_est"])
    feat["decile"], _ = seifa_disadvantage(feat.seifa_irsd_score)
    return feat.set_index("hex_id").loc[hex_ids]


WEST = ["PENRITH", "BLACKTOWN", "LIVERPOOL", "CAMPBELLTOWN", "FAIRFIELD", "HAWKESBURY"]


def build_bubblers():
    """B1 water fountains: V12's inputs and settings on the council-plus-OSM label. No council-planned sites."""
    codes = DriverCodes()
    out = REPO / "experiments/bubblers/out"
    sm = pd.read_csv(out / "study_metrics.csv").set_index("seed")
    mean, s0 = sm.loc["mean"].astype(float), sm.loc["0"].astype(float)
    hexes = pd.read_csv(REPO / "data/model/bubblers/hex_predictions.csv")
    seed0 = pd.read_csv(REPO / "data/model/bubblers/metrics.csv").set_index("model").loc["forest v12"]
    assert len(hexes) == 16228 and math.isclose(seed0.deviance, s0.deviance) and math.isclose(seed0.pr_auc, s0.pr_auc)
    n_hex = len(hexes)
    with_one = int((hexes.bubbler_count > 0).sum())
    base_rate = with_one / n_hex

    # The suggested list (seed 0): every hexagon where the model expects at least one more fountain
    # than exist, ranked by gap. The label already counts OSM fountains, so no fix after the model.
    recs = hexes[hexes.predicted_bubblers - hexes.bubbler_count >= 1].assign(gap=lambda d: d.predicted_bubblers - d.bubbler_count)
    recs = recs.sort_values(["gap", "hex_id"], ascending=[False, True]).reset_index(drop=True)
    recs["rank"] = recs.index + 1
    assert set(recs.hex_id) == set(hexes[hexes.is_candidate].hex_id)
    labels = pd.read_csv(REPO / "data/processed/bubbler_labels.csv").set_index("hex_id")
    seifa = seifa_deciles(hexes.hex_id)
    rec_dec = seifa.loc[recs.hex_id, "decile"]
    n_list = len(recs)
    picks = {
        "listed": n_list,
        "alreadyOne": ratio((recs.bubbler_count > 0).sum(), n_list),
        "poorest30": ratio(rec_dec.between(1, 3).sum(), n_list),
        "richest30": ratio(rec_dec.between(8, 10).sum(), n_list),
        "noSeifa": int(rec_dec.isna().sum()),
    }

    # Western councils publish few fountain records, so the label there is thin.
    west = labels.loc[hexes.hex_id, "lga"].isin(WEST).to_numpy()
    undercount = {
        "councils": [c.title() for c in WEST], "recorded": int(hexes.bubbler_count[west].sum()),
        "predicted": round(hexes.predicted_bubblers[west].sum()), "listed": int(recs.hex_id.isin(hexes.hex_id[west]).sum()),
    }

    tracking = {
        "undercount": undercount,
        "versions": [{
            "id": "B1", "description": "V12's 45 inputs and settings, trained on council and OpenStreetMap water fountains",
            "hexes": n_hex, "features": 45, "deviance": r(mean.deviance, 4), "prAuc": r(mean.pr_auc, 4),
            "top100": round(mean.top100), "status": "current",
        }],
        "current": {
            "id": "B1",
            "prAuc": {"value": r(mean.pr_auc), "random": r(base_rate)},
            "deviance": {"value": r(mean.deviance)},
            "top1000": {"x": round(mean.top1000), "y": 1000, "pct": round(mean.top1000 / 10, 1)},
            "predictedTotal": round(mean.pred_total), "actualTotal": int(mean.actual_total),
            "picks": picks,
        },
    }

    gm = pd.read_csv(out / "growth_metrics.csv").set_index("seed").loc["mean"].astype(float)
    growth_pred = pd.read_csv(out / "growth_predictions.csv")
    g_hexes, g_with = len(growth_pred), int(gm.hexes_with)
    assert g_with == int((growth_pred.bubbler_count > 0).sum())

    fair = pd.read_csv(REPO / "data/model/bubblers/fairness.csv")
    fair = fair[fair.group != "unknown"].assign(decile=lambda d: d.group.astype(int)).set_index("decile")
    by_dec = seifa.assign(count=hexes.set_index("hex_id").bubbler_count).groupby("decile").agg(
        hexes=("count", "size"), count=("count", "sum"), pop=("population_est", "sum"))
    by_dec.index = by_dec.index.astype(int)
    assert (by_dec.hexes == fair.hexes).all() and (by_dec["count"] == fair.actual_bubblers).all(), "deciles differ from fairness.csv"

    stats = {
        "find": {
            "hexes": n_hex, "toiletHexes": with_one,
            "top100": ratio(round(mean.top100), 100), "top1000": tracking["current"]["top1000"],
            "prAuc": r(mean.pr_auc), "random": r(base_rate),
        },
        "growth": {
            "hexes": g_hexes, "toiletHexes": g_with,
            "top100": ratio(round(gm.top100), g_with), "randomTop100": round(100 * g_with / g_hexes),
            "prAuc": r(gm.pr_auc), "random": r(g_with / g_hexes),
            "predicted": round(gm.pred_total), "actual": int(gm.actual_total),
        },
        "reach": {
            "listed": n_list, "poorest30": picks["poorest30"], "richest30": picks["richest30"], "noSeifa": picks["noSeifa"],
            "deciles": [
                {"decile": d, "real": int(fair.loc[d, "actual_bubblers"]), "predicted": round(float(fair.loc[d, "predicted_bubblers"])),
                 "per10k": r(by_dec.loc[d, "count"] / by_dec.loc[d, "pop"] * 1e4, 2)}
                for d in range(1, 11)
            ],
        },
    }

    today = [[h.hex_id, int(h.bubbler_count), r(h.predicted_bubblers), r(h.p_any_bubbler), codes.encode(h.top_drivers), pl]
             for h, pl in zip(hexes.itertuples(), nearest_place(hexes.hex_id))]
    rec_rows = [[h.hex_id, int(h.rank), r(h.gap), int(labels.loc[h.hex_id, "bubbler_osm"])] for h in recs.itertuples()]
    growth = [[h.hex_id, int(h.bubbler_count), r(h.M1_s0), r(1 - math.exp(-h.M1_s0)), pl]
              for h, pl in zip(growth_pred.itertuples(), nearest_place(growth_pred.hex_id))]
    fut = pd.read_csv(out / "future_top10.csv").sort_values(["area", "rank"])
    assert fut.groupby("area").size().to_dict() == {"aerotropolis": 10, "leppington": 10}
    future = [[f.area, int(f.rank), f.hex_id, r(f.pred), r(1 - math.exp(-f.pred)), f.zone, f.nearest_station, int(f.station_dist_m),
               codes.encode(f.drivers)] for f in fut.itertuples()]
    heatmap = {"feats": codes.feats, "places": p_names, "today": today, "recs": rec_rows, "growth": growth, "future": future}
    return tracking, stats, heatmap


BUILDERS = {"toilets": build_toilets, "bubblers": build_bubblers}

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build the app data for one infrastructure layer.")
    parser.add_argument("--target", choices=list(BUILDERS), default="toilets", help="the infrastructure layer to build")
    target = parser.parse_args().target
    tracking, stats, heatmap = BUILDERS[target]()
    out = {
        APP / f"src/data/infra/{target}/tracking.json": json.dumps(tracking, indent=1, ensure_ascii=False),
        APP / f"src/data/infra/{target}/stats.json": json.dumps(stats, indent=1, ensure_ascii=False),
        APP / f"public/infra/{target}/heatmap.json": json.dumps(heatmap, separators=(",", ":"), ensure_ascii=False),
    }
    for path, text in out.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        print(f"{path.relative_to(APP)}: {path.stat().st_size / 1024:.0f} KB")
