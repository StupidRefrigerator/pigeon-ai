"""Good-areas experiment on small synthetic data."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import numpy as np
import pytest

from pigeon_ai import good_areas
from pigeon_ai.good_areas import choose_good_blocks, cross_validate_good_areas


def test_choose_good_blocks_takes_highest_ratio_and_skips_small_blocks():
    # Nine blocks of 10 hexes. Block i has actual 10 * i toilets against 10 expected,
    # except "tiny", which has a huge ratio but only 2 expected toilets.
    names = [f"b{i}" for i in range(1, 10)]
    block = np.array([n for n in names for _ in range(10)] + ["tiny"] * 2)
    actual = np.array([i for i in range(1, 10) for _ in range(10)] + [50, 50])
    pred = np.array([1.0] * 90 + [1.0, 1.0])
    assert choose_good_blocks(block, actual, pred) == ["b9", "b8", "b7"]
    assert "tiny" not in choose_good_blocks(block, actual, pred, top_fraction=1)


def test_good_area_predictions_cover_every_row_and_never_use_own_block(monkeypatch):
    blocks = [f"b{i}" for i in range(8)]
    block = np.array([b for b in blocks for _ in range(20)])
    X = np.arange(len(block), dtype=float).reshape(-1, 1)
    y = np.array([i for i in range(8) for _ in range(20)], dtype=float)
    good = blocks[:6]

    fits = []
    real_forest = good_areas.make_forest

    def spy(seed):
        forest = real_forest(seed)
        original = forest.fit

        def fit(X_train, y_train):
            fits.append(set(X_train[:, 0].astype(int)))
            return original(X_train, y_train)

        forest.fit = fit
        return forest

    monkeypatch.setattr(good_areas, "make_forest", spy)
    pred, shap_values = cross_validate_good_areas(X, y, block, good)
    assert shap_values is None
    assert pred.shape == y.shape and np.isfinite(pred).all()

    assert len(fits) == 6  # one forest for the outside rows, five folds inside
    rows_of = lambda b: set(np.flatnonzero(block == b))
    # Every forest trained on good rows only; a forest never saw a block it predicted.
    outside = set(np.flatnonzero(~np.isin(block, good)))
    assert all(f <= set(np.flatnonzero(np.isin(block, good))) for f in fits)
    for b in blocks:
        predicting = [f for f in fits if not (f & rows_of(b))]
        assert predicting, f"no forest excluded block {b}"
    # Labels equal the block number, so outside blocks must be predicted from the good range.
    assert pred[list(outside)].max() <= 5
