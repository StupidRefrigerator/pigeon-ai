import h3
import numpy as np
import pandas as pd
import pytest

from postprocess import (coverage_step, coverage_summary, gap, newly_covered_population,
                         priority, rings_for_walk, seifa_disadvantage, top_n)

CENTRE = h3.latlng_to_cell(-33.87, 151.21, 9)
RING1 = sorted(h3.grid_ring(CENTRE, 1))
RING2 = sorted(h3.grid_ring(CENTRE, 2))
HEXES = [CENTRE] + RING1 + RING2  # 19 hexes


def test_gap_floors_at_zero():
    assert gap([2.5, 0.2, 1.0], [1, 1, 0]).tolist() == [1.5, 0.0, 1.0]


def test_rings_for_walk():
    assert rings_for_walk(400) == 1
    assert rings_for_walk(0) == 0
    assert rings_for_walk(1000) == 2


def test_toilet_covers_its_ring_only():
    actual = [1] + [0] * 18
    out = coverage_step(HEXES, [0] * 19, actual, k=1)
    assert out.loc[out.hex_id.isin([CENTRE] + RING1), "uncovered"].sum() == 0
    assert out.loc[out.hex_id.isin(RING2), "uncovered"].all()
    assert coverage_step(HEXES, [0] * 19, actual, k=0).uncovered.sum() == 18


def test_extra_toilets_add_coverage():
    actual = [0] * 19
    assert coverage_step(HEXES, [0] * 19, actual).uncovered.all()
    out = coverage_step(HEXES, [0] * 19, actual, extra_toilet_hexes=[CENTRE])
    assert out.uncovered.sum() == 12
    assert out.set_index("hex_id").at[CENTRE, "has_toilet"]


def test_coverage_score_zero_when_covered():
    pred = [3] * 19
    actual = [1] + [0] * 18
    out = coverage_step(HEXES, pred, actual).set_index("hex_id")
    assert out.at[RING1[0], "coverage_score"] == 0
    assert out.at[RING2[0], "coverage_score"] == 3


def test_seifa_disadvantage_deciles_and_missing():
    seifa = list(range(100)) + [np.nan]
    dec, dis = seifa_disadvantage(seifa)
    assert dec[0] == 1 and dec[99] == 10 and np.isnan(dec[100])
    assert dis[0] == 1.0 and dis[99] == pytest.approx(0.1)
    assert dis[100] == pytest.approx(np.mean(dis[:100]))


def test_equity_weight_reorders_equal_gaps():
    hexes = HEXES[:10]
    pred = [2.0] * 10
    actual = [0] * 10
    seifa = np.arange(10) * 10.0  # hexes[0] most disadvantaged
    base = priority(hexes, pred, actual, seifa_score=seifa, w=0)
    weighted = priority(hexes, pred, actual, seifa_score=seifa, w=1)
    assert base.priority.nunique() == 1
    assert weighted.set_index("hex_id").at[hexes[0], "rank"] == 1
    assert weighted.set_index("hex_id").at[hexes[0], "priority"] == pytest.approx(4.0)


def test_priority_coverage_drops_covered_from_top_n():
    pred = [5.0] * 19
    actual = [1] + [0] * 18
    picks = top_n(priority(HEXES, pred, actual, coverage=True), n=50)
    assert set(picks.hex_id) == set(RING2)


def test_summary_and_newly_covered_population():
    pop = pd.Series(10.0, index=HEXES)
    actual = [1] + [0] * 18
    cov = coverage_step(HEXES, [0] * 19, actual)
    s = coverage_summary(cov.uncovered, pop.to_numpy())
    assert s["uncovered_hexes"] == 12 and s["uncovered_population_share"] == pytest.approx(12 / 19)
    uncovered = cov.hex_id[cov.uncovered]
    got = newly_covered_population([RING2[0]], uncovered, pop)
    reach = (set(h3.grid_disk(RING2[0], 1)) & set(uncovered))
    assert got == 10.0 * len(reach)
