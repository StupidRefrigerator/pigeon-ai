# Post-processing: 400 m coverage and equity weighting

Two steps that re-rank the toilet model's suggested spots after the model runs. The model is not retrained. All numbers come from the original model's held-out 5-fold spatial-CV predictions (`data/model/hex_predictions.csv`, 16,228 hexes, 120 candidates).

| File | Contents |
|---|---|
| `postprocess.py` | The two steps as pure functions. |
| `test_postprocess.py` | 9 tests on a synthetic 19-hex patch. Run `/tmp/pigeon-env/bin/python -m pytest -q`. |
| `evaluate.py` | Builds every table below. Run `/tmp/pigeon-env/bin/python evaluate.py [repo path]`. |
| `results.csv` | One row per variant, all metrics. |
| `picks.csv` | The top 120 of every variant, with suburb, gap, decile and coverage flag. |
| `coverage.csv` | Uncovered share of hexes and population, for both toilet sources and for k = 0 and k = 1. |
| `coverage_by_area.csv` | Coverage per suburb (rough names: nearest ABS suburb point). |

## How to reuse the functions on a new model

Every function takes `hex_ids, predicted, actual`, plus its own extra inputs, and returns one row per hex.

```python
from postprocess import coverage_step, equity_step, priority, top_n

cov = coverage_step(hex_ids, predicted, actual, extra_toilet_hexes=osm_hexes, k=1)
# -> hex_id, gap, has_toilet, uncovered, coverage_score (= gap x uncovered)

eq = equity_step(hex_ids, predicted, actual, seifa_irsd_score, w=1)
# -> hex_id, gap, seifa_decile, disadvantage, equity_score (= gap x (1 + w x disadvantage))

ranked = priority(hex_ids, predicted, actual, seifa_score=seifa_irsd_score, w=1,
                  coverage=False, extra_toilet_hexes=(), k=1)
picks = top_n(ranked, 120)
```

- `gap = max(0, predicted − actual)`.
- `disadvantage = (11 − SEIFA IRSD decile) / 10`. Deciles are cut over the hexes passed in, the same way as the fairness audit in `src/pigeon_ai/model.py`. Decile 1 (most disadvantaged) gives 1.0, and decile 10 gives 0.1. 2,392 hexes (435,027 residents) have no SEIFA score. They get the mean disadvantage, so they are neither boosted nor penalised.
- `extra_toilet_hexes` adds toilets from another source, such as OpenStreetMap. Hexes with `actual > 0` always count as having a toilet.

## Step 1: 400 m walking coverage

### Method: H3 grid disk, k = 1

A hex is **covered** if it or one of its 6 neighbours has a toilet. There is no street network or toilet point data offline (`data/raw/` is absent), so coverage works from hex to hex. `rings_for_walk(400, circuity=1.3)` turns walking metres into k: 400 m ÷ 1.3 = 308 m straight-line, ÷ 382 m (the measured spacing between neighbouring hex centres in Sydney) = 0.81, which rounds to k = 1.

Why k = 1 and not the 310 m centroid buffer: neighbouring hex centres are 382 m apart, so a 310 m buffer around a centre reaches no other centre. It collapses to k = 0, which means "no toilet in this 0.1 km² hex". I measured both by sampling random points:

| | k = 0 (same hex only) | k = 1 (hex + 6 neighbours) |
|---|---|---|
| Resident-to-toilet pairs within 308 m straight line | 92.5% inside the same hex | Only 25% for a toilet in a neighbour hex (mean 409 m straight line, about 530 m walking) |
| Hexes uncovered (official toilets) | 14,317/16,228 (88.2%) | 8,731/16,228 (53.8%) |
| Residents uncovered (official toilets) | 3,637,699/4,491,614 (81.0%) | 1,471,429/4,491,614 (32.8%) |

k = 0 calls most of Sydney uncovered, including people who live next door to a toilet. With k = 1, "uncovered" is a safe claim: no point in the hex is within 220 m straight-line of a listed toilet, and the typical walk is about 1 km. k = 1 is generous about what counts as covered (up to about 500 m walking), so the uncovered shares here are a lower bound for a strict 400 m target. It also matches the 1-ring rule used for planned council sites. `k` is a parameter.

