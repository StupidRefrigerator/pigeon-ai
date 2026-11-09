# Candidate validity check: baseline vs good-areas model

Date 2026-11-09. Automated proxy review. **No human review exists yet. This is not a substitute for one.**

Rerun with `/tmp/pigeon-env/bin/python` on, in order: `q1_metrics.py`, `fetch_osm.py`, `fetch_zoning.py`, `fetch_zoning_point.py`, `classify.py`, `build_report.py`. The fetchers cache to `cache/`, so a rerun is offline.

## Question 1. Does each model predict where toilets already are?

Both columns use held-out predictions for all 16,228 hexes.

| Metric | Baseline | Good areas | Note |
|---|---|---|---|
| Poisson deviance (lower is better) | 0.419 | 0.449 | Guessing the mean scores 0.719 |
| PR-AUC (toilet hex vs prediction) | 0.519 | 0.491 | Random order scores 0.118 |
| Top-100 hits | 86 | 83 | |
| Top-500 hits | 359 | 326 | |
| Top-1,000 hits | 616 | 582 | |
| Recall of toilet hexes in top 1,000 | 32.2% | 30.5% | Of 1,911 toilet hexes |
| Share of toilets in top 1,000 | 40.4% | 38.6% | Of 2,570 toilets |
| Predicted total | 2,632 | 3,624 | Actual 2,570 |
| PR-AUC outside the 20 good blocks | 0.488 | 0.466 | 11,771 hexes. Neither model trained near them. |
| PR-AUC inside the good blocks | 0.597 | 0.553 | 4,457 hexes |

The good-areas model is built to predict above today's counts. It predicts 41% more toilets than exist. Deviance and calibration penalise it for that by design. Ranking metrics are the fair test of whether it knows where toilets go. **On every ranking metric the baseline is ahead, by a small margin.** That includes the hexes outside the good blocks, where the comparison is cleanest. So training on good areas does not teach the model anything new about where toilets sit. It mostly scales predictions up.

Calibration bands (mean predicted vs mean actual):

| Prediction band | Baseline n | Baseline pred | Baseline actual | Good-areas n | GA pred | GA actual |
|---|---|---|---|---|---|---|
| 0 to 0.05 | 8,462 | 0.015 | 0.017 | 6,728 | 0.016 | 0.014 |
| 0.05 to 0.1 | 2,117 | 0.071 | 0.060 | 2,453 | 0.073 | 0.041 |
| 0.1 to 0.25 | 2,182 | 0.167 | 0.143 | 2,601 | 0.159 | 0.092 |
| 0.25 to 0.5 | 2,037 | 0.357 | 0.353 | 2,274 | 0.363 | 0.258 |
| 0.5 to 1.0 | 1,037 | 0.672 | 0.676 | 1,473 | 0.689 | 0.517 |
| 1.0 to 1.5 | 260 | 1.203 | 1.235 | 413 | 1.183 | 0.927 |
| 1.5 to 2.0 | 92 | 1.720 | 1.717 | 125 | 1.720 | 1.112 |
| 2.0 and up | 41 | 2.227 | 2.049 | 161 | 2.377 | 1.665 |

Mean prediction by actual toilet count:

| Actual | Hexes | Baseline | Good areas |
|---|---|---|---|
| 0 | 14,317 | 0.11 | 0.16 |
| 1 | 1,487 | 0.46 | 0.60 |
| 2 | 289 | 0.79 | 1.01 |
| 3 | 87 | 0.96 | 1.23 |
| 4 | 25 | 0.98 | 1.31 |
| 5 | 11 | 0.94 | 1.43 |
| 6+ | 12 | 1.47 | 1.78 |

Both models compress the top end. Hexes with 3 to 5 toilets get about 1 from the baseline. The good-areas model lifts every row by about 30%, as a near-constant multiplier.

## Question 2. Are the candidates valid places?

### Method

Every hex in the union of both candidate lists (315 hexes) was checked against live OpenStreetMap (Overpass, fetched 2026-11-09, 21 cached bbox queries) and NSW LEP Land Zoning (layer 19 of the Planning Portal service). Hexes are res-9 polygons in EPSG:32756.

Categories, first match wins:

