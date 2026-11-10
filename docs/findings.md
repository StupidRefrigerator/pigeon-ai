# Findings

Quick reference for every model result so far. The scripts and raw CSVs for each section are in [`experiments/`](../experiments). Each section names its folder. The longer write-up with maps is the Claude doc [PIGEON-AI: toilet model results](https://claude.ai/artifact/Cip7zbvXLs5kT73gScpaWC).

## The two models

| | Original | Good-areas |
|---|---|---|
| Trained on | All 16,228 study hexes, 5-fold spatial CV | 20 of 90 blocks where real toilets beat the original's prediction most |
| Code | `src/pigeon_ai/model.py`, `scripts/train_model.py` | `src/pigeon_ai/good_areas.py` (PR #8) |
| Candidates (pred − actual ≥ 1) | 120 | 314, including 119 of the original's 120 |

Every number below is held-out. No model saw the hex it was scored on.

**Decision (team, 9 Nov 2026): use the original cross-validated model. The good-areas model is dropped and PR #8 is closed.** Good-areas ranks real toilets slightly worse, predicts 41% too many toilets, and flags 2.6× as many spots. Each of its flags is no more likely to match a council plan than one of the original's flags.

## The three new-area tests

There are 3 different tests. This is the easiest place to get confused.

| Test | Where | Does real data exist? | What it shows |
|---|---|---|---|
| A. Growth suburbs | Oran Park, Marsden Park, etc. | Yes: real features and real toilets | The model works on suburbs it never saw (24/35) |
| B. Bradfield | Airport city, not built yet | No, so the features are **built from government plans** | Where it *would* put toilets in the future |
| C. Oran Park check | Oran Park | Yes | **Whether test B's guessed features can be trusted** |

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

## Data sources for a new suburb

A new suburb needs a value for every feature the model uses. These are the official sources for each one, so they can go straight into the new-suburb prompt or input form.

| Feature | Source | Format | Notes |
|---|---|---|---|
| Population, today | ABS Census 2021 mesh blocks and SA1 | CSV and shapefile | Already in the pipeline |
| Population, future | NSW DPHI 2024 Common Planning Assumptions, SA2 projections to 2041 | XLSX | Spread over land zoned for housing |
| Land use and zoning | NSW Planning Portal, Principal Planning Layers (ArcGIS MapServer, layer 19 Land Zoning) | GeoJSON via REST | Gives centre, residential, park (RE1), mixed use and infrastructure zones |
| Precinct and master plans | DPHI precinct plans (Aerotropolis Precinct Plan, Bradfield City Centre Master Plan, South West Growth Area plans) | PDF | Locations of town centres, parks and "amenities" |
| Train and metro stations | Sydney Metro (Western Sydney Airport line) and Transport for NSW | Station coordinates | Planned stations are in the master plans |
| Bus stops | TfNSW GTFS (today) | GTFS | Future values: calibrated densities per zone |
| Shops and food | OpenStreetMap (today) | Overpass API | Future values: low, mid or high density per zone, calibrated on 20 Sydney suburbs |
| Parks, sports fields, playgrounds, beaches | OpenStreetMap (today) and zoning RE1 (planned) | Overpass and GeoJSON | Being added as v2 features |
| Disadvantage | ABS SEIFA 2021 IRSD | CSV | New suburbs have no score until the next Census |
| Planned toilets | Council toilet strategies, project pages and DA reports | Web and PDF | 56 sites collected in `experiments/gov/planned_sites.csv` |

## v2: new inputs, label fix, 400 m walk and equity (10 Nov 2026)

Folder: `experiments/v2/`. The data is in `data/`, the 400 m and equity steps in `postprocess/`, and every combination in `combos/results.md`. All numbers are held-out, and each model was run with 3 seeds. A gain smaller than the seed spread is noise.

| Change | PR-AUC | Council sites in top 10% | Growth toilet hexes in top 100 | Verdict |
|---|---|---|---|---|
| Base model | 0.520 | 26/42 | 24/35 | |
| **+ sports fields, playgrounds, beaches** | **0.569** (seed spread ±0.001) | **30/42** | 22/35 | **Keep.** It is the only change that beats the noise. |
| Retrain on OSM toilets as labels | 0.506 | 24/42 | 24/35 | Drop. It predicts 29% too many toilets and makes 267 candidates. |
| Count OSM toilets *after* the model | same model | same | same | **Keep.** Picks that already have an OSM toilet fall from 37/120 to 9/120. |
| Equity weight w=1 | same model | same | same | **Keep.** Picks in deciles 1–3 rise from 32 to 54 of 120; picks in deciles 8–10 fall from 17 to 3. |
| 400 m walk as a filter | same model | same | same | Drop as a filter, keep as a map layer. Only 5–20 of its 120 picks are real gaps, and 0–3 are near a council plan. |

- **Chosen setup:** latest + sports, playground and beach features, trained on official labels. OSM toilets are counted after the model, the list is equity-weighted (w=1), and only picks with a gap of at least 1 are listed (87).
- **400 m walk:** 1,471,429 of 4,491,614 residents (32.8%) have no listed toilet within about 400 m.
- **Still missed:** Ken Birdsey Park (31st percentile) and Anthony Skarratt Reserve (20th). OpenStreetMap has no sports ground mapped at either site.
- **Bradfield:** the station hex is still #1 for every variant. The new features lower the area total from 142 to 107 and add two planned parks at #3 and #4.
- **Correction to section 2:** counting strictly inside the hex, **39/120 (32%)** of the original candidates already have an OSM public toilet. The 50% figure also counted toilets up to 50 m outside the hex.

## Next improvements, in order

1. Add sports fields, playgrounds and beaches as features. These cover the biggest misses.
2. Count OSM-listed public toilets as existing, so candidates stop pointing at toilets that already exist.
3. Add 400 m walking coverage. City of Sydney plans to a 400 m target.
4. Add the disadvantage priority step.
