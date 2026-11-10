"""Markdown tables for results.md from the CSVs in out/."""
import numpy as np
import pandas as pd

from common import OUT, label, load_study, load_growth

L = []
w = L.append


def rng(s, fmt="{:.3f}"):
    lo, hi, mu = s.min(), s.max(), s.mean()
    if np.isclose(lo, hi):
        return fmt.format(mu)
    return f"{fmt.format(mu)} ({fmt.format(lo)}–{fmt.format(hi)})"


def md(df):
    cols = list(df.columns)
    out = ["| " + " | ".join(map(str, cols)) + " |", "|" + "---|" * len(cols)]
    out += ["| " + " | ".join(map(str, r)) + " |" for r in df.itertuples(index=False)]
    return "\n".join(out)


# label changes
df = load_study()
g = load_growth()
rows = []
for v in ("public", "tagged"):
    for name, d in (("study", df), ("growth", g)):
        y0, y1 = d.toilet_count.to_numpy(), label(d, v)
        rows.append({"label": v, "area": name, "hexes changed": int((y1 > y0).sum()),
                     "empty hexes that gain a toilet": int(((y0 == 0) & (y1 > 0)).sum()),
                     "toilets added": int((y1 - y0).sum()), "toilets before": int(y0.sum()), "toilets after": int(y1.sum()),
                     "toilet hexes before": int((y0 > 0).sum()), "toilet hexes after": int((y1 > 0).sum())})
w("## label_changes\n" + md(pd.DataFrame(rows)))

# study metrics
m = pd.read_csv(OUT / "study_metrics_by_seed.csv")
for (lab, sub), d in m.groupby(["eval_label", "subset"], sort=False):
    t = d.groupby("model", sort=False).agg(list)
    out = pd.DataFrame({
        "model": t.index,
        "PR-AUC": [rng(pd.Series(x)) for x in t.pr_auc],
        "top 100": [rng(pd.Series(x), "{:.0f}") + "/100" for x in t.top100],
        "top 500": [rng(pd.Series(x), "{:.0f}") + "/500" for x in t.top500],
        "top 1,000": [rng(pd.Series(x), "{:.0f}") + "/1,000" for x in t.top1000],
        "deviance": [rng(pd.Series(x)) for x in t.deviance],
        "predicted total": [rng(pd.Series(x), "{:,.0f}") for x in t.pred_total],
        "actual": [f"{x[0]:,}" for x in t.actual_total],
        "candidates": [rng(pd.Series(x), "{:.0f}") for x in t.candidates]})
    w(f"## study_metrics {lab} {sub} (hexes {d.hexes.iloc[0]:,})\n" + md(out))

# picks
p = pd.read_csv(OUT / "picks_metrics_by_seed.csv")
p0 = p[p.seed == 0].set_index(["model", "post"])
pr = p.groupby(["model", "post"], sort=False)
out = []
for (mm, pp), d in pr:
    r = p0.loc[(mm, pp)]
    def rr(col):
        lo, hi = d[col].min(), d[col].max()
        return f"{int(r[col])}" + ("" if lo == hi else f" [{lo}–{hi}]")
    out.append({"model": mm, "post": pp, "gap ≥ 1": rr("gap_ge1") + "/120", "total gap": f"{r.total_gap:.0f}",
                "no_toilet / shortfall": f"{int(r.kind_no_toilet)} / {int(r.kind_shortfall)}",
                "OSM public toilet already": rr("osm_toilet_already") + f"/120 ({r.osm_toilet_already / 1.2:.0f}%)",
                "busy destination": f"{int(r.busy)}/{int(r.busy_checked)}" + (f" ({100 * r.busy / r.busy_checked:.0f}%)" if r.busy_checked else ""),
                "near planned site": rr("near_planned") + f"/120 ({r.near_planned / 1.2:.1f}%)",
                "uncovered (official)": f"{int(r.uncovered_official)}/120",
                "deciles 1–3": rr("dec_1_3"), "deciles 8–10": rr("dec_8_10"), "no SEIFA": int(r.dec_unknown),
                "newly covered residents": f"{r.newly_covered:,.0f}", "same as M0-P0": f"{int(r.overlap_with_M0P0)}/120"})
w("## picks (seed 0, [range over seeds 0–2] when it differs)\n" + md(pd.DataFrame(out)))
dec = p0[[f"dec{k}" for k in range(1, 11)] + ["dec_unknown"]].reset_index()
dec.columns = ["model", "post"] + [str(k) for k in range(1, 11)] + ["none"]
w("## seifa deciles of picks (seed 0)\n" + md(dec))

# council
c = pd.read_csv(OUT / "council_by_seed.csv")
out = []
for (s, mm), d in c.groupby(["set", "model"], sort=False):
    n = int(d.n.iloc[0])
    if s.startswith("reverse"):
        out.append({"set": s, "model": mm, "top 10%": "", "top 25%": "", "median pct": "",
                    "candidate in 1-ring": f"{rng(d.cand_ring, '{:.1f}')} of {rng(d.cand_ring_n, '{:.0f}')} candidates ({100 * d.cand_ring.sum() / d.cand_ring_n.sum():.1f}%)"})
        continue
    out.append({"set": s, "model": mm, "top 10%": f"{rng(d.top10, '{:.1f}')}/{n} ({100 * d.top10.mean() / n:.0f}%)",
                "top 25%": f"{rng(d.top25, '{:.1f}')}/{n} ({100 * d.top25.mean() / n:.0f}%)",
                "median pct": rng(d.median_pct, "{:.1f}"),
                "candidate in 1-ring": f"{rng(d.cand_ring, '{:.1f}')}/{int(d.cand_ring_n.iloc[0])} ({100 * d.cand_ring.mean() / d.cand_ring_n.iloc[0]:.0f}%)"})
w("## council\n" + md(pd.DataFrame(out)))
s = pd.read_csv(OUT / "council_sites_by_model_seed.csv")
sp = s[s.site_id.isin(["ST02", "NB01", "CU01", "HO02", "BL01", "TH01"])]
t = sp.groupby(["site_id", "name", "grid", "toilet_count_hex", "model"])["pct_hex"].mean().round(0).astype(int).unstack("model").reset_index()
w("## sports sites (percentile among empty study hexes, mean of 3 seeds)\n" + md(t))

# growth
gm = pd.read_csv(OUT / "growth_metrics_by_seed.csv")
for lab, d in gm.groupby("eval_label", sort=False):
    t = d.groupby("model", sort=False)
    out = pd.DataFrame({"model": list(t.groups),
                        "predicted total": [rng(x.pred_total, "{:.1f}") for _, x in t],
                        "actual": [int(x.actual_total.iloc[0]) for _, x in t],
                        "PR-AUC": [rng(x.pr_auc) for _, x in t],
                        "toilet hexes in top 100": [rng(x.found_top100, "{:.0f}") + f"/{int(x.toilet_hexes.iloc[0])}" for _, x in t],
                        "deviance": [rng(x.deviance) for _, x in t]})
    w(f"## growth {lab}\n" + md(out))
open(OUT / "tables.md", "w").write("\n\n".join(L) + "\n")
print("\n\n".join(L))
