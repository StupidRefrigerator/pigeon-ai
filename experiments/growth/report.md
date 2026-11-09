# Growth-suburb out-of-area test (v1 features, 19 columns)

Both models were trained only on the 16,228 study hexes and applied unchanged to the 1,108 growth hexes
(39 toilets in 35 hexes, 16 of the 20 growth suburbs; Badgerys Creek, Luddenham, Appin and Menangle Park have no hexes in the file).
Baseline = forest on all study hexes. Good areas = forest on the 4,457 study hexes in the 20 good blocks.
Both use `make_forest(0)`, single seed. No cross-validation is needed: no growth hex was ever in training.

## Headline

|                             |   baseline |   good_areas |
|:----------------------------|-----------:|-------------:|
| pred_total                  |     54.606 |       97.276 |
| actual                      |     39     |       39     |
| deviance                    |      0.163 |        0.21  |
| pr_auc                      |      0.312 |        0.311 |
| base_rate                   |      0.032 |        0.032 |
| toilets_top20               |     12     |       11     |
| toilets_top35               |     13     |       16     |
| toilets_top100              |     28     |       27     |
| hexes_with_toilet_in_top100 |     24     |       23     |
| hexes_with_toilet           |     35     |       35     |
| candidates                  |      1     |        1     |
| pred/actual                 |      1.4   |        2.494 |

Reading it:
- Baseline predicts 54.6 toilets for 39 real (1.4x). Good areas predicts 97.3 (2.5x): it over-predicts badly out of area, as expected from a model trained on blocks where toilets are over-supplied relative to the baseline.
- Poisson deviance (lower is better): baseline 0.163, good areas 0.210. Baseline is better calibrated.
- Ranking is a wash. PR-AUC 0.31 for both vs a base rate of 0.032 (about 10x chance). Toilets in the top 100 hexes: 28 vs 27 (24 vs 23 of the 35 toilet hexes); chance would be about 3.
- The good-areas model is slightly better at the very top-35 (16 vs 13 toilets) and slightly worse at top 20 (11 vs 12). With 35 positive hexes these differences are one or two toilets, i.e. noise.
- Candidates (pred - actual >= 1): one each, and it is the same hex (89be085a90fffff, Schofields, 0 toilets, predicted 1.22 baseline / 1.18 good areas). Almost no growth hex is predicted above 1 (baseline: 2 hexes, good areas: 4), because these are new, low-density, low-amenity hexes in the 2021 data.

## Per suburb (approximate assignment)

Hexes are assigned to the nearest *growth-suburb* representative point in `sydney_places.json` (no suburb polygons are available offline: `data/raw` is absent). This is a Voronoi split, so boundaries are rough; 286 hexes would instead be nearest a non-growth neighbour (Horningsea Park, Angus, Bradfield, Rossmore, Harrington Park, West Hoxton, Grantham Farm, Denham Court...). The column `nearest_place_all` in growth_predictions.csv gives that alternative label. Treat per-suburb numbers as indicative.

| suburb          |   hexes |   actual_toilets |   baseline_pred |   good_areas_pred |
|:----------------|--------:|-----------------:|----------------:|------------------:|
| Austral         |     118 |                0 |             2.2 |               4.7 |
| Box Hill (NSW)  |      86 |                1 |             4.7 |               9.7 |
| Bringelly       |      87 |                0 |             0.3 |               1.7 |
| Catherine Field |      72 |                1 |             0.9 |               2.6 |
| Colebee         |      45 |                1 |             5.1 |               7.9 |
| Edmondson Park  |      64 |                5 |             4.7 |               6.8 |
| Gilead          |       3 |                0 |             0.1 |               0.2 |
| Gledswood Hills |      76 |                3 |             5   |               8.8 |
| Gregory Hills   |      23 |                7 |             3   |               4.8 |
| Leppington      |     140 |                6 |             4.8 |               9.6 |
| Marsden Park    |     102 |                0 |             4.7 |               9.5 |
| Oran Park       |      86 |                5 |             8.3 |              13.5 |
| Riverstone      |      48 |                6 |             3.9 |               5.1 |
| Schofields      |      64 |                3 |             4.6 |               7.2 |
| Shanes Park     |      66 |                1 |             1.2 |               2.8 |
| Vineyard        |      28 |                0 |             1   |               2.3 |
| TOTAL           |    1108 |               39 |            54.5 |              97.2 |

