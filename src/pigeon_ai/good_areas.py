"""Good-areas experiment: train only on well-served blocks, predict everywhere.

A block is a res-6 H3 cell, the same grouping the production spatial CV uses.
Not production: model.py stays the production path and owns the shared helpers.
"""
from time import perf_counter

import h3
import numpy as np
import pandas as pd
import shap
from sklearn.model_selection import GroupKFold

from .model import (
    BLOCK_RESOLUTION, DATA_FILE, MODEL_DIR, N_FOLDS, REVIEW_PATH, SEEDS, SEIFA_COLUMN, TARGETS,
    candidate_kind, cross_validate, fairness_table, is_candidate, load_review,
    make_forest, merge_review, metrics_row, p_any, save_review, top_drivers,
)

GOOD_AREAS_DIR = MODEL_DIR / "good_areas"
GOOD_AREAS_REVIEW_PATH = REVIEW_PATH.with_name("candidate_review_good_areas.csv")
MIN_PREDICTED = 5
TOP_FRACTION = 1 / 3
N_CONTROLS = 3
CONTROL_RNG_SEED = 0
SPREAD_CAP = 6


def block_ids(df):
    return np.array([h3.cell_to_parent(h, BLOCK_RESOLUTION) for h in df["hex_id"]])


def block_table(block, actual, baseline_pred):
    table = pd.DataFrame({"block": block, "actual": actual, "baseline_pred": baseline_pred, "hexes": 1})
    table = table.groupby("block").sum()
    table["ratio"] = table["actual"] / table["baseline_pred"]
    return table


def eligible_blocks(block, actual, baseline_pred, min_predicted=MIN_PREDICTED):
    table = block_table(block, actual, baseline_pred)
    return table[table["baseline_pred"] >= min_predicted]


def choose_good_blocks(block, actual, baseline_pred, min_predicted=MIN_PREDICTED,
                       top_fraction=TOP_FRACTION):
    """Blocks with the most real toilets relative to what the baseline model expects."""
    eligible = eligible_blocks(block, actual, baseline_pred, min_predicted)
    keep = int(len(eligible) * top_fraction)
    return list(eligible.sort_values("ratio", ascending=False, kind="stable").head(keep).index)


def cross_validate_good_areas(X, y, block, good_blocks, seed=0, with_shap=False):
    """Held-out prediction for every row from forests trained on good blocks only.

    Rows outside the good blocks are predicted by one forest fit on all good rows.
    Rows inside are predicted by GroupKFold over the good blocks, so no forest
    ever sees the block it predicts.
    """
    X, y, block = np.asarray(X), np.asarray(y), np.asarray(block)
    inside = np.isin(block, list(good_blocks))
    pred = np.zeros(len(y))
    shap_values = np.zeros(X.shape) if with_shap else None
    seen = np.zeros(len(y), dtype=int)

    def fit_predict(train, test):
        forest = make_forest(seed).fit(X[train], y[train])
        pred[test] = forest.predict(X[test])
        seen[test] += 1
        if with_shap:
            shap_values[test] = shap.TreeExplainer(forest).shap_values(X[test])

    inside_idx = np.flatnonzero(inside)
    fit_predict(inside_idx, np.flatnonzero(~inside))
    for train, test in GroupKFold(N_FOLDS).split(inside_idx, groups=block[inside_idx]):
        fit_predict(inside_idx[train], inside_idx[test])
    assert (seen == 1).all()
    return pred, shap_values


def comparison_row(name, actual, pred, in_good, baseline_candidate):
    candidate = is_candidate(pred, actual)
    row = metrics_row(name, actual, pred, pred)
    outside = ~in_good
    row.update(
        no_toilet=int((candidate & (actual == 0)).sum()),
        shortfall=int((candidate & (actual > 0)).sum()),
        max_pred=float(pred.max()),
        predicted_outside_good=float(pred[outside].sum()),
        actual_outside_good=int(actual[outside].sum()),
        overlap_with_baseline=int((candidate & baseline_candidate).sum()),
    )
    return row


def spread_table(actual, baseline_pred, good_pred):
    frame = pd.DataFrame({"toilet_count": np.minimum(actual, SPREAD_CAP),
                          "baseline": baseline_pred, "good_areas": good_pred})
    out = frame.groupby("toilet_count").agg(
        hexes=("baseline", "size"), baseline=("baseline", "mean"), good_areas=("good_areas", "mean"))
    out.index = [str(i) if i < SPREAD_CAP else f"{SPREAD_CAP}+" for i in out.index]
    return out.rename_axis("toilet_count").reset_index()


