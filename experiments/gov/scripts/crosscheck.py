"""Cross-check government-planned toilet sites against the two models' held-out predictions."""
import sys
import numpy as np, pandas as pd, h3

REPO = "/Users/summitsetia/Desktop/University/26T3/PIGEON-AI-DATASET"
WORK = "/tmp/pigeon-eval/gov"
RNG = np.random.default_rng(20261109)
MODELS = {"original": "baseline_pred", "good_areas": "good_areas_pred"}

orig = pd.read_csv(f"{REPO}/data/model/hex_predictions.csv")
good = pd.read_csv(f"{REPO}/data/model/good_areas/hex_predictions.csv")
feat = pd.read_csv(f"{REPO}/data/processed/sydney_extended_features.csv", usecols=["hex_id", "park_area_inside_m2"])
hexes = good[["hex_id", "toilet_count", "baseline_pred", "good_areas_pred", "gap"]].rename(columns={"gap": "gap_good"})
hexes = hexes.merge(orig[["hex_id", "is_candidate", "gap"]].rename(columns={"is_candidate": "cand_original", "gap": "gap_original"}), on="hex_id")
hexes = hexes.merge(good[["hex_id", "is_candidate"]].rename(columns={"is_candidate": "cand_good_areas"}), on="hex_id")
hexes = hexes.merge(feat, on="hex_id")
assert len(hexes) == 16228
H = hexes.set_index("hex_id")
growth = pd.read_csv("/tmp/pigeon-eval/growth/growth_predictions.csv").set_index("hex_id")

empty = hexes[hexes.toilet_count == 0]
EMPTY_SORTED = {m: np.sort(empty[c].values) for m, c in MODELS.items()}

def pct(model, v):
    a = EMPTY_SORTED[model]
    return 100.0 * np.searchsorted(a, v, side="right") / len(a)

def evaluate(h):
    """Model values for one res-9 hex and its 1-ring. Returns None if the hex is outside both grids."""
    ring = h3.grid_disk(h, 1)
    if h in H.index:
        src = "study"
        r = H.loc[[x for x in ring if x in H.index]]
        out = {"in_grid": src, "toilet_count_hex": int(H.at[h, "toilet_count"]), "toilet_count_ring": int(r.toilet_count.sum())}
        for m, c in MODELS.items():
            out[f"{m}_hex"] = H.at[h, c]
            out[f"{m}_ring_max"] = r[c].max()
            out[f"{m}_pct_hex"] = pct(m, H.at[h, c])
            out[f"{m}_pct_ring_max"] = pct(m, r[c].max())
            out[f"{m}_cand_hex"] = bool(H.at[h, f"cand_{m}"])
            out[f"{m}_cand_ring"] = bool(r[f"cand_{m}"].any())
        return out
    if h in growth.index:
        r = growth.loc[[x for x in ring if x in growth.index]]
        out = {"in_grid": "growth", "toilet_count_hex": int(growth.at[h, "toilet_count"]), "toilet_count_ring": int(r.toilet_count.sum())}
        for m, c in MODELS.items():
            out[f"{m}_hex"] = growth.at[h, c]
            out[f"{m}_ring_max"] = r[c].max()
            out[f"{m}_pct_hex"] = pct(m, growth.at[h, c])
            out[f"{m}_pct_ring_max"] = pct(m, r[c].max())
            out[f"{m}_cand_hex"] = np.nan
            out[f"{m}_cand_ring"] = np.nan
        return out
    return {"in_grid": "outside"}

def summarise(df, label):
    rows = []
    for m in MODELS:
        s = {"set": label, "model": m, "n": len(df)}
        cr = df[f"{m}_cand_ring"].dropna().astype(bool)
        s["n_with_candidate_flags"] = len(cr)
        s["share_candidate_in_ring"] = cr.mean() if len(cr) else np.nan
        s["share_candidate_in_hex"] = df[f"{m}_cand_hex"].dropna().astype(bool).mean() if len(cr) else np.nan
        s["median_pct_hex"] = df[f"{m}_pct_hex"].median()
        s["share_top10_hex"] = (df[f"{m}_pct_hex"] >= 90).mean()
        s["share_top25_hex"] = (df[f"{m}_pct_hex"] >= 75).mean()
        s["median_pct_ring_max"] = df[f"{m}_pct_ring_max"].median()
        s["share_top10_ring_max"] = (df[f"{m}_pct_ring_max"] >= 90).mean()
        s["share_top25_ring_max"] = (df[f"{m}_pct_ring_max"] >= 75).mean()
        rows.append(s)
    return rows

def control(pool, n, label):
    pick = pool.sample(n=n, random_state=int(RNG.integers(1e9)))
    return pd.DataFrame([evaluate(h) for h in pick.hex_id]), label

def main():
    sites = pd.read_csv(f"{WORK}/sites_geocoded.csv")
    sites["hex_id"] = [h3.latlng_to_cell(a, b, 9) if pd.notna(a) else None for a, b in zip(sites.lat, sites.lng)]
    vals = pd.DataFrame([evaluate(h) if h else {"in_grid": "no_geocode"} for h in sites.hex_id])
    sites = pd.concat([sites, vals], axis=1)
    sites["in_main_comparison"] = (sites.geocode_confidence != "suburb-only") & sites.in_grid.isin(["study", "growth"])
    sites.to_csv(f"{WORK}/planned_sites.csv", index=False)

    main_all = sites[sites.in_main_comparison]
    main_new = main_all[main_all.site_type == "new"]
    new_empty = main_new[main_new.toilet_count_hex == 0]
    summary = []
    summary += summarise(main_all, "planned: all types")
    summary += summarise(main_new, "planned: new sites")
    summary += summarise(new_empty, "planned: new sites, hex has no mapped toilet")
    summary += summarise(main_all[main_all.site_type != "new"], "planned: replacement/relocation")
    for pool, n, label in [(empty, 1000, "control: random empty hexes"),
                           (empty[empty.park_area_inside_m2 > 0], 1000, "control: random empty park hexes")]:
        df, lab = control(pool, n, label)
        summary += summarise(df, lab)
    summ = pd.DataFrame(summary)

    rev = []
    site_rings = {h: set(h3.grid_disk(h, 1)) for h in main_all.hex_id}
    for m in MODELS:
        top = hexes[hexes[f"cand_{m}"]].sort_values(f"gap_{m if m=='original' else 'good'}", ascending=False).head(30)
        hits = [h for h in top.hex_id if any(h in ring for ring in site_rings.values())]
        rev.append({"set": "reverse: top-30 candidates within 1 ring of a planned site", "model": m, "n": 30, "hits": len(hits), "hit_hexes": ";".join(hits)})
        allc = hexes[hexes[f"cand_{m}"]]
        hits_all = sum(any(h in ring for ring in site_rings.values()) for h in allc.hex_id)
        rev.append({"set": "reverse: all candidates within 1 ring of a planned site", "model": m, "n": len(allc), "hits": hits_all})
        # chance level: fraction of study hexes within one ring of any planned site
        cover = set().union(*site_rings.values()) & set(hexes.hex_id)
        rev.append({"set": "reverse: chance (share of study hexes inside any planned-site ring)", "model": m, "n": len(hexes), "hits": len(cover)})
    summ = pd.concat([summ, pd.DataFrame(rev)], ignore_index=True)
    summ.to_csv(f"{WORK}/crosscheck_summary.csv", index=False)
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30)
    print(summ.round(3).to_string())

if __name__ == "__main__":
    main()