Pattern: both models under-predict the already built-up, toilet-rich suburbs (Gregory Hills 7 real vs 3.0/4.8, Riverstone 6 vs 3.9/5.1, Leppington 6 vs 4.8/9.6 for baseline/good) and over-predict the ones still mostly greenfield with 0 toilets (Marsden Park 0 vs 4.7/9.5, Austral 0 vs 2.2/4.7, Vineyard, Bringelly). Marsden Park, Box Hill and Colebee are the main over-prediction pockets; the plausible reading is that they are being built out (see population caveat), so a model fed 2021 inputs expects toilets for their location but 2021 population and amenities are still low.

## The 35 toilet hexes: predictions and rank (of 1,108; 1 = most toilets predicted)

| hex_id          | suburb          |   toilet_count |   baseline_pred |   good_areas_pred |   baseline_rank |   good_areas_rank |
|:----------------|:----------------|---------------:|----------------:|------------------:|----------------:|------------------:|
| 89be0858e17ffff | Box Hill (NSW)  |              1 |            0.4  |              0.57 |              25 |                24 |
| 89be08cccb3ffff | Catherine Field |              1 |            0.53 |              0.63 |              14 |                17 |
| 89be08434abffff | Colebee         |              1 |            0.3  |              0.56 |              42 |                25 |
| 89be08cc613ffff | Edmondson Park  |              1 |            0.97 |              1.06 |               3 |                 4 |
| 89be08cf32bffff | Edmondson Park  |              1 |            0.29 |              0.37 |              48 |                70 |
| 89be08cd5b7ffff | Edmondson Park  |              1 |            0.25 |              0.36 |              62 |                79 |
| 89be08cc68bffff | Edmondson Park  |              1 |            0.12 |              0.12 |             127 |               196 |
| 89be08cc2bbffff | Edmondson Park  |              1 |            0.02 |              0.12 |             354 |               183 |
| 89be08ce827ffff | Gledswood Hills |              1 |            0.55 |              0.74 |              12 |                11 |
| 89be08ce867ffff | Gledswood Hills |              1 |            0.19 |              0.41 |              91 |                56 |
| 89be08ce847ffff | Gledswood Hills |              1 |            0.06 |              0.06 |             188 |               415 |
| 89be08ce817ffff | Gregory Hills   |              3 |            0.47 |              0.59 |              18 |                20 |
| 89be08ce953ffff | Gregory Hills   |              2 |            0.25 |              0.54 |              60 |                32 |
| 89be08ce8afffff | Gregory Hills   |              1 |            0.03 |              0.07 |             302 |               372 |
| 89be08ce807ffff | Gregory Hills   |              1 |            0.01 |              0.02 |             539 |               615 |
| 89be08cc303ffff | Leppington      |              1 |            0.74 |              0.75 |               7 |                10 |
| 89be08cea57ffff | Leppington      |              1 |            0.5  |              0.77 |              16 |                 9 |
| 89be08cc02bffff | Leppington      |              1 |            0.29 |              0.39 |              45 |                63 |
| 89be08cea4bffff | Leppington      |              1 |            0.19 |              0.32 |              90 |                88 |
| 89be08cc1d7ffff | Leppington      |              1 |            0.08 |              0.08 |             154 |               363 |
| 89be08cc067ffff | Leppington      |              1 |            0.02 |              0.1  |             400 |               259 |
| 89be081b64bffff | Oran Park       |              1 |            0.77 |              1.11 |               6 |                 3 |
| 89be081b643ffff | Oran Park       |              1 |            0.68 |              0.82 |               9 |                 8 |
| 89be08ccd97ffff | Oran Park       |              2 |            0.26 |              0.43 |              52 |                51 |
| 89be081b613ffff | Oran Park       |              1 |            0.11 |              0.14 |             129 |               152 |
| 89be084364fffff | Riverstone      |              1 |            1.06 |              1.15 |               2 |                 2 |
| 89be084362bffff | Riverstone      |              1 |            0.51 |              0.56 |              15 |                26 |
| 89be0858db7ffff | Riverstone      |              1 |            0.29 |              0.42 |              49 |                53 |
| 89be084364bffff | Riverstone      |              1 |            0.18 |              0.21 |              95 |               120 |
| 89be0843647ffff | Riverstone      |              1 |            0.04 |              0.13 |             264 |               174 |
| 89be0858d23ffff | Riverstone      |              1 |            0    |              0    |             860 |              1107 |
| 89be085a933ffff | Schofields      |              1 |            0.29 |              0.41 |              46 |                57 |
| 89be085a96fffff | Schofields      |              1 |            0.25 |              0.33 |              66 |                86 |
| 89be085a96bffff | Schofields      |              1 |            0.22 |              0.37 |              75 |                72 |
| 89be0840417ffff | Shanes Park     |              1 |            0    |              0.01 |             717 |               802 |