1. `toilet_already_mapped_public`. An OSM `amenity=toilets` lies within 50 m of the hex with access `yes`, `public`, `permissive`, `destination` or no access tag.
2. `toilet_customers_or_private`. Same, with access `customers`, `private`, `no` and similar.
3. `shopping_centre`. `shop=mall` intersects the hex, or a `landuse=retail` polygon of 2 ha or more, or a `building=retail` of 5,000 m² or more. A department store alone does not count.
4. `public_destination`. Inside the hex: a park or garden with 1,500 m² or more inside, a playground, non-private pitch, sports centre, stadium, beach, library, community centre, town hall, marketplace, bus or ferry station, tourism attraction, 50 m or more of pedestrian street, a rail or light-rail station within 50 m, or 30% or more zoned RE1/RE2. Tier `strong` means station, beach, library, community centre, town hall, marketplace, bus or ferry station, stadium, sports centre, pedestrian street, or 1 ha or more of park. Tier `weak` means only a playground, pitch, small park or tourism point.
5. `commercial_street`. 8 or more shop or food nodes in the hex, or 25% or more commercial or retail landuse, or a main zone of E1, E2, MU1 or a B zone.
6. `residential_or_industrial_only`. 25% or more residential or industrial landuse, or a main zone of R, IN, E3, E4 or E5.
7. `unknown`. None of the above.

`toilet_not_on_map` means OSM has more public toilets in the hex than the National Public Toilet Map does. For empty candidates that equals category 1. For shortfall hexes the single map toilet is usually the same OSM toilet, so only the excess counts.

The "site-only" classifier ignores OSM toilets, rules 1 and 2. It asks only whether the place itself looks like a toilet site.

Zoning came from the hex polygon for 713 hexes, including every candidate and every real-toilet hex. The server then degraded to 502 errors and 9 to 12 s replies, so the other 485 control hexes use the zone at the hex centre. One hex has no zone.

### Calibration check: does the proxy mean anything?

Three random samples (seed 0), classified the same way:

| Signal | Real toilet hexes (300) | Empty, low prediction < 0.1 in both models (300) | Empty, baseline 0.5 to 1.0, not a candidate (300) |
|---|---|---|---|
| OSM public toilet in hex | 56% | 1% | 26% |
| OSM has more public toilets than the map | 15% | 1% | 26% |
| Site-only: shopping centre | 23% | 1% | 15% |
| Site-only: strong destination | 65% | 3% | 73% |
| Site-only: shopping or strong destination | 70% | 4% | 82% |
| Site-only: weak destination only | 21% | 25% | 14% |
| Site-only: residential, industrial or unknown | 7% | 71% | 3% |
| Full classifier: toilet mapped, shopping or public destination | 93% (280) | 29% (87) | 96% (288) |

Full-classifier breakdown for the two requested samples. Real toilet hexes: 56% toilet_already_mapped_public, 1% customers or private, 8% shopping_centre, 28% public_destination, 0% commercial_street, 5% residential_or_industrial_only, 1% unknown. Empty low-prediction hexes: 1%, 0%, 1%, 27%, 0%, 37%, 34%.

What this shows:

- **The proxy separates toilet places from quiet places well.** 70% of real toilet hexes are a shopping centre or strong destination, against 4% of empty low-prediction hexes. It is meaningful at that level.
- **Weak destinations do not discriminate.** A playground, pitch or small park appears in about a quarter of every group. Treat `weak` as no evidence.
- **The proxy cannot tell a good candidate from any busy hex.** Empty hexes the baseline scores 0.5 to 1.0, which are not candidates, look as valid as candidates do (82% shopping or strong). So "valid-looking site" tests that a model ranks busy places highly. It does not test the threshold or the ranking among busy places.
- **OSM only finds 56% of map toilets in the same hex.** OSM toilet coverage is far from complete. A missing OSM toilet is weak evidence of a real gap.
- **OSM over-counts too.** In 15% of real toilet hexes OSM has more public toilets than the map. Separate male and female nodes or a second block cause this. That 15% is the noise floor for a shortfall "extra toilet".

### Candidate breakdown

Full classifier (counts and shares):

| Category | Baseline (120) | Good areas (314) | Both models (119) | Good-areas only (195) | Baseline shortfall (14) | Good-areas shortfall (52) |
|---|---|---|---|---|---|---|
| toilet_already_mapped_public | 60 (50%) | 131 (42%) | 59 (50%) | 72 (37%) | 13 (93%) | 44 (85%) |
| toilet_customers_or_private | 2 (2%) | 7 (2%) | 2 (2%) | 5 (3%) | 0 | 0 |
| shopping_centre | 18 (15%) | 51 (16%) | 18 (15%) | 33 (17%) | 1 (7%) | 3 (6%) |
| public_destination | 38 (32%) | 114 (36%) | 38 (32%) | 76 (39%) | 0 | 5 (10%) |
| commercial_street | 2 (2%) | 9 (3%) | 2 (2%) | 7 (4%) | 0 | 0 |
| residential_or_industrial_only | 0 | 2 (1%) | 0 | 2 (1%) | 0 | 0 |
| unknown | 0 | 0 | 0 | 0 | 0 | 0 |

