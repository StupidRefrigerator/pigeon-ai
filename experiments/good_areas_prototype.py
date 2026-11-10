"""Good-areas experiment: train only on well-served areas, predict everywhere.

Areas are the res-6 blocks (about 36 km2, 90 of them) already used for CV.
A block is well-served when its real toilets exceed the baseline model's
held-out prediction for it. Every prediction here is still held-out:
other areas are predicted by a forest trained on the good blocks, and the
good blocks are predicted by 5-fold CV within themselves.

A random-block control with the same number of blocks separates the effect
of choosing good areas from the effect of training on fewer rows.
"""
import sys
from pathlib import Path

import h3
import numpy as np
import pandas as pd
from sklearn.metrics import mean_poisson_deviance
from sklearn.model_selection import GroupKFold

ROOT = Path(sys.argv[1])
sys.path.insert(0, str(ROOT / "src"))
from pigeon_ai.model import TARGETS, fairness_table, is_candidate, make_forest  # noqa: E402

pd.set_option("display.width", 220)
df = pd.read_csv(ROOT / "data/processed/sydney_extended_features.csv")
base = pd.read_csv(ROOT / "data/model/hex_predictions.csv").set_index("hex_id").loc[df.hex_id]
features = TARGETS["toilets"].feature_sets["latest"]
X, y = df[features].to_numpy(), df["toilet_count"].to_numpy()
block = np.array([h3.cell_to_parent(h, 6) for h in df.hex_id])
base_pred = base["predicted_toilets"].to_numpy()

blocks = pd.DataFrame({"block": block, "actual": y, "pred": base_pred}).groupby("block").sum()
blocks["ratio"] = blocks.actual / blocks.pred
eligible = blocks[blocks.pred >= 5]
good = eligible.sort_values("ratio", ascending=False).head(len(eligible) // 3).index
print(f"{len(blocks)} blocks, {len(eligible)} with >=5 predicted toilets, {len(good)} chosen as well-served")
print(f"good blocks: actual {blocks.loc[good].actual.sum()} vs baseline predicted {blocks.loc[good].pred.sum():.0f}"
      f" (ratio {blocks.loc[good].actual.sum() / blocks.loc[good].pred.sum():.2f}),"
      f" {np.isin(block, good).sum()} hexes")


def train_on(chosen, seed=0):
    inside = np.isin(block, chosen)
    pred = np.zeros(len(y))
    pred[~inside] = make_forest(seed).fit(X[inside], y[inside]).predict(X[~inside])
    idx = np.flatnonzero(inside)
    for train, test in GroupKFold(5).split(idx, groups=block[idx]):
        pred[idx[test]] = make_forest(seed).fit(X[idx[train]], y[idx[train]]).predict(X[idx[test]])
    return pred, inside


def summary(name, pred, inside):
    cand = is_candidate(pred, y)
    out = ~inside
    return dict(
        model=name,
        total_pred=round(pred.sum()), total_actual=int(y.sum()),
        other_areas_pred=round(pred[out].sum()), other_areas_actual=int(y[out].sum()),
        deviance_all=round(mean_poisson_deviance(y, np.clip(pred, 1e-6, None)), 4),
        candidates=int(cand.sum()), no_toilet=int((cand & (y == 0)).sum()),
        shortfall=int((cand & (y > 0)).sum()), max_pred=round(pred.max(), 2),
        overlap_with_baseline=int((cand & base["is_candidate"].to_numpy()).sum()),
    )


rows = [summary("baseline (all areas)", base_pred, np.zeros(len(y), bool))]
good_pred, good_inside = train_on(good)
rows.append(summary("good areas only", good_pred, good_inside))
rng = np.random.default_rng(0)
for i in range(3):
    random_blocks = rng.choice(eligible.index, size=len(good), replace=False)
    rows.append(summary(f"random areas #{i + 1}", *train_on(random_blocks)))
print(pd.DataFrame(rows).to_string(index=False))

print("\nAverage prediction by real toilet count")
spread = pd.DataFrame({"actual": np.minimum(y, 6), "baseline": base_pred, "good": good_pred})
print(spread.groupby("actual")[["baseline", "good"]].mean().round(2).T.rename(columns={6: "6+"}).to_string())

seifa = df["seifa_irsd_score"]
for name, pred in [("baseline", base_pred), ("good areas", good_pred)]:
    table = fairness_table(seifa, pred, y, is_candidate(pred, y))
    print(f"\nFairness ({name}): decile 1 = most disadvantaged")
    print(table[["group", "hexes", "actual_toilets", "predicted_toilets", "candidates",
                 "candidates_per_1000_hexes"]].round(1).to_string(index=False))

cand = is_candidate(good_pred, y)
top = pd.DataFrame({"hex_id": df.hex_id, "actual": y, "good_pred": good_pred, "base_pred": base_pred})[cand]
top = top.assign(new=~base["is_candidate"].to_numpy()[cand]).sort_values("good_pred", ascending=False).head(15)
top[["lat", "lng"]] = [h3.cell_to_latlng(h) for h in top.hex_id]
print("\nTop 15 good-areas candidates")
print(top.round(3).to_string(index=False))
