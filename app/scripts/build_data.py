"""Turn the repo CSVs into app/src/data/stats.json for the internal stats page.

Run from anywhere:  /tmp/pigeon-env/bin/python app/scripts/build_data.py
Needs the remote branch origin/heatmap-held-out (fetched) for the held-out
`latest` predictions, unless app/data-src/predictions.csv already exists.
"""
import json
from pathlib import Path

import pandas as pd

APP = Path(__file__).resolve().parents[1]
REPO = APP.parent

SCENARIO = "dphi2041|shops_mid|bus_calibrated"
BRADFIELD_NOTE = "planned scenario — read the ranking, not the totals"


def r(x, n=3):
    return None if pd.isna(x) else round(float(x), n)


def load_predictions():
    local = APP / "data-src" / "predictions.csv"
    if local.exists():
        return pd.read_csv(local)
    return pd.read_csv(REPO / "web/predictions.csv")


# ---------- study hexes (held-out, latest) ----------
pred = load_predictions()
assert len(pred) == 16228
review = pd.read_csv(REPO / "data/review/candidate_review.csv")
gap = (pred["latest"] - pred["toilet_count"]).clip(lower=0)
cand_ids = set(pred.loc[(pred["latest"] - pred["toilet_count"]) >= 1, "hex_id"])
assert cand_ids == set(review["hex_id"]) and len(cand_ids) == 120, "candidates do not match candidate_review.csv"

top = pd.read_csv(REPO / "experiments/future/aero_top15.csv")
top = top[(top.scenario == SCENARIO) & (top.model == "baseline")]

# ---------- stats (original model only) ----------
curated = json.load(open(APP / "scripts/curated_stats.json"))
m = pd.read_csv(REPO / "experiments/validity/metrics_existing.csv").set_index("metric")["baseline"]
n_hex, actual_total = len(pred), int(pred.toilet_count.sum())
hexes_with_toilet = int((pred.toilet_count > 0).sum())

def hit(key, n):
    return {"label": f"Real toilet hexes in top {n:,}", "x": int(m[key]), "y": n, "pct": round(100 * m[key] / n, 1)}

headline = {
    "hexes": n_hex, "toilets": actual_total, "toiletHexes": hexes_with_toilet,
    "prAuc": {"value": r(m.pr_auc), "random": 0.118},
    "topN": [hit("top100_hits", 100), hit("top500_hits", 500), hit("top1000_hits", 1000)],
    "deviance": r(m.poisson_deviance),
    "predictedTotal": round(float(m.predicted_total)),
    "actualTotal": actual_total,
    "predictedTotalPctOfActual": round(100 * float(m.predicted_total) / actual_total, 1),
    "candidates": len(cand_ids),
}

cc = pd.read_csv(REPO / "experiments/validity/candidates_classified.csv")
cc = cc[cc.baseline_candidate]
assert len(cc) == 120
osm_public = int((cc.osm_public_toilets_in_hex > 0).sum())
osm_extra = int(cc.toilet_not_on_map.sum())
assert (osm_public, osm_extra) == (60, 55)
v = curated["validity_curated"]
n = len(cc)
validity = {
    "n": n,
    "rows": [
        {"label": "A public toilet on OpenStreetMap", "x": osm_public, "y": n},
        {"label": "More OSM public toilets than the official map lists", "x": osm_extra, "y": n},
        {"label": "A shopping centre or strong destination (station, beach, large park, library, mall)", "x": v["shop_or_destination"], "y": n},
        {"label": "Only houses or industry", "x": v["houses_or_industry_only"], "y": n},
    ],
    "note": v["limit_note"],
}
for row in validity["rows"]:
    row["pct"] = round(100 * row["x"] / row["y"])

