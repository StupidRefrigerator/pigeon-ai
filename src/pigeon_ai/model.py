"""Toilet-placement model: spatial CV, SHAP, candidates, evals and the review file."""
from dataclasses import dataclass
from enum import StrEnum
from time import perf_counter

import h3
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import shap
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import average_precision_score, mean_poisson_deviance
from sklearn.model_selection import GroupKFold
from sklearn.tree import DecisionTreeRegressor, plot_tree

from .accessibility import ACCESSIBILITY_FEATURES
from .experiments import EXTENDED_FEATURES
from .paths import PROCESSED, ROOT
from .validation import FEATURES

DATA_FILE = PROCESSED / "sydney_extended_features.csv"
MODEL_DIR = ROOT / "data/model"
REVIEW_PATH = ROOT / "data/review/candidate_review.csv"

THRESHOLD = 1.0
SEEDS = (0, 1, 2)
BLOCK_RESOLUTION = 6
N_FOLDS = 5
MIN_PREDICTION = 1e-6
SEIFA_COLUMN = "seifa_irsd_score"
POPULATION_ONLY = ["population_est", "population_250m", "population_500m"]
CALIBRATION_BINS = [0, 0.1, 0.25, 0.5, 1, 1.5, np.inf]


@dataclass(frozen=True)
class Target:
    label: str
    feature_sets: dict[str, list[str]]


# Each infrastructure type lists its own inputs so a future target can omit
# columns that would leak its label (a parks target would drop park_*).
_V1 = [f for f in FEATURES if f != "population_density"]
TARGETS = {
    "toilets": Target(
        label="toilet_count",
        feature_sets={
            "v1": _V1,
            "latest": _V1 + EXTENDED_FEATURES[len(FEATURES):] + ACCESSIBILITY_FEATURES,
        },
    ),
}


class ReviewStatus(StrEnum):
    UNREVIEWED = "unreviewed"
    REAL_GAP = "real_gap"
    TOILET_NOT_ON_MAP = "toilet_not_on_map"
    NOT_PUBLIC_PLACE = "not_public_place"


REVIEW_COLUMNS = [
    "hex_id", "lat", "lng", "predicted_toilets", "p_any_toilet", "top_drivers",
    "first_flagged", "status", "reviewer", "reviewed_on", "notes", "still_candidate",
]
MODEL_OUTPUTS = ["predicted_toilets", "p_any_toilet", "top_drivers"]


# Modelling

def make_forest(seed):
    return RandomForestRegressor(
        n_estimators=300, min_samples_leaf=20, max_features=0.5, n_jobs=-1, random_state=seed
    )


def cross_validate(df, features, label, seed=0, with_shap=False):
    """Out-of-fold predictions grouped by res-6 parent, so no block spans train and test."""
    X, y = df[features].to_numpy(), df[label].to_numpy()
    groups = [h3.cell_to_parent(h, BLOCK_RESOLUTION) for h in df["hex_id"]]
    pred = np.zeros(len(df))
    fold = np.zeros(len(df), dtype=int)
    shap_values = np.zeros(X.shape) if with_shap else None
    for k, (train, test) in enumerate(GroupKFold(n_splits=N_FOLDS).split(X, y, groups)):
        forest = make_forest(seed).fit(X[train], y[train])
        pred[test], fold[test] = forest.predict(X[test]), k
        if with_shap:
            shap_values[test] = shap.TreeExplainer(forest).shap_values(X[test])
    return pred, fold, shap_values


def top_drivers(shap_values, features, n=3):
    order = np.argsort(-np.abs(shap_values), axis=1, kind="stable")[:, :n]
    return [
        "; ".join(f"{features[j]} {row[j]:+.2f}" for j in idx)
        for row, idx in zip(shap_values, order)
    ]


def is_candidate(pred, actual, threshold=THRESHOLD):
    return (pred >= threshold) & (actual == 0)


def p_any(pred):
    return 1 - np.exp(-pred)


# Evals

def top_hits(score, actual, n=100):
    return int((actual[np.argsort(-score, kind="stable")[:n]] > 0).sum())


def metrics_row(name, actual, pred=None, ranking=None, threshold=THRESHOLD):
    """Fill only the metrics that mean something for this kind of model."""
    row = dict(model=name, deviance=np.nan, pr_auc=np.nan, predicted_total=np.nan,
               actual_total=int(actual.sum()), top100_hits=np.nan, candidates=np.nan)
    if pred is not None:
        pred = np.clip(pred, MIN_PREDICTION, None)
        row.update(deviance=mean_poisson_deviance(actual, pred), predicted_total=pred.sum(),
                   candidates=int(is_candidate(pred, actual, threshold).sum()))
    if ranking is not None:
        row.update(pr_auc=average_precision_score(actual > 0, ranking),
                   top100_hits=top_hits(ranking, actual))
    return row


