"""Model behaviour on small synthetic data; no real dataset needed."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import h3
import numpy as np
import pandas as pd
import pytest

from pigeon_ai.model import (
    REVIEW_COLUMNS, TARGETS, ReviewStatus, cross_validate, is_candidate, load_review, merge_review,
    save_review,
)


def synthetic_hexes(per_block=60):
    blocks = sorted(h3.grid_disk(h3.latlng_to_cell(-33.87, 151.2, 6), 1))
    ids = [c for b in blocks for c in sorted(h3.cell_to_children(b, 9))[:per_block]]
    rng = np.random.default_rng(0)
    shops = rng.poisson(1.0, len(ids))
    return pd.DataFrame({
        "hex_id": ids, "toilet_count": rng.poisson(0.1 + 0.3 * shops),
        "shop_500m": shops, "park_area_inside_m2": rng.uniform(0, 5000, len(ids)),
    })


def test_every_hex_predicted_once_and_blocks_never_split_across_folds():
    df = synthetic_hexes()
    pred, fold, _ = cross_validate(df, ["shop_500m", "park_area_inside_m2"], "toilet_count")
    assert len(pred) == len(df) and np.isfinite(pred).all()
    assert set(fold) == set(range(5))
    parent = pd.Series([h3.cell_to_parent(h, 6) for h in df["hex_id"]])
    assert (pd.DataFrame({"parent": parent, "fold": fold}).groupby("parent")["fold"].nunique() == 1).all()


def candidates(*rows):
    return pd.DataFrame(
        [dict(hex_id=h, lat=0.0, lng=0.0, toilet_count=0, kind="no_toilet", predicted_toilets=p, p_any_toilet=0.5, top_drivers=d)
         for h, p, d in rows])


def test_merge_keeps_human_fields_appends_new_and_is_idempotent(tmp_path):
    path = tmp_path / "review.csv"
    first = merge_review(load_review(path), candidates(("a", 1.5, "x +1"), ("b", 1.2, "y +1")), "2026-11-02")
    save_review(first, path)

    reviewed = load_review(path)
    reviewed.loc[reviewed.hex_id == "a", ["status", "reviewer", "notes"]] = [
        ReviewStatus.REAL_GAP.value, "sam", "busy park"]
    save_review(reviewed, path)

    later = candidates(("a", 2.0, "z +2"), ("c", 1.1, "w +1"))
    second = merge_review(load_review(path), later, "2026-12-01")
    save_review(second, path)
    row = lambda h: second.set_index("hex_id").loc[h]
    assert row("a").status == "real_gap" and row("a").notes == "busy park" and row("a").reviewer == "sam"
    assert row("a").predicted_toilets == 2.0 and row("a").top_drivers == "z +2"
    assert row("a").first_flagged == "2026-11-02"
    assert row("b").status == "unreviewed" and not row("b").still_candidate
    assert row("c").status == "unreviewed" and row("c").first_flagged == "2026-12-01"
    assert list(second.columns) == REVIEW_COLUMNS

    before = path.read_text()
    save_review(merge_review(load_review(path), later, "2027-01-01"), path)
    assert path.read_text() == before


def test_loading_unknown_status_names_the_value_and_row(tmp_path):
    path = tmp_path / "review.csv"
    review = merge_review(load_review(path), candidates(("a", 1.5, "x"), ("b", 1.2, "y")), "2026-11-02")
    review.loc[1, "status"] = "maybe"
    save_review(review, path)
    with pytest.raises(ValueError, match="maybe") as error:
        load_review(path)
    assert "row 3" in str(error.value)


def test_feature_sets_hold_no_label_identifier_or_sensitive_columns():
    banned = ("seifa", "age_", "household", "projected", "growth", "council", "hex_id")
    for target in TARGETS.values():
        for features in target.feature_sets.values():
            assert target.label not in features
            assert len(features) == len(set(features))
            assert not [f for f in features if any(b in f for b in banned)]
            assert not {"lat", "lng", "lon"} & set(features)


def test_candidates_are_empty_hexes_or_shortfalls_of_at_least_the_threshold():
    pred = np.array([1.0, 0.9, 2.1, 1.5, 3.2])
    actual = np.array([0, 0, 1, 1, 2])
    assert is_candidate(pred, actual, 1.0).tolist() == [True, False, True, False, True]