gm = pd.read_csv(REPO / "experiments/growth/metrics.csv").set_index("model").loc["baseline"]
ps = pd.read_csv(REPO / "experiments/growth/per_suburb.csv")
ps = ps[ps.suburb != "TOTAL"]
growth = {
    "hexes": int(ps.hexes.sum()), "suburbs": len(ps),
    "actual": int(gm.actual), "predicted": r(gm.pred_total, 1),
    "toiletHexes": int(gm.hexes_with_toilet),
    "top100": {"x": int(gm.hexes_with_toilet_in_top100), "y": int(gm.hexes_with_toilet),
               "pct": round(100 * gm.hexes_with_toilet_in_top100 / gm.hexes_with_toilet)},
    "prAuc": {"value": r(gm.pr_auc), "random": r(gm.base_rate)},
    "perSuburb": [
        {"suburb": s.suburb, "hexes": int(s.hexes), "actual": int(s.actual_toilets), "pred": r(s.baseline_pred, 1)}
        for s in ps.itertuples()
    ],
    "note": "A random top 100 would catch about 3 of the 35. Over-predicting is expected because these suburbs are still filling in.",
}

asum = pd.read_csv(REPO / "experiments/future/aero_summary.csv")
asum = asum[asum.model == "baseline"].set_index("scenario")
mid, today = asum.loc[SCENARIO], asum.loc["today_real_features"]
oran = pd.read_csv(REPO / "experiments/future/oran_summary.csv")
oran = oran[oran.model == "baseline"].set_index("scenario")
proxy = oran.loc["zoning_proxy|shops_mid|bus_calibrated"]
assert (int(proxy.top10_overlap_with_real_features), int(proxy.real_toilet_hexes_in_top10)) == (5, 2)
real = oran.loc["real_features"]
bradfield = {
    "label": BRADFIELD_NOTE,
    "scenario": SCENARIO,
    "todayTotal": r(today.total, 1), "midTotal": r(mid.total, 1),
    "hexesGe1": int(mid.hexes_ge1), "maxHex": r(mid.max_hex, 2),
    "top": [
        {"rank": i + 1, "zone": t.zone, "station": t.nearest_station, "stationM": int(t.station_dist_m),
         "pred": r(t.pred, 2), "drivers": t.drivers}
        for i, t in enumerate(top.sort_values("pred", ascending=False).head(5).itertuples())
    ],
    "oranProxy": {
        "overlap": {"real": int(real.top10_overlap_with_real_features), "proxy": int(proxy.top10_overlap_with_real_features), "of": 10},
        "toiletHexesInTop10": {"real": int(real.real_toilet_hexes_in_top10), "proxy": int(proxy.real_toilet_hexes_in_top10), "of": int(proxy.real_toilets)},
    },
}

cs = pd.read_csv(REPO / "experiments/gov/crosscheck_summary.csv")
cs = cs[cs.model == "original"].set_index("set")
def planrow(name, label, n_fn=None):
    s = cs.loc[name]
    n = int(s.n)
    return {
        "label": label, "n": n,
        "top10": {"x": round(s.share_top10_hex * n), "y": n, "pct": round(100 * s.share_top10_hex)},
        "top25": {"x": round(s.share_top25_hex * n), "y": n, "pct": round(100 * s.share_top25_hex)},
        "candidateNear": {"x": round(s.share_candidate_in_ring * s.n_with_candidate_flags), "y": int(s.n_with_candidate_flags),
                          "pct": round(100 * s.share_candidate_in_ring)},
        "medianPct": round(s.median_pct_hex),
    }
rev_all = cs.loc["reverse: all candidates within 1 ring of a planned site"]
rev_chance = cs.loc["reverse: chance (share of study hexes inside any planned-site ring)"]
plans = {
    "rows": [
        planrow("planned: all types", "Planned sites"),
        planrow("control: random empty hexes", "Random empty hexes"),
        planrow("control: random empty park hexes", "Random empty park hexes"),
    ],
    "fairest": planrow("planned: new sites, hex has no mapped toilet", "Brand-new sites in hexes with no toilet yet"),
    "reverse": {
        "candidatesNear": {"x": int(rev_all.hits), "y": int(rev_all.n), "pct": round(100 * rev_all.hits / rev_all.n, 1)},
        "chance": {"x": int(rev_chance.hits), "y": int(rev_chance.n), "pct": round(100 * rev_chance.hits / rev_chance.n, 1)},
    },
    "sources": "56 sites from 22 councils' strategies, project pages, DA reports and media releases; 42 could be placed on a hex.",
    "misses": "Sports-field amenity blocks (Ken Birdsey Park at the 29th percentile, Anthony Skarratt Reserve at the 41st). The model has no sports-field feature.",
}

