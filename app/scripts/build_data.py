"""Turn the repo CSVs into app/src/data/stats.json for the internal stats page.

Run from anywhere:  /tmp/pigeon-env/bin/python app/scripts/build_data.py
Needs the remote branch origin/heatmap-held-out (fetched) for the held-out
`latest` predictions, unless app/data-src/predictions.csv already exists.
"""
import io
import json
import subprocess
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
    txt = subprocess.check_output(
        ["git", "-C", str(REPO), "show", "origin/heatmap-held-out:web/predictions.csv"], text=True
    )
    return pd.read_csv(io.StringIO(txt))


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
    "model": "Original cross-validated RandomForest, `latest` feature set (5-fold spatial CV; every number is held-out)",
    "headline": headline, "validity": validity, "growth": growth, "bradfield": bradfield,
    "plans": plans, "seifa": curated["seifa"], "newAreaTests": curated["new_area_tests"],
}, indent=1, ensure_ascii=False))
print(f"stats.json: {STATS_PATH.stat().st_size / 1024:.0f} KB (bundled into the app, src/data/)")