def run(seed=0, out_dir=GOOD_AREAS_DIR, review_path=GOOD_AREAS_REVIEW_PATH, today=None,
        data_file=DATA_FILE):
    start = perf_counter()
    target = TARGETS["toilets"]
    label, features = target.label, target.feature_sets["latest"]
    df = pd.read_csv(data_file)
    X, actual, block = df[features].to_numpy(), df[label].to_numpy(), block_ids(df)
    out_dir.mkdir(parents=True, exist_ok=True)

    baseline_pred, _, _ = cross_validate(df, features, label, 0)
    baseline_candidate = is_candidate(baseline_pred, actual)

    good = choose_good_blocks(block, actual, baseline_pred)
    in_good = np.isin(block, good)
    pred, shap_values = cross_validate_good_areas(X, actual, block, good, seed, with_shap=True)
    candidate = is_candidate(pred, actual)

    eligible = eligible_blocks(block, actual, baseline_pred)
    rng = np.random.default_rng(CONTROL_RNG_SEED)
    controls = []
    for i in range(N_CONTROLS):
        chosen = rng.choice(eligible.index, size=len(good), replace=False)
        control_pred, _ = cross_validate_good_areas(X, actual, block, chosen, seed)
        controls.append((f"random areas #{i + 1}", control_pred, np.isin(block, chosen)))

    comparison = pd.DataFrame(
        [comparison_row("baseline (all areas)", actual, baseline_pred, np.zeros(len(df), bool),
                        baseline_candidate),
         comparison_row("good areas only", actual, pred, in_good, baseline_candidate)]
        + [comparison_row(name, actual, p, inside, baseline_candidate) for name, p, inside in controls])
    comparison = comparison.astype({"candidates": int, "top100_hits": int})

    stability_rows = []
    for s in SEEDS:
        seed_pred = pred if s == seed else cross_validate_good_areas(X, actual, block, good, s)[0]
        mask = is_candidate(seed_pred, actual)
        common = int((mask & candidate).sum())
        stability_rows.append(dict(
            comparison=f"seed {s} vs seed {seed}", candidates=int(mask.sum()),
            in_common_with_reference=common, jaccard=common / max(int((mask | candidate).sum()), 1)))
    stability = pd.DataFrame(stability_rows)

    spread = spread_table(actual, baseline_pred, pred)
    seifa = df[SEIFA_COLUMN]
    fairness = pd.concat(
        [fairness_table(seifa, p, actual, is_candidate(p, actual)).assign(model=name)
         for name, p in [("baseline", baseline_pred), ("good areas", pred)]], ignore_index=True)
    fairness = fairness[["model"] + [c for c in fairness.columns if c != "model"]]

    chosen_blocks = block_table(block, actual, baseline_pred).loc[good]
    chosen_blocks[["lat", "lng"]] = [[round(c, 5) for c in h3.cell_to_latlng(b)] for b in chosen_blocks.index]
    chosen_blocks = chosen_blocks.sort_values("ratio", ascending=False).reset_index()

    drivers = top_drivers(shap_values, features)
    hexes = pd.DataFrame({
        "hex_id": df["hex_id"], label: actual, "baseline_pred": baseline_pred,
        "good_areas_pred": pred, "gap": pred - actual, "is_candidate": candidate,
        "kind": np.where(candidate, candidate_kind(actual), ""),
        "in_good_block": in_good, "top_drivers": drivers})

    for name, table in [("comparison", comparison), ("spread", spread), ("fairness", fairness),
                        ("stability", stability), ("good_blocks", chosen_blocks),
                        ("hex_predictions", hexes)]:
        table.to_csv(out_dir / f"{name}.csv", index=False)

    found = hexes[candidate].rename(columns={"good_areas_pred": "predicted_toilets"}).copy()
    found["p_any_toilet"] = p_any(found["predicted_toilets"])
    found[["lat", "lng"]] = [[round(c, 5) for c in h3.cell_to_latlng(i)] for i in found["hex_id"]]
    for col in ("predicted_toilets", "p_any_toilet"):
        found[col] = found[col].round(4)
    review = merge_review(load_review(review_path), found,
                          today or pd.Timestamp.today().date().isoformat())
    save_review(review, review_path)

    fmt = lambda x: f"{x:.4f}"
    block_summary = (f"{len(good)} of {len(eligible)} eligible blocks chosen ({int(in_good.sum())} hexes): "
                     f"actual {int(chosen_blocks['actual'].sum())} vs baseline predicted "
                     f"{chosen_blocks['baseline_pred'].sum():.0f}")
    seifa_view = fairness[["model", "group", "hexes", "actual_toilets", "predicted_toilets",
                           "candidates", "candidates_per_1000_hexes"]]
    return "\n".join([
        f"Good-areas experiment (seed {seed}); not production. Production review file untouched.",
        block_summary,
        f"\n== Comparison (out-of-fold) ==\n{comparison.to_string(index=False, float_format=fmt)}",
        f"\n== Mean prediction by real toilet count ==\n{spread.to_string(index=False, float_format=fmt)}",
        f"\n== Stability across seeds ==\n{stability.to_string(index=False, float_format=fmt)}",
        "\n== Fairness by SEIFA decile (1 = most disadvantaged) ==\n"
        + seifa_view.to_string(index=False, float_format=lambda x: f"{x:.1f}"),
        f"\nCandidates: {int(candidate.sum())} ({int((candidate & (actual == 0)).sum())} no_toilet, "
        f"{int((candidate & (actual > 0)).sum())} shortfall); review rows: {len(review)}; "
        f"runtime: {perf_counter() - start:.0f}s",
    ])
