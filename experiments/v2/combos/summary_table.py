"""One-table summary of every combination (seed 0 picks; model metrics = mean of seeds 0-2)."""
import pandas as pd

from common import OUT

m = pd.read_csv(OUT / "study_metrics_by_seed.csv")
mo = m[(m.eval_label == "official") & (m.subset == "all")].groupby("model")[["pr_auc", "top100", "deviance", "pred_total"]].mean()
ma = m[(m.eval_label == "official") & (m.subset == "labels_agree")].groupby("model").pr_auc.mean()
c = pd.read_csv(OUT / "council_by_seed.csv")
c = c[c.set == "planned (42)"].groupby("model")[["top10", "top25"]].mean()
g = pd.read_csv(OUT / "growth_metrics_by_seed.csv")
g = g[g.eval_label == "official"].groupby("model")[["pred_total", "found_top100", "pr_auc"]].mean()
p = pd.read_csv(OUT / "picks_metrics_by_seed.csv")
p = p[p.seed == 0]
POST = {"P0": "none", "P1": "equity w=1", "P2": "coverage filter", "P3": "coverage + equity"}
rows = []
for r in p.itertuples():
    if r.model in ("M2t", "M3t"):
        continue
    base = r.model.split("+")[0]
    name = {"M0": "M0 base", "M1": "M1 +F", "M2": "M2 +L", "M3": "M3 +F+L",
            "M0+postL": "M0, OSM fix after model", "M1+postL": "M1, OSM fix after model"}[r.model]
    rows.append({"model": name, "post-processing": f"{r.post} {POST[r.post]}",
                 "PR-AUC (official)": f"{mo.pr_auc[base]:.3f}", "PR-AUC (labels agree)": f"{ma[base]:.3f}",
                 "top-100 hits": f"{mo.top100[base]:.0f}/100", "deviance": f"{mo.deviance[base]:.3f}",
                 "council top 10%": f"{c.top10[base]:.0f}/42", "growth found": f"{g.found_top100[base]:.0f}/35",
                 "growth predicted (39)": f"{g.pred_total[base]:.0f}",
                 "picks gap ≥ 1": f"{r.gap_ge1}/120",
                 "OSM toilet already": f"{r.osm_toilet_already}/120",
                 "near planned site": f"{r.near_planned}/120",
                 "deciles 1–3 / 8–10": f"{r.dec_1_3} / {r.dec_8_10}",
                 "newly covered residents": f"{r.newly_covered / 1000:.0f}k"})
t = pd.DataFrame(rows)
md = ["| " + " | ".join(t.columns) + " |", "|" + "---|" * len(t.columns)]
md += ["| " + " | ".join(map(str, x)) + " |" for x in t.itertuples(index=False)]
open(OUT / "summary_table.md", "w").write("\n".join(md) + "\n")
t.to_csv(OUT / "summary_table.csv", index=False)
print("\n".join(md))
