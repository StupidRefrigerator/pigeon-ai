"""Study-area evaluations for every model x post-processing combination, all held-out.

1. Existing toilets: metrics vs official, OSM-corrected, and agreement-subset labels.
2. Validity of the top-120 picks (OSM toilet already there, busy destination, kind).
3. Council plans (method of experiments/gov/scripts/crosscheck.py).
4. SEIFA deciles of picks.
"""
import h3
import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, mean_poisson_deviance

from common import MODELS, OUT, REPO, SEEDS, label, load_study
from postprocess import newly_covered_population, priority, seifa_disadvantage, top_n, covered_hexes

N = 120
df = load_study()
oof = pd.read_csv(OUT / "study_oof_predictions.csv")
assert (oof.hex_id == df.hex_id).all()
ids = df.hex_id.to_numpy()
y_off = df.toilet_count.to_numpy()
LABELS = {"official": y_off, "osm_public": label(df, "public"), "osm_tagged": label(df, "tagged")}
MODEL_LABEL = {"M0": "official", "M1": "official", "M2": "osm_public", "M3": "osm_public",
               "M2t": "osm_tagged", "M3t": "osm_tagged",
               "M0+postL": "osm_public", "M1+postL": "osm_public"}  # post-hoc fix: no retraining
BASE_PRED = {**{m: m for m in MODELS}, "M0+postL": "M0", "M1+postL": "M1"}
OSM_HEX = {"official": [], "osm_public": list(ids[df.osm_toilets_public > 0]),
           "osm_tagged": list(ids[df.osm_toilets_public_tagged > 0])}
POST = {"P0": dict(w=0, coverage=False), "P1": dict(w=1, coverage=False),
        "P2": dict(w=0, coverage=True), "P3": dict(w=1, coverage=True)}


def pred(m, s):
    return oof[f"{BASE_PRED[m]}_s{s}"].to_numpy()


# ---------- 1. existing toilets ----------
def hits(score, y, n):
    return int((y[np.argsort(-score, kind="stable")[:n]] > 0).sum())


agree = LABELS["official"] == LABELS["osm_public"]
rows = []
for m in MODELS:
    for s in SEEDS:
        p = np.clip(pred(m, s), 1e-6, None)
        for lname, y in LABELS.items():
            for subset, mask in (("all", np.ones(len(y), bool)), ("labels_agree", agree)):
                if subset == "labels_agree" and lname != "official":
                    continue
                yy, pp = y[mask], p[mask]
                rows.append(dict(model=m, seed=s, eval_label=lname, subset=subset, hexes=int(mask.sum()),
                                 pr_auc=average_precision_score(yy > 0, pp), top100=hits(pp, yy, 100),
                                 top500=hits(pp, yy, 500), top1000=hits(pp, yy, 1000),
                                 deviance=mean_poisson_deviance(yy, pp), pred_total=pp.sum(),
                                 actual_total=int(yy.sum()), candidates=int(((pp - yy) >= 1).sum())))
metrics = pd.DataFrame(rows)
metrics.to_csv(OUT / "study_metrics_by_seed.csv", index=False)
agg = metrics.drop(columns="seed").groupby(["eval_label", "subset", "model"]).agg(["mean", "min", "max"])
agg.to_csv(OUT / "study_metrics.csv")

# ---------- shared lookups ----------
cls = pd.read_csv(REPO / "experiments/validity/hex_osm_classified.csv").set_index("hex_id")
busy = ((cls.strong_destinations.fillna("").astype(str).str.len() > 0)
        | (cls.category_site_only == "shopping_centre"))
decile, _ = seifa_disadvantage(df.seifa_irsd_score)
DEC = pd.Series(decile, index=ids)
POP = df.set_index("hex_id").population_est
osm_pub = df.set_index("hex_id").osm_toilets_public
# Coverage yardstick for "newly covered residents": official + OSM public toilets, k = 1, same for every variant.
covered_now = covered_hexes(set(ids[(y_off > 0) | (df.osm_toilets_public > 0)]), 1)
uncovered_now = [h for h in ids if h not in covered_now]
uncov_official = set(ids) - covered_hexes(set(ids[y_off > 0]), 1)

sites = pd.read_csv(REPO / "experiments/gov/planned_sites.csv")
sites = sites[sites.in_main_comparison].reset_index(drop=True)
assert len(sites) == 42
site_rings = set().union(*[set(h3.grid_disk(h, 1)) for h in sites.hex_id])
chance = len(site_rings & set(ids))