The one baseline-only candidate is a toilet_already_mapped_public hex.

Key signals:

| Signal | Baseline (120) | Good areas (314) | Good-areas only (195) | Baseline shortfall (14) | GA top 50 | Baseline top 50 |
|---|---|---|---|---|---|---|
| OSM has more public toilets than the map (toilet_not_on_map) | 46% | 37% | 32% | 57% | 50% | 56% |
| ...where every such toilet lacks an access tag | 23% | 20% | 19% | 29% | 24% | 30% |
| Site-only: shopping or strong destination | 89% | 85% | 83% | 100% | 86% | 90% |
| Site-only: weak destination only | 9% | 10% | 11% | 0% | 8% | 10% |
| Site-only: residential, industrial or unknown | 0% | 1% | 1% | 0% | 0% | 0% |
| Median shops and food places in hex | 22 | 14 | 11 | 60 | 36 | 36 |

Empty (`no_toilet`) candidates only, toilet_not_on_map rate: baseline 44% (of 106), good areas 33% (of 262), good-areas only 26% (of 157). Empty non-candidates scored 0.5 to 1.0 by the baseline give the same 26%.

How to read this:

- **Both lists are almost all plausible sites.** 85% to 89% are a shopping centre or a strong public destination. Only 2 of 315 look residential or industrial only. Both are good-areas-only hexes near Rockdale and Canterbury stations.
- **Many candidates are probably map gaps, not missing toilets.** About half of baseline candidates and about two in five good-areas candidates already have an OSM public toilet that the National Public Toilet Map lacks. Of the 88 empty candidates with one, 34% are shopping centres and 35% have a station. This matches the README's expectation for Liverpool and Bondi Junction.
- **The good-areas-only candidates are weaker on the one signal that discriminates.** They have a toilet_not_on_map rate of 26%, the same as busy empty hexes that no model flagged. They are less busy (median 11 shops and food places against 22) and lean more on public_destination (39%). They are plausible places, but the proxy gives no sign that they are better candidates than the next 300 busy hexes.
- **The 14 baseline shortfalls are all big centres.** Penrith, Royal Randwick, Central, Kings Cross, Cronulla, Milsons Point, Hurstville and others. In 8 of 14 (57%) OSM has more public toilets than the map's one. The noise floor is 15%, so this is a real signal that the map under-counts there. The other 6 may be real shortfalls or a single large facility.

## Caveats

- This is a proxy. OSM tags say what a place is, not whether a toilet is needed or could be built there.
- OSM completeness varies. OSM found only 56% of map toilets in the same hex. Missing access tags are common. Here "no tag" counts as public, and 20% to 30% of the toilet_not_on_map hits rely on that. Mall toilets often have no tag and are customer-only in practice.
- The timing differs. OSM is live on 2026-11-09. The toilet map snapshot is from 2026-10-18. Toilets added to OSM in between count as "not on map".
- The rules depend on thresholds: the 50 m toilet snap, 1,500 m² parks, 8 shops. The 150 m buffer is evidence only and is not used to choose a category.
- Zoning: 485 control hexes use the zone at the hex centre, not area shares. This affects only the split between residential and unknown in the low-prediction group.
- Place names are the nearest OSM `place` node plus the name of the mall, destination or station found. Treat them as approximate.
- The good-areas model was evaluated out-of-fold inside the good blocks. But the blocks were chosen using actual counts, so the inside-block PR-AUC is not fully clean. Use the outside-block row.

## Files

- `metrics_existing.csv`, `q1_calibration_bands.csv`, `q1_mean_pred_by_actual.csv`. Question 1.
- `candidates_classified.csv`. All 315 union candidates with both predictions, ranks, membership, OSM and zoning flags, category, site-only category, destination tier, toilet_not_on_map, place name and evidence.
- `calibration_check.csv`, `calibration_signals.csv`, `candidate_signals.csv`. Calibration and group rates.
- `hex_osm_classified.csv`. Every classified hex (1,199).
- `tables.md`. Every generated table, in full.

## Top 20 candidates per model

Rank is by gap, predicted minus actual. Each row has lat/lng, nearest OSM suburb, the name found, category and evidence.

