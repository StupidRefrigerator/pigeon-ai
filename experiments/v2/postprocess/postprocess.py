"""Post-processing steps that re-rank PIGEON-AI toilet predictions.

Both steps are pure: they take per-hex arrays and return a per-hex DataFrame.
They never touch the model, so they work on any model variant's predictions.

    coverage_step  400 m walking coverage from existing toilets (H3 grid-disk)
    equity_step    SEIFA disadvantage weighting
    priority       gap x (1 + w x disadvantage) [x uncovered]
"""
import h3
import numpy as np
import pandas as pd

# Mean centroid-to-centroid distance between neighbouring res-9 hexes, measured in Sydney.
RES9_SPACING_M = 382.0


def gap(predicted, actual):
    """Toilets the model expects beyond those that exist, floored at 0."""
    return np.maximum(0.0, np.asarray(predicted, float) - np.asarray(actual, float))


def rings_for_walk(walk_m=400.0, circuity=1.3, spacing_m=RES9_SPACING_M):
    """Grid-disk radius k that best matches a walking distance.

    Walking distance / circuity gives straight-line distance; divide by the
    neighbour spacing and round. 400 m / 1.3 = 308 m -> 0.81 -> k = 1.
    """
    return int(round(walk_m / circuity / spacing_m))


def covered_hexes(toilet_hexes, k=1):
    """Every hex within k rings of a hex that has a toilet."""
    out = set()
    for h in set(toilet_hexes):
        out.update(h3.grid_disk(h, k))
    return out


def coverage_step(hex_ids, predicted, actual, extra_toilet_hexes=(), k=1):
    """Flag hexes with no existing toilet within k rings.

    Existing toilets = hexes with actual > 0, plus `extra_toilet_hexes`
    (for example OpenStreetMap public toilets). Returns one row per hex with
    gap, has_toilet, uncovered and coverage_score = gap x uncovered.
    """
    hex_ids = pd.Index(hex_ids)
    actual = np.asarray(actual, float)
    existing = set(hex_ids[actual > 0]) | set(extra_toilet_hexes)
    cov = covered_hexes(existing, k)
    g = gap(predicted, actual)
    uncovered = ~hex_ids.isin(cov)
    return pd.DataFrame({
        "hex_id": hex_ids, "gap": g,
        "has_toilet": hex_ids.isin(existing), "uncovered": uncovered,
        "coverage_score": g * uncovered,
    })


def seifa_disadvantage(seifa_score, missing="mean"):
    """(11 - decile) / 10, deciles cut over the hexes given. Decile 1 -> 1.0, 10 -> 0.1.

    Hexes without a SEIFA score get the mean disadvantage (neutral: no boost
    and no penalty against the average), or `missing` if it is a number.
    Returns (decile, disadvantage); decile is NaN where SEIFA is missing.
    """
    s = pd.Series(np.asarray(seifa_score, float))
    decile = pd.Series(np.nan, index=s.index)
    known = s.notna()
    decile[known] = pd.qcut(s[known], 10, labels=False) + 1
    dis = (11 - decile) / 10
    fill = dis.mean() if missing == "mean" else float(missing)
    return decile.to_numpy(), dis.fillna(fill).to_numpy()


def equity_step(hex_ids, predicted, actual, seifa_score, w=1.0):
    """equity_score = gap x (1 + w x disadvantage)."""
    decile, dis = seifa_disadvantage(seifa_score)
    g = gap(predicted, actual)
    return pd.DataFrame({
        "hex_id": pd.Index(hex_ids), "gap": g, "seifa_decile": decile,
        "disadvantage": dis, "equity_score": g * (1 + w * dis),
    })


def priority(hex_ids, predicted, actual, *, seifa_score=None, w=0.0,
             coverage=False, extra_toilet_hexes=(), k=1):
    """Both steps combined: gap x (1 + w x disadvantage) x (uncovered if coverage).

    Returns per-hex columns from both steps plus `priority` and `rank`
    (1 = best; ties broken by hex_id so lists are reproducible).
    """
    out = coverage_step(hex_ids, predicted, actual, extra_toilet_hexes, k)
    out["priority"] = out["gap"]
    if seifa_score is not None:
        eq = equity_step(hex_ids, predicted, actual, seifa_score, w)
        out[["seifa_decile", "disadvantage"]] = eq[["seifa_decile", "disadvantage"]].to_numpy()
        out["priority"] = eq["equity_score"].to_numpy()
    elif w:
        raise ValueError("w > 0 needs seifa_score")
    if coverage:
        out["priority"] = out["priority"] * out["uncovered"]
    order = out.sort_values(["priority", "hex_id"], ascending=[False, True]).index
    out.loc[order, "rank"] = np.arange(1, len(out) + 1)
    out["rank"] = out["rank"].astype(int)
    return out


def top_n(scored, n=120):
    """The n best-ranked hexes with priority > 0."""
    s = scored[scored["priority"] > 0].sort_values("rank")
    return s.head(n)


def coverage_summary(uncovered, population):
    """Share of hexes and of population that is uncovered."""
    u = np.asarray(uncovered, bool)
    pop = np.asarray(population, float)
    return {
        "hexes": int(u.size), "uncovered_hexes": int(u.sum()), "uncovered_hex_share": u.mean(),
        "population": pop.sum(), "uncovered_population": pop[u].sum(),
        "uncovered_population_share": pop[u].sum() / pop.sum(),
    }


def newly_covered_population(pick_hexes, uncovered_hex_ids, population_by_hex, k=1):
    """Population in currently uncovered hexes that a toilet in each pick would cover."""
    reach = covered_hexes(pick_hexes, k) & set(uncovered_hex_ids)
    return float(population_by_hex.reindex(list(reach)).fillna(0).sum())


__all__ = [
    "gap", "rings_for_walk", "covered_hexes", "coverage_step", "seifa_disadvantage",
    "equity_step", "priority", "top_n", "coverage_summary", "newly_covered_population",
]
