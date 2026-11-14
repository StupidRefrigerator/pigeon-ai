# Bike lanes experiment

Tests whether the toilet model's approach transfers to Sydney bike lanes. It uses the same 16,228 res-9 hexes and the same 5-fold spatial CV by res-6 block, and every number is held-out.

> `experiments/bike/report.md` is not in this commit: the agent that ran the experiment could not write `.md` report files. The full report text is below and still needs adding as that file. All scripts, per-hex data and result CSVs are committed.

## Summary

**The approach transfers.** The toilet recipe (a random forest predicting a quantity per hex; gap = predicted − existing) works with metres of bike lane as the label. With bike features it scores PR-AUC **0.702**, where random order scores 0.325: 5,279 of 16,228 hexes (32.5%) have a lane. 96 of its top 100 hexes and 839 of its top 1,000 have a lane. It predicts 2,382 km against 2,361 km real. Toilets, for comparison, score 0.569 against a random 0.118.

**Best approach: the toilet forest on metres of lane, with bike features added (approach a).**
- **(c) Poisson gradient boosting ranks slightly better** (PR-AUC 0.716 against 0.701, mean of 3 seeds). But it predicts 15% too little lane (2,007 against 2,361 km), and only 59–63 of its top 100 gaps survive a seed change. For the forest, 86–90 survive.
- **(b) The classifier ties with the forest:** PR-AUC 0.704, top-100 stability 87–90.
- **Log length ranks the same (0.704), but its predictions total 338 km**, so they can't be read as metres.
- **Baselines:** road length within 600 m scores 0.521, a population-only forest 0.485, population within 500 m 0.449, and closeness to the CBD 0.432.

**What transfers from toilets unchanged:** the hex grid, the spatial folds and held-out scoring; the forest settings; "existing = max over sources" applied after the model; the SEIFA audit. The toilet's own 45 features already score 0.669.

**What does not transfer:**
1. **Shared features can contain the label.** The three toilet walkability features count shared paths. Dropping them takes the toilet set from 0.669 to 0.618. The pipeline needs to record which source layers built each feature, so a target can drop its own.
2. **Lines leak through neighbours.** Lane length in the rings around a hex lifts PR-AUC to 0.806 (0.830 if the hex itself is included). Most of that is leakage: under spatial CV the neighbours' labels are held-out answers, and the model learns to continue existing lines. Missing links are better as a post-processing column: 734 hexes with no lane would join two separate groups of lane neighbours, and 17 of the top 100 gaps are such links.
3. **"Gap ≥ 1" has no equivalent for metres.** A 200 m threshold flags 1,572 hexes, so the list is the ranked top 100 instead (gaps of 433–831 m).
4. **Painted lanes are policy, not context.** They score PR-AUC 0.252 against a random 0.080, with 35 of the top 100 correct. Off-road paths score 0.659 against 0.288.
5. **There is nothing good to validate the gaps against.** OSM marks planned or under-construction cycleways in only 37 hexes with no lane today. The best model's top 500 contains 2 of them, close to the 1.8 expected at random; ranking by population finds 13.

**Distance to the CBD stays out of the inputs.** It adds 0.004–0.006 PR-AUC and shifts the top 100 from 42 to 36 hexes in SEIFA deciles 1–3.

**Official data:** TfNSW publishes the Existing Bicycle Network as an open shapefile (CC BY, updated monthly). Counting dedicated infrastructure only, it has 2,095 km in the study area against OSM's 2,361 km.
- 4,239 hexes have a lane in both, 1,040 in OSM only and 600 in TfNSW only. Hex length correlation is 0.84.
- The model trained on OSM scores 0.682 against the TfNSW label.
- 27 of the top 100 no-OSM-lane hexes have a TfNSW lane, against 5.5 at random, so TfNSW must count as existing before making the list.
- The two sources split painted and off-road lanes very differently (388 km against 63 km painted), so we model total length only.

**Recommendation for many infrastructure types.** Share:
- The grid, the folds and the eval harness: PR-AUC against base rate, top-k, calibration, top-100 seed stability, SEIFA, second-source and planned-site checks.
- One base feature table, with each column tagged by the source layers that built it.
- A random forest on the natural quantity (count or metres) as the default model. It is calibrated and stable.
- The post-model step: existing = max over sources, then rank by gap.

Per target:
- Label builder and unit.
- Excluded source layers, enforced from the tags.
- Extra features.
- Gap threshold, or ranking only.
- Network or point: networks get a missing-link column, and neighbour-label features are never inputs.
- Planned-site data to validate against.

## Key tables

| Model (seed 0) | PR-AUC | Top 100 | Top 1000 | Predicted km (real 2,361) |
|---|---|---|---|---|
| Baseline: road length within 600 m | 0.521 | 81 | 660 | |
| Baseline: forest on population | 0.485 | 68 | 554 | 2,369 |
| (a) RF length, toilet v12 | 0.669 | 90 | 834 | 2,378 |
| (a) RF length, toilet v12 without walk | 0.618 | 91 | 755 | 2,385 |
| **(a) RF length, bike** | **0.702** | **96** | **839** | **2,382** |
| (a) RF log length, bike | 0.704 | 94 | 841 | 339 |
| (b) RF classifier, bike | 0.704 | 93 | 836 | |
| (c) HGB Poisson, bike | 0.718 | 98 | 879 | 2,045 |
| Leak test: RF length + rings (hex excluded) | 0.806 | 96 | 926 | 2,361 |
| Leak test: RF length + disk (hex included) | 0.830 | 97 | 945 | 2,358 |

| By facility type (RF, bike features) | Random | PR-AUC | Top 100 |
|---|---|---|---|
| Painted lanes | 0.080 | 0.252 | 35 |
| Off-road (separated and shared paths) | 0.288 | 0.659 | 89 |
| All dedicated (OSM) | 0.325 | 0.702 | 96 |
| All dedicated (TfNSW label) | 0.298 | 0.682 | 95 |

## Files

- `experiments/bike/out/best_predictions.csv`: map-ready, every hex. Held-out `predicted_m`, `p_lane`, `existing_m` (larger of OSM and TfNSW), `gap_m`, `missing_link`, `lat`/`lng`.
- `experiments/bike/out/top100_gaps.csv`: the top 100 gaps among hexes with no lane in either source.
- `experiments/bike/out/*.csv`: every table. `experiments/bike/data/*.csv`: per-hex labels and features.
- `experiments/bike/scripts/` and `run_all.sh`: the pipeline.
- Raw downloads (about 1.1 GB: Overpass tiles, Geofabrik PBF, TfNSW zip, terrain tiles) are not in Git. They are listed in `DATA.md`, and `.gitignore` covers `experiments/bike/downloads/` and `*.osm.pbf`.

Nothing outside `experiments/bike/`, `DATA.md` and `.gitignore` changed. `data/review/candidate_review.csv` is untouched.