### Baseline top 20

|   rank |      lat |     lng | suburb                       | place_name                                        |   toilet_count |   pred |   gap | category                     | destination_tier   | evidence                                                                                                                                                                                                                                                                                      |
|-------:|---------:|--------:|:-----------------------------|:--------------------------------------------------|---------------:|-------:|------:|:-----------------------------|:-------------------|:----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
|      1 | -33.9208 | 150.926 | Liverpool                    | Liverpool Plaza, Westfield Liverpool              |              0 |   2.24 |  2.24 | toilet_already_mapped_public | nan                | OSM toilet in hex (missing:1); shopping: Liverpool Plaza, Westfield Liverpool; destinations: park;pedestrian_street;playground (Bigge Park); within 150m: community_centre;mall;park;playground; 82 shops/food; landuse retail 10%; zone MU1 85%                                              |
|      2 | -33.968  | 151.107 | Allawah                      | Westfield Hurstville                              |              0 |   2.22 |  2.22 | toilet_already_mapped_public | nan                | OSM toilet in hex (missing:1); shopping: Westfield Hurstville; within 150m: mall;park;playground; 58 shops/food; landuse residential 33%; zone MU1 53%                                                                                                                                        |
|      3 | -33.894  | 151.249 | Bondi Junction               | Eastgate Bondi Junction, Westfield Bondi Junction |              0 |   2.13 |  2.13 | shopping_centre              | nan                | shopping: Eastgate Bondi Junction, Westfield Bondi Junction; destinations: playground; within 150m: community_centre;park;station; 69 shops/food; landuse retail 55%; zone MU1 46%                                                                                                            |
|      4 | -33.871  | 151.224 | Potts Point                  | Art+                                              |              0 |   2.12 |  2.12 | toilet_already_mapped_public | nan                | OSM toilet in hex (missing:1); destinations: pedestrian_street;tourism (Art+, The Cross Art Projects, Sisters of Charity Heritage Centre and Archives); within 150m: community_centre;library;park;playground;tourism; 89 shops/food; zone R1 53%                                             |
|      5 | -33.813  | 151.002 | Parramatta                   | Mayfair Plaza                                     |              0 |   2.03 |  2.03 | toilet_already_mapped_public | nan                | OSM toilet in hex (missing:2;private:1;yes:1); shopping: Mayfair Plaza; destinations: library;park;pedestrian_street;sports_centre;station;tourism (Church Street, Parramatta RSL Club, Murray Garden); within 150m: park;playground;tourism; 48 shops/food; landuse retail 18%; zone MU1 85% |
|      6 | -33.8702 | 151.194 | Pyrmont                      | Bank Street                                       |              0 |   2.02 |  2.02 | toilet_already_mapped_public | nan                | OSM toilet in hex (missing:1); destinations: bus_station;park;pedestrian_street;pitch;playground;station;tourism (Bank Street, Mount St (501), Paradise Reserve); within 150m: library;park;station; 49 shops/food; landuse retail 16%; zone MU1 31%                                          |
|      7 | -33.9224 | 151.227 | Kingsford                    | Kingsford                                         |              0 |   1.96 |  1.96 | toilet_already_mapped_public | nan                | OSM toilet in hex (missing:1); destinations: pedestrian_street;station (Kingsford); within 150m: community_centre;park;station; 58 shops/food; landuse residential 16%; zone R3 58%                                                                                                           |
|      8 | -33.8877 | 151.199 | Chippendale                  | Duya Billiards                                    |              0 |   1.94 |  1.94 | public_destination           | strong             | destinations: playground;sports_centre;tourism (Duya Billiards, Harrington Street Gallery, Nanda Hobbs); within 150m: community_centre;library;park;playground;tourism; 58 shops/food; landuse residential 12%; zone MU1 78%                                                                  |
|      9 | -33.9249 | 151.23  | Kingsford                    | Juniors Kingsford                                 |              0 |   1.89 |  1.89 | toilet_customers_or_private  | nan                | OSM toilet in hex (private:1); destinations: bus_station;park;pedestrian_street;station (Juniors Kingsford, Dacey Gardens); within 150m: park; 16 shops/food; landuse residential 37%; zone SP2 100%                                                                                          |
|     10 | -33.84   | 151.21  | Victoria Cross               | Greenwood Plaza                                   |              0 |   1.84 |  1.84 | toilet_already_mapped_public | nan                | OSM toilet in hex (missing:1;yes:1); shopping: Greenwood Plaza; destinations: pedestrian_street;station (North Sydney); within 150m: mall;park;station;tourism; 61 shops/food; landuse commercial 39%; zone SP2 98%                                                                           |
|     11 | -33.8783 | 151.217 | Darlinghurst                 | Qtopia                                            |              0 |   1.83 |  1.83 | toilet_already_mapped_public | nan                | OSM toilet in hex (missing:2;private:1;yes:1); destinations: community_centre;pedestrian_street;playground;tourism (Qtopia, NAS Gallery, Gallery 9); within 150m: community_centre;library;park;tourism; 30 shops/food; zone R1 69%                                                           |
|     12 | -33.7687 | 151.268 | North Manly                  | Westfield Warringah Mall                          |              0 |   1.81 |  1.81 | toilet_already_mapped_public | nan                | OSM toilet in hex (missing:3); shopping: Westfield Warringah Mall; destinations: library;playground (Warringah Mall Library); within 150m: park;playground; 63 shops/food; landuse retail 41%; zone E2 42%                                                                                    |
|     13 | -33.8808 | 151.22  | Darlinghurst                 | NAS Library                                       |              0 |   1.65 |  1.65 | toilet_already_mapped_public | nan                | OSM toilet in hex (missing:1); destinations: library;park;pedestrian_street;playground (NAS Library, Green Park); within 150m: community_centre;park;playground;tourism; 15 shops/food; zone SP2 45%                                                                                          |
|     14 | -33.9005 | 151.213 | Waterloo                     | The Rope Walk                                     |              0 |   1.64 |  1.64 | toilet_already_mapped_public | nan                | OSM toilet in hex (yes:1); destinations: park;pedestrian_street (The Rope Walk, Dyuralya Square); within 150m: mall;park;playground;tourism; 45 shops/food; landuse residential 61%; zone MU1 88%                                                                                             |
|     15 | -33.8575 | 151.18  | Balmain                      |                                                   |              0 |   1.62 |  1.62 | public_destination           | strong             | destinations: pedestrian_street; within 150m: library;park;playground; 41 shops/food; landuse residential 100%; zone R1 100%                                                                                                                                                                  |
|     16 | -33.8856 | 151.211 | Surry Hills                  | Surry Hills                                       |              0 |   1.62 |  1.62 | toilet_already_mapped_public | nan                | OSM toilet in hex (permissive:1); destinations: station (Surry Hills); within 150m: community_centre;library;park;playground;station;tourism; 46 shops/food; zone MU1 100%                                                                                                                    |
|     17 | -33.7206 | 150.921 | Myrtle Glen Stanhope Gardens | Stanhope Village                                  |              0 |   1.59 |  1.59 | shopping_centre              | nan                | shopping: Stanhope Village; destinations: library;pedestrian_street;playground;sports_centre;zoned_public_recreation (Blacktown Leisure Centre Stanhope, Dennis Johnson Library); within 150m: park;playground; 38 shops/food; landuse residential 33%; zone R2 49%                           |
|     18 | -33.7676 | 150.775 | St Marys                     | Bennett Park                                      |              0 |   1.58 |  1.58 | toilet_already_mapped_public | nan                | OSM toilet in hex (missing:1); shopping: large retail polygon; destinations: library;park (Bennett Park, St Marys Library, Lang Park); within 150m: mall;park;playground; 44 shops/food; landuse retail 64%; zone MU1 60%                                                                     |
|     19 | -34.0649 | 150.816 | Campbelltown                 | Campbelltown                                      |              0 |   1.56 |  1.56 | toilet_already_mapped_public | nan                | OSM toilet in hex (missing:4); destinations: library;park;pedestrian_street;pitch;playground;station (Campbelltown, H. J. Daley Library, Mawson Park); within 150m: community_centre;station; 13 shops/food; zone E2 50%                                                                      |
|     20 | -33.923  | 151.189 | Mascot                       | Mascot                                            |              0 |   1.55 |  1.55 | toilet_already_mapped_public | nan                | OSM toilet in hex (missing:1); destinations: pedestrian_street;station (Mascot); within 150m: park;playground; 23 shops/food; landuse residential 22%; zone SP2 100%                                                                                                                          |