def calibration_table(pred, actual):
    bands = pd.cut(np.clip(pred, MIN_PREDICTION, None), CALIBRATION_BINS)
    frame = pd.DataFrame({"band": bands, "pred": pred, "actual": actual})
    out = frame.groupby("band", observed=False).agg(
        hexes=("pred", "size"), mean_predicted=("pred", "mean"), mean_actual=("actual", "mean"))
    out.index = out.index.astype(str)
    return out.rename_axis("band").reset_index()


def fold_table(pred, actual, fold):
    rows = []
    for k in sorted(set(fold)):
        m = fold == k
        rows.append(dict(
            fold=k, hexes=int(m.sum()), toilets=int(actual[m].sum()),
            deviance=mean_poisson_deviance(actual[m], np.clip(pred[m], MIN_PREDICTION, None)),
            pr_auc=average_precision_score(actual[m] > 0, pred[m])))
    return pd.DataFrame(rows)


def stability_row(name, mask, reference):
    common = int((mask & reference).sum())
    return dict(comparison=name, candidates=int(mask.sum()), in_common_with_reference=common,
                jaccard=common / max(int((mask | reference).sum()), 1))


def fairness_table(seifa, pred, actual, candidate):
    """SEIFA is used here only to audit the output, never as a model input."""
    group = pd.Series("unknown", index=seifa.index, dtype=object)
    known = seifa.notna()
    group[known] = pd.qcut(seifa[known], 10, labels=range(1, 11)).astype(str)
    frame = pd.DataFrame({"group": group, "actual": actual, "pred": pred, "cand": candidate})
    out = frame.groupby("group").agg(
        hexes=("actual", "size"), actual_toilets=("actual", "sum"),
        predicted_toilets=("pred", "sum"), candidates=("cand", "sum"))
    out["pred_actual_ratio"] = out["predicted_toilets"] / out["actual_toilets"].replace(0, np.nan)
    out["candidates_per_1000_hexes"] = 1000 * out["candidates"] / out["hexes"]
    order = [str(d) for d in range(1, 11)] + ["unknown"]
    return out.reindex([g for g in order if g in out.index]).reset_index()


def readable(name):
    return name.replace("_m2", " (m2)").replace("_", " ")


def save_surrogate_plot(df, features, oof_pred, path):
    tree = DecisionTreeRegressor(max_depth=3).fit(df[features], oof_pred)
    fig, ax = plt.subplots(figsize=(16, 8))
    plot_tree(tree, feature_names=[readable(f) for f in features], filled=True,
              rounded=True, precision=2, fontsize=9, ax=ax)
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return tree.score(df[features], oof_pred)


# Review file

def load_review(path):
    """Read the review file, rejecting any status outside ReviewStatus."""
    if not path.exists():
        return pd.DataFrame({c: pd.Series(dtype=object) for c in REVIEW_COLUMNS})
    review = pd.read_csv(path, dtype=str, keep_default_na=False)
    allowed = ", ".join(s.value for s in ReviewStatus)
    for i, (hex_id, status) in enumerate(zip(review["hex_id"], review["status"])):
        if status not in set(ReviewStatus):
            raise ValueError(
                f"{path}: row {i + 2} (hex {hex_id}) has invalid status {status!r}; "
                f"allowed: {allowed}")
    for col in ("predicted_toilets", "p_any_toilet"):
        review[col] = review[col].astype(float)
    review["still_candidate"] = review["still_candidate"] == "True"
    return review[REVIEW_COLUMNS]


def merge_review(existing, candidates, today):
    """Idempotent merge. Human fields are never touched; stale rows are kept and flagged."""
    review = existing.set_index("hex_id")
    current = candidates.set_index("hex_id")
    known = current.index.intersection(review.index)
    review.loc[known, MODEL_OUTPUTS] = current.loc[known, MODEL_OUTPUTS]
    review["still_candidate"] = review.index.isin(current.index)
    new = current.drop(known).sort_values("predicted_toilets", ascending=False)
    new = new.assign(first_flagged=today, status=ReviewStatus.UNREVIEWED.value,
                     reviewer="", reviewed_on="", notes="", still_candidate=True)
    return pd.concat([review, new[review.columns]]).rename_axis("hex_id").reset_index()[REVIEW_COLUMNS]


