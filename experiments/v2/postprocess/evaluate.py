"""Evaluate every post-processing variant on the original model's held-out predictions.

Run: /tmp/pigeon-env/bin/python evaluate.py [path/to/PIGEON-AI-DATASET]
Writes results.csv, picks.csv, coverage.csv and coverage_by_area.csv next to this file.
"""
import json
import sys
from pathlib import Path

import h3
import numpy as np
import pandas as pd
from sklearn.neighbors import BallTree

from postprocess import (coverage_step, coverage_summary, covered_hexes, newly_covered_population,
                         priority, top_n)

REPO = Path(sys.argv[1] if len(sys.argv) > 1 else
            "/Users/summitsetia/Desktop/University/26T3/PIGEON-AI-DATASET")
OUT = Path(__file__).parent
N = 120
K = 1
WEIGHTS = [0.5, 1.0, 2.0]
CENTRAL_SYDNEY = ["Sydney", "Haymarket", "The Rocks", "Millers Point", "Dawes Point", "Barangaroo"]


def load():
    pred = pd.read_csv(REPO / "data/model/hex_predictions.csv")
    feat = pd.read_csv(REPO / "data/processed/sydney_extended_features.csv",
                       usecols=["hex_id", "population_est", "seifa_irsd_score"])
    df = pred.merge(feat, on="hex_id", how="left", validate="1:1")
    assert len(df) == 16228 and df.is_candidate.sum() == 120

    osm = pd.concat([
        pd.read_csv(REPO / "experiments/validity/hex_osm_classified.csv", usecols=["hex_id", "osm_public_toilets_in_hex"]),
        pd.read_csv(REPO / "experiments/validity/candidates_classified.csv", usecols=["hex_id", "osm_public_toilets_in_hex"]),
    ]).drop_duplicates("hex_id").set_index("hex_id")["osm_public_toilets_in_hex"]

    sites = pd.read_csv(REPO / "experiments/gov/planned_sites.csv")
    sites = sites[sites.in_main_comparison & sites.hex_id.notna()]
    assert len(sites) == 42
    near_site = covered_hexes(sites.hex_id, 1)
    return df, osm, near_site


def variants():
    yield "none", dict()
    for cov in ["official", "official+osm"]:
        yield f"coverage[{cov}]", dict(coverage=cov)
    for w in WEIGHTS:
        yield f"equity w={w:g}", dict(w=w)
    for cov in ["official", "official+osm"]:
        for w in WEIGHTS:
            yield f"coverage[{cov}] + equity w={w:g}", dict(coverage=cov, w=w)


def main():
    df, osm, near_site = load()
    osm_hexes = set(osm[osm > 0].index)
    pop = df.set_index("hex_id")["population_est"]
    ids, p, a = df.hex_id, df.predicted_toilets, df.toilet_count

    # Coverage on its own, both toilet sources, k = 0 shown as a sensitivity check.
    cov_rows, uncovered_sets = [], {}
    for source, extra in [("official", ()), ("official+osm", osm_hexes)]:
        for k in [0, 1]:
            c = coverage_step(ids, p, a, extra, k=k)
            cov_rows.append({"toilets": source, "k_rings": k, **coverage_summary(c.uncovered, df.population_est)})
            if k == K:
                uncovered_sets[source] = set(c.hex_id[c.uncovered])
                df[f"uncovered_{source}"] = c.uncovered.to_numpy()
    pd.DataFrame(cov_rows).to_csv(OUT / "coverage.csv", index=False)

    # Coverage by suburb: nearest ABS suburb point to each hex centroid.
    places = json.load(open(REPO / "data/reference/sydney_places.json"))["places"]
    names = list(places)
    tree = BallTree(np.radians([places[n] for n in names]), metric="haversine")
    cent = np.radians([h3.cell_to_latlng(h) for h in df.hex_id])
    df["suburb"] = [names[i] for i in tree.query(cent, k=1, return_distance=False)[:, 0]]
    by = df.groupby("suburb").agg(
        hexes=("hex_id", "size"), population=("population_est", "sum"),
        toilets=("toilet_count", "sum"),
        uncovered_hexes=("uncovered_official", "sum"),
        uncovered_hexes_with_osm=("uncovered_official+osm", "sum"))
    by["uncovered_population"] = df[df.uncovered_official].groupby("suburb").population_est.sum()
    by["uncovered_population_with_osm"] = df[df["uncovered_official+osm"]].groupby("suburb").population_est.sum()
    by = by.fillna(0)
    by["uncovered_hex_share"] = by.uncovered_hexes / by.hexes
    by["uncovered_pop_share"] = by.uncovered_population / by.population.replace(0, np.nan)
    by["central_sydney"] = by.index.isin(CENTRAL_SYDNEY)
    by.sort_values("uncovered_population", ascending=False).to_csv(OUT / "coverage_by_area.csv")

    # Every variant, same N.
    chance = len(near_site & set(df.hex_id)) / len(df)
    base_list = None
    rows, picks_out = [], []
    for name, opt in variants():
        cov = opt.get("coverage")
        s = priority(ids, p, a, seifa_score=df.seifa_irsd_score, w=opt.get("w", 0.0),
                     coverage=cov is not None, extra_toilet_hexes=osm_hexes if cov == "official+osm" else (), k=K)
        t = top_n(s, N)
        hexes = list(t.hex_id)
        base_list = base_list or set(hexes)
        dec = t.seifa_decile
        known_osm = [h for h in hexes if h in osm.index]
        rows.append({
            "variant": name, "picks": len(hexes),
            "picks_gap_ge_1": int((t.gap >= 1).sum()),
            "sum_gap": t.gap.sum(), "median_gap": t.gap.median(),
            "overlap_with_none": len(base_list & set(hexes)),
            "near_planned_site": sum(h in near_site for h in hexes),
            "near_planned_site_top30": sum(h in near_site for h in hexes[:30]),
            "chance_rate": chance,
            "osm_checked": len(known_osm),
            "osm_public_toilet": int(sum(osm[h] > 0 for h in known_osm)),
            "decile_1_3": int(dec.between(1, 3).sum()),
            "decile_8_10": int(dec.between(8, 10).sum()),
            "decile_unknown": int(dec.isna().sum()),
            "decile_counts": ";".join(f"{d}:{int((dec == d).sum())}" for d in range(1, 11)),
            "newly_covered_pop_official": newly_covered_population(hexes, uncovered_sets["official"], pop, K),
            "newly_covered_pop_with_osm": newly_covered_population(hexes, uncovered_sets["official+osm"], pop, K),
            "has_toilet_already": int(t.has_toilet.sum()),
        })
        picks_out.append(t.assign(variant=name, suburb=df.set_index("hex_id").suburb.reindex(t.hex_id).to_numpy())
                         [["variant", "rank", "hex_id", "suburb", "gap", "seifa_decile", "uncovered", "has_toilet", "priority"]])
    res = pd.DataFrame(rows)
    res.to_csv(OUT / "results.csv", index=False)
    pd.concat(picks_out).to_csv(OUT / "picks.csv", index=False)
    with pd.option_context("display.width", 250, "display.max_columns", 30):
        print(pd.DataFrame(cov_rows).round(3).to_string())
        print(res.drop(columns=["decile_counts"]).round(3).to_string())
        print(by[by.central_sydney].round(2).to_string())
        print(by.sort_values("uncovered_population", ascending=False).head(15).round(2).to_string())


if __name__ == "__main__":
    main()