### Good-areas top 20

|   rank |      lat |     lng | suburb            | place_name                                        |   toilet_count |   pred |   gap | category                     | destination_tier   | evidence                                                                                                                                                                                                                                                                                      |
|-------:|---------:|--------:|:------------------|:--------------------------------------------------|---------------:|-------:|------:|:-----------------------------|:-------------------|:----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
|      1 | -33.813  | 151.002 | Parramatta        | Mayfair Plaza                                     |              0 |   2.65 |  2.65 | toilet_already_mapped_public | nan                | OSM toilet in hex (missing:2;private:1;yes:1); shopping: Mayfair Plaza; destinations: library;park;pedestrian_street;sports_centre;station;tourism (Church Street, Parramatta RSL Club, Murray Garden); within 150m: park;playground;tourism; 48 shops/food; landuse retail 18%; zone MU1 85% |
|      2 | -33.9208 | 150.926 | Liverpool         | Liverpool Plaza, Westfield Liverpool              |              0 |   2.64 |  2.64 | toilet_already_mapped_public | nan                | OSM toilet in hex (missing:1); shopping: Liverpool Plaza, Westfield Liverpool; destinations: park;pedestrian_street;playground (Bigge Park); within 150m: community_centre;mall;park;playground; 82 shops/food; landuse retail 10%; zone MU1 85%                                              |
|      3 | -33.871  | 151.224 | Potts Point       | Art+                                              |              0 |   2.59 |  2.59 | toilet_already_mapped_public | nan                | OSM toilet in hex (missing:1); destinations: pedestrian_street;tourism (Art+, The Cross Art Projects, Sisters of Charity Heritage Centre and Archives); within 150m: community_centre;library;park;playground;tourism; 89 shops/food; zone R1 53%                                             |
|      4 | -33.8877 | 151.199 | Chippendale       | Duya Billiards                                    |              0 |   2.56 |  2.56 | public_destination           | strong             | destinations: playground;sports_centre;tourism (Duya Billiards, Harrington Street Gallery, Nanda Hobbs); within 150m: community_centre;library;park;playground;tourism; 58 shops/food; landuse residential 12%; zone MU1 78%                                                                  |
|      5 | -33.8979 | 151.176 | Newtown           | Garavel Playground                                |              0 |   2.55 |  2.55 | public_destination           | weak               | destinations: playground (Garavel Playground); within 150m: community_centre;mall;park;playground;station; 62 shops/food; landuse residential 41%; zone R2 46%                                                                                                                                |
|      6 | -33.8856 | 151.211 | Surry Hills       | Surry Hills                                       |              0 |   2.54 |  2.54 | toilet_already_mapped_public | nan                | OSM toilet in hex (permissive:1); destinations: station (Surry Hills); within 150m: community_centre;library;park;playground;station;tourism; 46 shops/food; zone MU1 100%                                                                                                                    |
|      7 | -33.968  | 151.107 | Allawah           | Westfield Hurstville                              |              0 |   2.53 |  2.53 | toilet_already_mapped_public | nan                | OSM toilet in hex (missing:1); shopping: Westfield Hurstville; within 150m: mall;park;playground; 58 shops/food; landuse residential 33%; zone MU1 53%                                                                                                                                        |
|      8 | -33.894  | 151.249 | Bondi Junction    | Eastgate Bondi Junction, Westfield Bondi Junction |              0 |   2.52 |  2.52 | shopping_centre              | nan                | shopping: Eastgate Bondi Junction, Westfield Bondi Junction; destinations: playground; within 150m: community_centre;park;station; 69 shops/food; landuse retail 55%; zone MU1 46%                                                                                                            |
|      9 | -33.8162 | 151     | Parramatta        | Westfield Parramatta                              |              0 |   2.47 |  2.47 | toilet_already_mapped_public | nan                | OSM toilet in hex (missing:1); shopping: Westfield Parramatta; within 150m: community_centre;mall;park; 72 shops/food; landuse retail 36%; zone MU1 78%                                                                                                                                       |
|     10 | -33.8702 | 151.194 | Pyrmont           | Bank Street                                       |              0 |   2.46 |  2.46 | toilet_already_mapped_public | nan                | OSM toilet in hex (missing:1); destinations: bus_station;park;pedestrian_street;pitch;playground;station;tourism (Bank Street, Mount St (501), Paradise Reserve); within 150m: library;park;station; 49 shops/food; landuse retail 16%; zone MU1 31%                                          |
|     11 | -33.7676 | 150.775 | St Marys          | Bennett Park                                      |              0 |   2.45 |  2.45 | toilet_already_mapped_public | nan                | OSM toilet in hex (missing:1); shopping: large retail polygon; destinations: library;park (Bennett Park, St Marys Library, Lang Park); within 150m: mall;park;playground; 44 shops/food; landuse retail 64%; zone MU1 60%                                                                     |
|     12 | -33.9224 | 151.227 | Kingsford         | Kingsford                                         |              0 |   2.4  |  2.4  | toilet_already_mapped_public | nan                | OSM toilet in hex (missing:1); destinations: pedestrian_street;station (Kingsford); within 150m: community_centre;park;station; 58 shops/food; landuse residential 16%; zone R3 58%                                                                                                           |
|     13 | -33.8206 | 151.01  | Little India      | Persian Library                                   |              0 |   2.39 |  2.39 | public_destination           | strong             | destinations: library (Persian Library); within 150m: park;playground;tourism; 47 shops/food; landuse residential 61%; zone R2 67%                                                                                                                                                            |
|     14 | -33.8878 | 151.233 | Centennial Square | EJ Ward Paddington Community Centre               |              0 |   2.33 |  2.33 | public_destination           | strong             | destinations: community_centre;pedestrian_street;pitch (EJ Ward Paddington Community Centre); within 150m: community_centre;park;playground;tourism; 35 shops/food; landuse residential 61%; zone R2 69%                                                                                      |
|     15 | -33.84   | 151.21  | Victoria Cross    | Greenwood Plaza                                   |              0 |   2.33 |  2.33 | toilet_already_mapped_public | nan                | OSM toilet in hex (missing:1;yes:1); shopping: Greenwood Plaza; destinations: pedestrian_street;station (North Sydney); within 150m: mall;park;station;tourism; 61 shops/food; landuse commercial 39%; zone SP2 98%                                                                           |
|     16 | -33.9005 | 151.213 | Waterloo          | The Rope Walk                                     |              0 |   2.32 |  2.32 | toilet_already_mapped_public | nan                | OSM toilet in hex (yes:1); destinations: park;pedestrian_street (The Rope Walk, Dyuralya Square); within 150m: mall;park;playground;tourism; 45 shops/food; landuse residential 61%; zone MU1 88%                                                                                             |
|     17 | -33.9131 | 151.159 | Marrickville      |                                                   |              0 |   2.29 |  2.29 | shopping_centre              | nan                | shopping: large retail polygon; within 150m: park;playground; 37 shops/food; landuse residential 72%; zone R2 72%                                                                                                                                                                             |
|     18 | -33.8214 | 151.194 | St Leonards       | St Leonards                                       |              0 |   2.26 |  2.26 | toilet_already_mapped_public | nan                | OSM toilet in hex (customers:1;missing:1); destinations: sports_centre;station (St Leonards); within 150m: library;mall;park;playground; 29 shops/food; landuse residential 24%; zone E2 36%                                                                                                  |
|     19 | -33.7687 | 151.268 | North Manly       | Westfield Warringah Mall                          |              0 |   2.25 |  2.25 | toilet_already_mapped_public | nan                | OSM toilet in hex (missing:3); shopping: Westfield Warringah Mall; destinations: library;playground (Warringah Mall Library); within 150m: park;playground; 63 shops/food; landuse retail 41%; zone E2 42%                                                                                    |
|     20 | -33.607  | 150.823 | Windsor           |                                                   |              0 |   2.21 |  2.21 | shopping_centre              | nan                | shopping: large retail polygon; destinations: pedestrian_street; within 150m: mall;park;tourism; 35 shops/food; landuse retail 31%; zone SP2 71%                                                                                                                                              |