def save_review(review, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    review.to_csv(path, index=False)


def review_progress(review):
    counts = review["status"].value_counts().reindex([s.value for s in ReviewStatus], fill_value=0)
    reviewed = int(counts.sum() - counts[ReviewStatus.UNREVIEWED])
    share = counts[ReviewStatus.REAL_GAP] / reviewed if reviewed else None
    return counts, reviewed, share


# Pipeline

def run(target_name="toilets", feature_set="latest", threshold=THRESHOLD, today=None,
        out_dir=MODEL_DIR, review_path=REVIEW_PATH, data_file=DATA_FILE):
    start = perf_counter()
    target = TARGETS[target_name]
    label, features = target.label, target.feature_sets[feature_set]
    other_set = next(s for s in target.feature_sets if s != feature_set)
    df = pd.read_csv(data_file)
    actual = df[label].to_numpy()
    out_dir.mkdir(parents=True, exist_ok=True)

    t = perf_counter()
    pred, fold, shap_values = cross_validate(df, features, label, 0, with_shap=True)
    main_seconds = perf_counter() - t
    candidate = is_candidate(pred, actual, threshold)

    seed_masks = {0: candidate}
    for seed in SEEDS[1:]:
        seed_pred, _, _ = cross_validate(df, features, label, seed)
        seed_masks[seed] = is_candidate(seed_pred, actual, threshold)
    other_pred, _, _ = cross_validate(df, target.feature_sets[other_set], label, 0)
    pop_pred, _, _ = cross_validate(df, POPULATION_ONLY, label, 0)

    drivers = top_drivers(shap_values, features)
    hexes = pd.DataFrame({
        "hex_id": df["hex_id"], label: actual, "predicted_toilets": pred,
        "p_any_toilet": p_any(pred), "gap": pred - actual, "is_candidate": candidate,
        "fold": fold, "top_drivers": drivers})
    hexes.to_csv(out_dir / "hex_predictions.csv", index=False)

    importance = pd.DataFrame({"feature": features, "mean_abs_shap": np.abs(shap_values).mean(axis=0)})
    importance = importance.sort_values("mean_abs_shap", ascending=False)
    importance.to_csv(out_dir / "feature_importance.csv", index=False)

    mean_pred = np.full(len(df), actual.mean())
    metrics = pd.DataFrame([
        metrics_row(f"forest {feature_set}", actual, pred, pred, threshold),
        metrics_row(f"forest {other_set}", actual, other_pred, other_pred, threshold),
        metrics_row("forest population only", actual, pop_pred, pop_pred, threshold),
        metrics_row("mean everywhere", actual, mean_pred, None, threshold),
        metrics_row("rank by shop_500m", actual, None, df["shop_500m"].to_numpy(), threshold),
    ]).astype({"top100_hits": "Int64", "candidates": "Int64"})
    calibration = calibration_table(pred, actual)
    folds = fold_table(pred, actual, fold)
    stability = pd.DataFrame(
        [stability_row("seed 0 (reference)", candidate, candidate)]
        + [stability_row(f"seed {s} vs seed 0", seed_masks[s], candidate) for s in SEEDS[1:]]
        + [stability_row(f"{other_set} vs {feature_set} (seed 0)",
                         is_candidate(other_pred, actual, threshold), candidate)])
    fairness = fairness_table(df[SEIFA_COLUMN], pred, actual, candidate)
    for name, table in [("metrics", metrics), ("calibration", calibration), ("folds", folds),
                        ("stability", stability), ("fairness", fairness)]:
        table.to_csv(out_dir / f"{name}.csv", index=False)
    surrogate_r2 = save_surrogate_plot(df, features, pred, out_dir / "decision_tree.png")

    found = hexes[candidate].copy()
    found[["lat", "lng"]] = [[round(c, 5) for c in h3.cell_to_latlng(i)] for i in found["hex_id"]]
    for col in ("predicted_toilets", "p_any_toilet"):
        found[col] = found[col].round(4)
    review = load_review(review_path)
    # Only the default configuration owns the review file; experiments must not
    # mark reviewed candidates as stale or add their own.
    if (target_name, feature_set, threshold) == ("toilets", "latest", THRESHOLD):
        review = merge_review(review, found, today or pd.Timestamp.today().date().isoformat())
        save_review(review, review_path)
    else:
        print(f"Experiment run: {review_path.name} left unchanged.")
    counts, reviewed, share = review_progress(review)

    def block(title, table, **kw):
        return f"\n== {title} ==\n{table.to_string(index=False, **kw)}"

    fmt = lambda x: f"{x:.4f}"
    share_text = "n/a (none reviewed)" if share is None else f"{share:.1%} ({counts['real_gap']}/{reviewed})"
    parts = [
        f"Target: {target_name} ({label}); features: {feature_set} ({len(features)} columns); "
        f"threshold: {threshold}; spatial CV: {N_FOLDS} folds by res-{BLOCK_RESOLUTION} block",
        f"SHAP computed for all {len(df)} held-out rows (main CV incl. SHAP: {main_seconds:.0f}s).",
        block("Headline metrics (out-of-fold)", metrics, float_format=fmt),
        block("Calibration bands", calibration, float_format=fmt),
        block("Per-fold", folds, float_format=fmt),
        block("Stability (candidate overlap with reference)", stability, float_format=fmt),
        block("Fairness audit by SEIFA IRSD decile (1 = most disadvantaged, 10 = least; "
              "SEIFA never used as an input)", fairness, float_format=lambda x: f"{x:.2f}"),
        block("Feature importance (mean |SHAP|)", importance, float_format=fmt),
        f"\nSurrogate depth-3 tree R^2 vs forest predictions: {surrogate_r2:.3f}",
        "\n== Review progress ==\n" + counts.to_string()
        + f"\nShare of reviewed candidates that are real gaps: {share_text}",
        f"\nCandidates this run: {int(candidate.sum())}; review rows: {len(review)}; "
        f"runtime: {perf_counter() - start:.0f}s",
    ]
    return "\n".join(parts)