Rank is the stable sort by predicted count (ties are rare but exist at the near-zero tail). Hexes ranked below 300 under both models (e.g. Riverstone 89be0858d23ffff, Shanes Park 89be0840417ffff, Gregory Hills 89be08ce807ffff) have almost no population/amenities in the 2021 inputs, so the model cannot see why a toilet is there.

## Candidates (pred - actual >= 1) in growth areas

Baseline: 1 hex. Good areas: 1 hex. Same hex.

| model      | hex_id          | suburb     |      lat |     lng |   toilet_count |   pred |
|:-----------|:----------------|:-----------|---------:|--------:|---------------:|-------:|
| baseline   | 89be085a90fffff | Schofields | -33.7044 | 150.875 |              0 | 1.2201 |
| good_areas | 89be085a90fffff | Schofields | -33.7044 | 150.875 |              0 | 1.1804 |

Raising the sensitivity (e.g. pred - actual >= 0.5) would be needed to get a usable candidate list in these suburbs; at the repo's threshold of 1.0 the models flag almost nothing here. Full ranked lists are in growth_predictions.csv.

## Caveats

- Population is the 2021 census, allocated from SA1 polygons. These suburbs have grown a lot since, and amenities mapped in OSM then are a snapshot of the same period; so the inputs understate current demand and the "over-prediction" in the greenfield suburbs may partly be demand that is not yet served rather than a model error. The comparison also cannot tell us whether the 39 toilets (as listed on the National Public Toilet Map, possibly newer than the inputs) were placed in response to growth after 2021.
- Toilet counts: the toilet data and the inputs are not time-aligned. Toilets built after 2021 sit in hexes whose features still look empty.
- Good blocks were selected using the baseline's `latest`-feature out-of-fold predictions (as committed in good_blocks.csv); this test applies them to a v1-feature forest. The block choice is therefore not tuned on the growth hexes, but it is also not the exact v1 selection.
- Single seed and 35 positive hexes: ranking differences of 1 to 3 toilets are not meaningful.
- Suburb assignment is approximate (above).
- Hit counts use toilets (summing toilet_count over the top N hexes), and "hexes with a toilet" separately; the repo's `top_hits` counts hexes with a toilet.

## Stretch: `latest` feature set - NOT DONE

Skipped. The 9 missing columns cannot be recomputed from the repo (`data/raw` and `data/interim` are not present: no NSW OSM extract, no osmium, no SA1 boundaries). I tried live Overpass (a bbox cut into 0.05 then 0.1 degree tiles, cached in osm_cache/). The public server returned 429/502/504 repeatedly: 4 of 19 tiles in about 25 minutes, so full coverage of the growth area was not reachable in the time box, and I stopped. Further problems that would remain even with the data: `population_1000m` needs SA1 population polygons (not OSM) and could only be approximated from the hex-level population; OSM polygon centres from Overpass differ slightly from the repo's representative points; the OSM snapshot differs from the one the committed features used. Scripts fetch_osm.py and compute_features.py are in this folder, unfinished (compute_features.py has never been run, and validation against 200 study hexes was therefore not done). Do not treat the `latest` results as available.

## Files
growth_predictions.csv (hex_id, suburb, nearest_place_all, lat, lng, toilet_count, baseline_pred, good_areas_pred), growth_predictions_full.csv (all features), metrics.csv, per_suburb.csv, toilet_hexes.csv, candidates.csv. Scripts: run_core.py, metrics.py, tables.py, build_report.py.