### Results

| Existing toilets | Hexes uncovered | Residents uncovered |
|---|---|---|
| Official only (1,911 hexes with toilets) | 8,731/16,228 (53.8%) | 1,471,429/4,491,614 (32.8%) |
| Official + OSM public toilets (+ OSM hexes) | 8,587/16,228 (52.9%) | 1,414,360/4,491,614 (31.5%) |

- OSM data exists only for the 1,199 + 315 hexes checked in `experiments/validity/` (busy hexes and candidates), not all of Sydney. The OSM row is a partial correction. A full Overpass pull would cover more.
- **Central Sydney** (Sydney, Haymarket, The Rocks, Millers Point, Dawes Point, Barangaroo): 0/15 hexes uncovered. The CBD already meets the City of Sydney 400 m target at this resolution.
- Most uncovered residents live in the outer suburbs. The top 5 by uncovered residents are Cherrybrook (16,543, 66% of its residents), Baulkham Hills (13,650, 50%), Glenhaven (13,047, 92%), Castle Hill (12,994, 51%) and North Kellyville (12,515, 83%). Full list: `coverage_by_area.csv`.
- **Only 8 of the 120 candidates are uncovered** (4/120 with OSM). They are Bondi, Parramatta, Enmore, Stanmore, The Ponds, Newtown, Camellia and Bellevue Hill. The model's gaps sit in busy centres next to existing toilets. Coverage gaps sit in low-density suburbs. The two signals measure different things.

## Step 2: equity weighting

`priority = gap × (1 + w × disadvantage)`. Deciles are cut over hexes, so each decile is 10% of the study hexes with a SEIFA score.

| w | Kept from the w = 0 list | Deciles 1–3 in top 120 | Deciles 8–10 in top 120 |
|---|---|---|---|
| 0 | 120/120 | 30/120 (25.0%) | 17/120 (14.2%) |
| 0.5 | 107/120 | 41/120 (34.2%) | 8/120 (6.7%) |
| 1 | 102/120 | 45/120 (37.5%) | 5/120 (4.2%) |
| 2 | 93/120 | 54/120 (45.0%) | 2/120 (1.7%) |

At w = 0 the list under-represents disadvantaged areas (25% against the 30% expected from hex counts). w = 1 reverses that and still keeps 102 of the 120 original candidates.

## Step 3: every combination, top 120 each

Every variant takes the 120 highest-priority hexes. That keeps the comparison fair, but a coverage filter must then reach far below gap = 1 to fill 120 places.

- **Near planned site:** the pick is in the same hex or 1-ring as one of the 42 placeable council-planned sites. Chance rate: 249/16,228 study hexes (1.5%).
- **OSM public toilet:** the hex already has an OSM public toilet. Only hexes checked in `experiments/validity/` count, so the denominator varies.
- **Newly covered residents:** residents in currently uncovered hexes (official toilets, k = 1) who would be covered if each pick got a toilet.

