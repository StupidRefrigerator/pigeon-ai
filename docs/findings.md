# Findings

Quick reference for every model result so far. The scripts and raw CSVs for each section are in [`experiments/`](../experiments). Each section names its folder. The longer write-up with maps is the Claude doc [PIGEON-AI: toilet model results](https://claude.ai/artifact/Cip7zbvXLs5kT73gScpaWC).

## The two models

| | Original | Good-areas |
|---|---|---|
| Trained on | All 16,228 study hexes, 5-fold spatial CV | 20 of 90 blocks where real toilets beat the original's prediction most |
| Code | `src/pigeon_ai/model.py`, `scripts/train_model.py` | `src/pigeon_ai/good_areas.py` (PR #8) |
| Candidates (pred − actual ≥ 1) | 120 | 314, including 119 of the original's 120 |

Every number below is held-out. No model saw the hex it was scored on.

**Decision: use the original.** Good-areas ranks real toilets slightly worse, predicts 41% too many toilets, and flags 2.6× as many spots. Each of its flags is no more likely to match a council plan than one of the original's flags.

## 1. Does it find where toilets already are?

Study area: 16,228 hexes with 2,570 toilets. Folder: `experiments/validity/`.

| Measure | Original | Good-areas | What it means |
|---|---|---|---|
| PR-AUC | **0.519** | 0.491 | Ranking quality. Random would score 0.12. |
| Real toilet hexes in top 100 | **86/100** | 83/100 | |
| Real toilet hexes in top 500 | **359/500** | 326/500 | |
| Real toilet hexes in top 1,000 | **616/1,000** | 582/1,000 | |
| Poisson deviance (lower is better) | **0.419** | 0.449 | Error in the counts |
| Predicted total (real: 2,570) | **2,632** | 3,624 | Good-areas overshoots by 41% |

## 2. Are the suggested spots valid?

Each candidate hex was checked against OpenStreetMap (Overpass API) and NSW zoning. Folder: `experiments/validity/`.

| Candidate hex contains | Original (120) | Good-areas (314) |
|---|---|---|
| A public toilet on OpenStreetMap | 60 (50%) | 131 (42%) |
| More OSM public toilets than the official map lists | 55 (46%) | 116 (37%) |
| A shopping centre or strong destination (station, beach, large park, library, mall) | 107 (89%) | 267 (85%) |
| Only houses or industry | 0 (0%) | 2 (1%) |

- **"Missing from the official map".** Our labels come from the National Public Toilet Map, which depends on councils and owners submitting their toilets. Toilets in shopping centres, stations and clubs are often absent from it. OpenStreetMap is volunteer-mapped and often lists them. About half of these OSM toilets have no access tag, so some may be customer-only.
- **Limit of this check.** 82% of busy hexes the model did not flag also contain a shopping centre or strong destination. The check shows that candidates are plausible places. It cannot prove that they need a toilet.

## 3. New suburbs the model never trained on

Growth suburbs: 16 suburbs, 1,108 hexes and 39 real toilets in 35 hexes. Both models use `v1` features. Folder: `experiments/growth/`.

| | Original | Good-areas |
|---|---|---|
| Toilets predicted (real: 39) | **55** | 97 |
| Real toilet hexes in top 100 | **24/35 (69%)** | 23/35 (66%) |
| PR-AUC (random: 0.032) | 0.312 | 0.311 |

A random top 100 would catch about 3 of the 35. Over-predicting is expected because these suburbs are still filling in.

## 4. Bradfield / Aerotropolis (no data exists yet)

Folder: `experiments/future/`. The model takes the `v1` features, so each one was built from official plans:

| Feature | Source used for the future |
|---|---|
| Population (in hex, 250 m, 500 m) | DPHI 2024 SA2 projections for 2041, spread over residential and mixed-use zoned land |
| Train stations | Sydney Metro Western Sydney Airport station locations (Bradfield, Luddenham, Airport Terminal, Airport Business Park) |
| Parks | NSW zoning layer: ENZ and RE zones |
| Shops, food, bus stops | Low, mid and high densities per zone type, measured in 20 existing Sydney suburbs |

- **Today**, with real features (farmland): 9.7 toilets predicted across the area.
- **Mid scenario, 2041:** about 139 (original). Read the ranking, not the total.
- **#1 hex in both models:** Bradfield Station (27 m away, Mixed Use zone, beside the planned Central Park). The Bradfield master plan (p64) marks "Amenities" there.
- **Proxy check on Oran Park,** where real features exist:

  | | Real features | Proxy features (from zoning) |
  |---|---|---|
  | Overlap with the real-feature top 10 | 10/10 | 5/10 |
  | Real toilet hexes in top 10 | 3/5 | 2/5 |

  The proxy keeps about half the ranking.

## 5. Planned council toilets

Folder: `experiments/gov/`, with every site, its source URL and its scores in `planned_sites.csv`.

- **Sources:** 56 sites from 22 councils' toilet strategies, project pages, DA reports and media releases. Examples are the City of Sydney automatic public toilet program and the Inner West Public Toilet Strategy 2022.
- **Scored:** 42 sites could be placed on a hex. The other 14 were suburb-only or outside the study area.

**Original model:**

| | Planned sites | Random empty hexes | Random empty park hexes |
|---|---|---|---|
| In model's top 10% | **26/42 (62%)** | 109/1,000 (11%) | 195/1,000 (20%) |
| In model's top 25% | **36/42 (86%)** | 248/1,000 (25%) | 472/1,000 (47%) |
| Candidate within ~250 m | 8/39 (21%) | 23/1,000 (2%) | 47/1,000 (5%) |
| Median percentile | 95th | 49th | 73rd |

- **Fairest subset:** 15 brand-new sites in hexes with no toilet yet. 10/15 (67%) of them are in the top 25%, against 47% for parks.
- **Reverse check:** 10/120 original candidates (8.3%) and 26/314 good-areas candidates (8.3%) are near a planned site, against 1.5% by chance. Per flag, the two models are equal.
- **Misses:** sports-field amenity blocks. Ken Birdsey Park was at the 29th percentile and Anthony Skarratt Reserve at the 41st. The model has no sports-field feature.

## 6. Socioeconomic shape (SEIFA deciles)

| | Decile 1 (most disadvantaged) | Decile 10 (least disadvantaged) |
|---|---|---|
| Toilets per 10k residents | 4.1 | 5.7 |
| Real ÷ predicted | Between 0.88 and 1.09 across all deciles | |

The model reproduces Sydney's current pattern, so wealthier areas get more. Changing that needs a priority step after the model: `priority = gap × (1 + weight × disadvantage)`.

## Next improvements, in order

1. Add sports fields, playgrounds and beaches as features. These cover the biggest misses.
2. Count OSM-listed public toilets as existing, so candidates stop pointing at toilets that already exist.
3. Add 400 m walking coverage. City of Sydney plans to a 400 m target.
4. Add the disadvantage priority step.
