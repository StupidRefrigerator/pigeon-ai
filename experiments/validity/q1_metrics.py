"""Q1: does each model predict where toilets already are? Side-by-side metrics on all hexes."""
import sys
import numpy as np, pandas as pd
from sklearn.metrics import average_precision_score, mean_poisson_deviance

REPO = sys.argv[1] if len(sys.argv) > 1 else "/Users/summitsetia/Desktop/University/26T3/PIGEON-AI-DATASET"
OUT = "/tmp/pigeon-eval/validity"
base = pd.read_csv(f"{REPO}/data/model/hex_predictions.csv")
ga = pd.read_csv(f"{REPO}/data/model/good_areas/hex_predictions.csv")
df = base[["hex_id", "toilet_count", "predicted_toilets"]].merge(
    ga[["hex_id", "toilet_count", "baseline_pred", "good_areas_pred", "in_good_block"]], on="hex_id", suffixes=("", "_ga"))
assert len(df) == len(base) == len(ga), (len(df), len(base), len(ga))
assert (df.toilet_count == df.toilet_count_ga).all()
assert np.allclose(df.predicted_toilets, df.baseline_pred)
y = df.toilet_count.values
has = (y > 0).astype(int)
models = {"baseline": df.predicted_toilets.values, "good_areas": df.good_areas_pred.values}

rows = []
def add(metric, vals, note=""):
    rows.append({"metric": metric, **vals, "note": note})

eps = 1e-9
add("hexes", {m: len(y) for m in models})
add("poisson_deviance", {m: mean_poisson_deviance(y, np.clip(p, eps, None)) for m, p in models.items()},
    f"mean-everywhere {mean_poisson_deviance(y, np.full(len(y), y.mean())):.3f}")
add("pr_auc", {m: average_precision_score(has, p) for m, p in models.items()}, f"random {has.mean():.3f}")
for n in (100, 500, 1000):
    add(f"top{n}_hits", {m: int(has[np.argsort(-p, kind='stable')[:n]].sum()) for m, p in models.items()}, "hexes with >=1 toilet")
add("recall_toilet_hexes_in_top1000", {m: has[np.argsort(-p, kind='stable')[:1000]].sum() / has.sum() for m, p in models.items()},
    f"of {has.sum()} toilet hexes")
add("toilets_in_top1000_share", {m: y[np.argsort(-p, kind='stable')[:1000]].sum() / y.sum() for m, p in models.items()},
    f"of {y.sum()} toilets")
add("predicted_total", {m: p.sum() for m, p in models.items()}, f"actual {y.sum()}")
add("spearman_with_actual", {m: pd.Series(p).corr(pd.Series(y), method="spearman") for m, p in models.items()})
# restricted to hexes outside good blocks (fully held-out for both; good-areas training never saw them)
mask = ~df.in_good_block.values
add("pr_auc_outside_good_blocks", {m: average_precision_score(has[mask], p[mask]) for m, p in models.items()},
    f"{mask.sum()} hexes, random {has[mask].mean():.3f}")
add("pr_auc_inside_good_blocks", {m: average_precision_score(has[~mask], p[~mask]) for m, p in models.items()},
    f"{(~mask).sum()} hexes, random {has[~mask].mean():.3f}")
metrics = pd.DataFrame(rows)

bands = [0, 0.05, 0.1, 0.25, 0.5, 1.0, 1.5, 2.0, np.inf]
cal = []
for m, p in models.items():
    b = pd.cut(p, bands, right=False)
    g = pd.DataFrame({"band": b, "p": p, "y": y}).groupby("band", observed=True).agg(n=("y", "size"), mean_pred=("p", "mean"), mean_actual=("y", "mean"))
    g["model"] = m
    cal.append(g.reset_index())
cal = pd.concat(cal)
cal["band"] = cal["band"].astype(str)

ycat = pd.Series(np.where(y >= 6, "6+", y.astype(str)))
bycount = pd.DataFrame({"actual": ycat, **models}).groupby("actual").agg(n=("baseline", "size"), baseline=("baseline", "mean"), good_areas=("good_areas", "mean"))

metrics.to_csv(f"{OUT}/metrics_existing.csv", index=False)
cal.to_csv(f"{OUT}/q1_calibration_bands.csv", index=False)
bycount.to_csv(f"{OUT}/q1_mean_pred_by_actual.csv")
pd.set_option("display.width", 200)
print(metrics.to_string(index=False)); print(cal.to_string(index=False)); print(bycount)