| Variant | Kept from no-step list | Picks with gap ≥ 1 | Total gap | Near planned site (chance 1.5%) | OSM public toilet already | Deciles 1–3 | Deciles 8–10 | Newly covered residents |
|---|---|---|---|---|---|---|---|---|
| None | 120/120 | 120/120 | 159 | **10/120 (8.3%)** | 60/120 (50%) | 30/120 (25.0%) | 17/120 (14.2%) | 47,708 |
| Coverage (official) | 8/120 | 8/120 | 79 | 1/120 (0.8%) | 8/95 (8%) | 40/120 (33.3%) | 22/120 (18.3%) | 170,110 |
| Coverage (official + OSM) | 4/120 | 4/120 | 73 | 0/120 (0.0%) | 0/74 (0%)* | 44/120 (36.7%) | 22/120 (18.3%) | 177,506 |
| Equity w = 0.5 | 107/120 | 107/120 | 157 | 11/120 (9.2%) | 57/119 (48%) | 41/120 (34.2%) | 8/120 (6.7%) | 49,879 |
| **Equity w = 1** | 102/120 | 102/120 | 156 | **11/120 (9.2%)** | 57/118 (48%) | 45/120 (37.5%) | 5/120 (4.2%) | 50,066 |
| Equity w = 2 | 93/120 | 93/120 | 152 | 12/120 (10.0%) | 54/117 (46%) | 54/120 (45.0%) | 2/120 (1.7%) | 48,789 |
| Coverage (official) + equity w = 0.5 | 8/120 | 8/120 | 78 | 1/120 (0.8%) | 8/84 (10%) | 52/120 (43.3%) | 11/120 (9.2%) | 173,607 |
| Coverage (official) + equity w = 1 | 8/120 | 8/120 | 77 | 1/120 (0.8%) | 8/79 (10%) | 58/120 (48.3%) | 7/120 (5.8%) | 174,576 |
| Coverage (official) + equity w = 2 | 8/120 | 8/120 | 76 | 1/120 (0.8%) | 8/75 (11%) | 64/120 (53.3%) | 5/120 (4.2%) | 176,023 |
| Coverage (official + OSM) + equity w = 0.5 | 4/120 | 4/120 | 72 | 0/120 (0.0%) | 0/69 (0%)* | 54/120 (45.0%) | 9/120 (7.5%) | 180,847 |
| Coverage (official + OSM) + equity w = 1 | 4/120 | 4/120 | 70 | 0/120 (0.0%) | 0/62 (0%)* | 63/120 (52.5%) | 5/120 (4.2%) | 183,224 |
| Coverage (official + OSM) + equity w = 2 | 4/120 | 4/120 | 69 | 0/120 (0.0%) | 0/62 (0%)* | 71/120 (59.2%) | 3/120 (2.5%) | 181,677 |

\* 0% by construction: OSM toilet hexes count as covered, so they are filtered out.

Full decile counts per variant are in `results.csv` (`decile_counts`). 15–22 picks per variant have no SEIFA score.

### What the table shows

1. **The coverage filter breaks the ranking.** Only 8 candidates are uncovered, so 112 of the 120 picks are hexes the model rates below 1 toilet (median gap 0.59 against 1.24). Planned-site hits fall from 10/120 to 1/120, below the 1.5% chance rate. In exchange, the picks would newly cover 170,110 residents, 3.6× the 47,708 covered by the model's own list. The coverage list answers a different question: where people live far from any toilet, not where the model expects a toilet.
2. **Equity weighting is nearly free.** At w = 1, planned-site hits rise from 10 to 11, the OSM "toilet already there" rate drops from 50% to 48%, and the total gap falls by only 2% (159 to 156). Deciles 1–3 go from 30 to 45 picks, and deciles 8–10 from 17 to 5. w = 2 pushes further (54 against 2) but drops 27 of the 120 candidates.
3. **The OSM check is also a coverage fix.** 60/120 (50%) of the unweighted picks already have an OSM public toilet. Removing hexes with OSM toilets from the candidate list (step 2 of the findings plan) is a separate filter from coverage, and it is worth doing.

## Recommendation for the app

- **Main list:** the model's candidates re-ranked with **equity w = 1**. It keeps the model's planned-site signal (11/120, 9.2%, against 1.5% chance) and moves the list toward disadvantaged areas (deciles 1–3: 37.5%; 8–10: 4.2%). Say in the app that the ranking includes a disadvantage weight.
- **Coverage as its own layer, not a filter:** shade hexes with no listed toilet within about 400 m walk (k = 1). Show the headline "1.47 M residents (32.8%) have no listed public toilet within about 400 m". Mark the 8 candidates that are also uncovered with a badge, because they meet both tests.
- **Optional second tab, "Access gaps":** uncovered hexes ranked by residents newly covered, with equity weighting. Label it as an access view, separate from the model's predictions.
- Do not multiply gap by the uncovered flag in the main list.