### Baseline shortfall

|     lat |     lng | suburb        | place_name                     |   toilet_count |   baseline_pred | category                     | evidence                                                                                                                                                                                                                                                                                                                              |
|--------:|--------:|:--------------|:-------------------------------|---------------:|----------------:|:-----------------------------|:--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| -33.751 | 150.695 | Penrith       | Westfield Penrith              |              1 |           2.345 | toilet_already_mapped_public | OSM toilet in hex (missing:3); shopping: Westfield Penrith; destinations: park;pedestrian_street;station (Penrith, Penrith City Park); within 150m: community_centre;park;tourism; 43 shops/food; landuse retail 48%; zone SP2 100%                                                                                                   |
| -33.914 | 151.241 | Randwick      | Royal Randwick Shopping Centre |              1 |           2.413 | toilet_already_mapped_public | OSM toilet in hex (missing:3;yes:1); shopping: Royal Randwick Shopping Centre; destinations: library;park;pedestrian_street;playground (Randwick Library, Alison Park); within 150m: park;tourism; 62 shops/food; landuse retail 30%; zone SP2 66%                                                                                    |
| -33.879 | 151.213 | Darlinghurst  | Harmony Park                   |              1 |           2.409 | toilet_already_mapped_public | OSM toilet in hex (missing:1); destinations: park;pedestrian_street;playground (Harmony Park); within 150m: community_centre;park;playground;tourism; 80 shops/food; zone MU1 79%                                                                                                                                                     |
| -33.917 | 151.24  | Randwick      | Royal Randwick Shopping Centre |              1 |           2.306 | toilet_already_mapped_public | OSM toilet in hex (missing:4); shopping: Royal Randwick Shopping Centre; destinations: park;pedestrian_street;station;tourism (Randwick, High Cross Park, Beach & Surf Gallery); within 150m: library;park; 43 shops/food; landuse residential 27%; zone SP2 100%                                                                     |
| -33.884 | 151.204 | Haymarket     | Central                        |              1 |           2.184 | toilet_already_mapped_public | OSM toilet in hex (yes:2); destinations: park;pedestrian_street;station (Central); within 150m: library;mall;park;playground;station;tourism; 56 shops/food; zone SP2 44%                                                                                                                                                             |
| -33.882 | 151.216 | Darlinghurst  | Flinders Street Gallery        |              1 |           2.337 | toilet_already_mapped_public | OSM toilet in hex (yes:1); destinations: pedestrian_street;tourism (Flinders Street Gallery, Palangi Gallery, Christopher Vine); within 150m: community_centre;library;park;playground;tourism; 97 shops/food; zone MU1 62%                                                                                                           |
| -33.966 | 151.1   | Hurstville    | Hurstville Central             |              1 |           2.341 | toilet_already_mapped_public | OSM toilet in hex (yes:1); shopping: Hurstville Central; within 150m: community_centre;library;mall;station;tourism; 71 shops/food; landuse residential 41%; zone MU1 42%                                                                                                                                                             |
| -33.924 | 150.924 | Liverpool     | Street University              |              1 |           2.13  | shopping_centre              | shopping: large retail polygon; destinations: community_centre;library;pedestrian_street;pitch (Street University, Yellamundie Library, Club Liverpool); within 150m: mall;park;playground;station; 61 shops/food; zone MU1 97%                                                                                                       |
| -33.97  | 151.08  | Penshurst     | Mortdale                       |              1 |           2.217 | toilet_already_mapped_public | OSM toilet in hex (missing:3); destinations: community_centre;playground;station (Mortdale, Mortdale Men's Shed, Mortdale Village Hall); within 150m: park; 58 shops/food; landuse residential 48%; zone R2 40%                                                                                                                       |
| -33.874 | 151.223 | Woolloomooloo | Kings Cross                    |              1 |           2.343 | toilet_already_mapped_public | OSM toilet in hex (missing:1); destinations: library;pedestrian_street;station;tourism (Kings Cross, Coca-Cola Billboard, Kings Cross Library); within 150m: community_centre;park;playground;tourism; 159 shops/food; zone MU1 49%                                                                                                   |
| -34.054 | 151.153 | Cronulla      | Cronulla                       |              1 |           2.191 | toilet_already_mapped_public | OSM toilet in hex (missing:4); destinations: beach;bus_station;park;pedestrian_street;pitch;playground;station (Cronulla, Monro Park, Cronulla Park); within 150m: library;station; 87 shops/food; landuse retail 21%; zone E2 75%                                                                                                    |
| -33.846 | 151.211 | Milsons Point | Milson Village                 |              1 |           2.01  | toilet_already_mapped_public | OSM toilet in hex (missing:2;private:2;yes:2); shopping: Milson Village; destinations: marketplace;park;pedestrian_street;pitch;playground;station;tourism (Milsons Point, Milsons Point Playground, Big Dipper); within 150m: community_centre;library;park;playground;tourism; 50 shops/food; landuse residential 26%; zone MU1 32% |
| -33.965 | 151.089 | Penshurst     | Penshurst                      |              1 |           2.141 | toilet_already_mapped_public | OSM toilet in hex (missing:1;yes:1); destinations: station (Penshurst); within 150m: park; 47 shops/food; landuse residential 32%; zone E1 32%                                                                                                                                                                                        |
| -33.785 | 151.179 | Roseville     | Roseville                      |              1 |           2.003 | toilet_already_mapped_public | OSM toilet in hex (missing:1); destinations: park;station (Roseville, Roseville Memorial Park); 27 shops/food; landuse residential 52%; zone R2 29%                                                                                                                                                                                   |