STATS_PATH = APP / "src" / "data" / "stats.json"
STATS_PATH.parent.mkdir(exist_ok=True)
STATS_PATH.write_text(json.dumps({
    "model": "Sections 1–7 use V11, the `latest` feature set (5-fold spatial CV; every number is held-out)",
    "headline": headline, "validity": validity, "growth": growth, "bradfield": bradfield,
    "plans": plans, "seifa": curated["seifa"], "newAreaTests": curated["new_area_tests"],
    "v2Changes": curated["v2_changes"]["rows"], "v2Note": curated["v2_changes"]["note"],
}, indent=1, ensure_ascii=False))
print(f"stats.json: {STATS_PATH.stat().st_size / 1024:.0f} KB (bundled into the app, src/data/)")

# ---------- tracking page: version history + the current model ----------
V2 = REPO / "experiments/v2/combos/out"
sm = pd.read_csv(V2 / "study_metrics.csv", header=[0, 1], index_col=[0, 1, 2])
def study(model):
    row = sm.loc[("official", "all", model)]
    return {k: row[(k, "mean")] for k in ["pr_auc", "top100", "top1000", "deviance", "pred_total", "actual_total"]}
summ = pd.read_csv(V2 / "summary_table.csv").set_index(["model", "post-processing"])
m0, m1 = study("M0"), study("M1")
assert (r(m0["pr_auc"]), r(m1["pr_auc"])) == (0.52, 0.569)

def ratio(s):
    x, y = (int(v) for v in s.split("/"))
    return {"x": x, "y": y, "pct": round(100 * x / y)}

jimmy = curated["versions_jimmy"]
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

chosen = summ.loc[("M1, OSM fix after model", "P1 equity w=1")]
poor, rich = (int(v) for v in chosen["deciles 1–3 / 8–10"].split("/"))
TRACKING_PATH = APP / "src" / "data" / "tracking.json"
TRACKING_PATH.write_text(json.dumps({
    "source": "5-fold res-6 spatial CV on 16,228 study hexes. V1–V10 are Jimmy's saved runs (seed 0). V11 and V12 are the mean of seeds 0–2 (experiments/v2/combos).",
    "versions": versions,
    "current": {
        "id": "V12",
        "prAuc": {"value": r(m1["pr_auc"]), "was": r(m0["pr_auc"]), "random": 0.118},
        "deviance": {"value": r(m1["deviance"]), "was": r(m0["deviance"])},
        "top1000": {"x": round(m1["top1000"]), "y": 1000, "pct": round(m1["top1000"] / 10, 1)},
        "council": ratio(summ.loc[("M1 +F", "P0 none"), "council top 10%"]),
        "predictedTotal": round(m1["pred_total"]), "actualTotal": int(m1["actual_total"]),
        "setup": [
            "Predict toilets per hex with V12",
            "Skip spots where OpenStreetMap already lists a toilet",
            "Rank with disadvantage weighting (w = 1)",
            "List only spots short by at least 1 toilet",
        ],
        "picks": {
            "listed": ratio(chosen["picks gap ≥ 1"])["x"],
            "osmAlready": ratio(chosen["OSM toilet already"]),
            "nearPlanned": ratio(chosen["near planned site"]),
            "poorest30": {"x": poor, "y": 120, "pct": round(100 * poor / 120)},
            "richest30": {"x": rich, "y": 120, "pct": round(100 * rich / 120)},
        },
    },
}, indent=1, ensure_ascii=False))
print(f"tracking.json: {TRACKING_PATH.stat().st_size / 1024:.0f} KB")