# ---------- 2 + 4. picks ----------
pick_rows, pick_lists = [], []
ref = {}
for m in MODEL_LABEL:
    lab = MODEL_LABEL[m]
    y = LABELS[lab]
    for s in SEEDS:
        p = pred(m, s)
        for pp_name, kw in POST.items():
            ranked = priority(ids, p, y, seifa_score=df.seifa_irsd_score, w=kw["w"], coverage=kw["coverage"],
                              extra_toilet_hexes=OSM_HEX[lab], k=1)
            top = top_n(ranked, N).copy()
            hx = top.hex_id.to_numpy()
            if (m, pp_name) == ("M0", "P0"):
                ref[s] = set(hx)
            yi = pd.Series(y, index=ids).loc[hx].to_numpy()
            yo = pd.Series(y_off, index=ids).loc[hx].to_numpy()
            in_cls = [h for h in hx if h in cls.index]
            d = DEC.loc[hx]
            row = dict(model=m, post=pp_name, seed=s, picks=len(hx),
                       gap_ge1=int((top.gap >= 1).sum()), total_gap=top.gap.sum(),
                       kind_no_toilet=int((yi == 0).sum()), kind_shortfall=int((yi > 0).sum()),
                       official_no_toilet=int((yo == 0).sum()),
                       osm_toilet_already=int((osm_pub.loc[hx] > 0).sum()),
                       busy_checked=len(in_cls), busy=int(busy.loc[in_cls].sum()),
                       near_planned=int(sum(h in site_rings for h in hx)),
                       uncovered_official=int(sum(h in uncov_official for h in hx)),
                       dec_1_3=int(d.between(1, 3).sum()), dec_4_7=int(d.between(4, 7).sum()),
                       dec_8_10=int(d.between(8, 10).sum()), dec_unknown=int(d.isna().sum()),
                       newly_covered=newly_covered_population(hx, uncovered_now, POP, 1),
                       overlap_with_M0P0=len(set(hx) & ref[s]))
            for k in range(1, 11):
                row[f"dec{k}"] = int((d == k).sum())
            pick_rows.append(row)
            if s == 0:
                pick_lists.append(top.assign(model=m, post=pp_name, label_used=lab,
                                             osm_toilets_public=osm_pub.loc[hx].to_numpy(),
                                             toilet_count_official=yo,
                                             busy=[busy.get(h, np.nan) for h in hx],
                                             near_planned=[h in site_rings for h in hx]))
picks = pd.DataFrame(pick_rows)
picks.to_csv(OUT / "picks_metrics_by_seed.csv", index=False)
picks.drop(columns="seed").groupby(["model", "post"], sort=False).agg(["mean", "min", "max"]).to_csv(OUT / "picks_metrics.csv")
pd.concat(pick_lists).to_csv(OUT / "picks_top120_seed0.csv", index=False)

# ---------- 3. council plans ----------
growth = pd.read_csv(OUT / "growth_predictions.csv").set_index("hex_id")
RNG = np.random.default_rng(20261109)
empty_ids = ids[y_off == 0]
park = df.set_index("hex_id").park_area_inside_m2
ctrl_empty = pd.Series(empty_ids).sample(n=1000, random_state=int(RNG.integers(1e9))).to_numpy()
ctrl_park = pd.Series([h for h in empty_ids if park[h] > 0]).sample(n=1000, random_state=int(RNG.integers(1e9))).to_numpy()
COUNCIL_MODELS = ["M0", "M1", "M2", "M3", "M2t", "M3t"]
site_rows, csum = [], []
for m in COUNCIL_MODELS:
    lab = MODEL_LABEL[m]
    for s in SEEDS:
        P = pd.Series(pred(m, s), index=ids)
        cand = pd.Series((P.to_numpy() - LABELS[lab]) >= 1, index=ids)
        srt = np.sort(P.loc[empty_ids].to_numpy())
        pct = lambda v: 100.0 * np.searchsorted(srt, v, side="right") / len(srt)
        G = growth[f"{m}_s{s}"]

        def ev(h):
            ring = h3.grid_disk(h, 1)
            if h in P.index:
                r = [x for x in ring if x in P.index]
                return dict(pct_hex=pct(P[h]), pred_hex=P[h], cand_ring=bool(cand.loc[r].any()), grid="study")
            r = [x for x in ring if x in G.index]
            return dict(pct_hex=pct(G[h]), pred_hex=G[h], cand_ring=np.nan, grid="growth")

        sv = pd.DataFrame([ev(h) for h in sites.hex_id])
        site_rows.append(sites[["site_id", "name", "site_type", "hex_id", "toilet_count_hex"]].join(sv).assign(model=m, seed=s))
        cs = {}
        for lbl, d in (("planned (42)", sv), ("planned new, empty hex", sv[(sites.site_type == "new") & (sites.toilet_count_hex == 0)]),
                       ("control: random empty hexes", pd.DataFrame([ev(h) for h in ctrl_empty])),
                       ("control: random empty park hexes", pd.DataFrame([ev(h) for h in ctrl_park]))):
            cr = d.cand_ring.dropna().astype(bool)
            csum.append(dict(model=m, seed=s, set=lbl, n=len(d), top10=int((d.pct_hex >= 90).sum()),
                             top25=int((d.pct_hex >= 75).sum()), median_pct=d.pct_hex.median(),
                             cand_ring=int(cr.sum()), cand_ring_n=len(cr)))
        allc = ids[cand.to_numpy()]
        csum.append(dict(model=m, seed=s, set="reverse: candidates near a planned site", n=len(allc),
                         cand_ring=int(sum(h in site_rings for h in allc)), cand_ring_n=len(allc),
                         top10=np.nan, top25=np.nan, median_pct=np.nan))
council = pd.DataFrame(csum)
council.to_csv(OUT / "council_by_seed.csv", index=False)
pd.concat(site_rows).to_csv(OUT / "council_sites_by_model_seed.csv", index=False)
print("chance ring hexes", chance, len(ids))
pd.set_option("display.width", 250); pd.set_option("display.max_columns", 40)
print(agg.round(3).to_string())
print(picks.drop(columns="seed").groupby(["model", "post"], sort=False).mean().round(1).to_string())
print(council.drop(columns="seed").groupby(["set", "model"], sort=False).mean().round(2).to_string())
