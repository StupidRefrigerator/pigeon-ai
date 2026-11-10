# Model decisions

This page records the modelling decisions for the toilet MVP, why we made them, and what each one costs. Decisions will change. When one does, edit its entry and add a line to the change log at the bottom.

`scripts/train_model.py` reproduces every number here. It uses 5-fold spatial cross-validation on `data/processed/sydney_extended_features.csv` (16,228 hexes, 2,570 toilets in 1,911 hexes). See `data/README.md` for how to run it and what each output contains.

## What the model can and cannot claim

The target, `toilet_count`, records where toilets exist today. The model therefore learns where toilets usually sit, given what surrounds a place. It does not learn where toilets are needed.

A hex the model predicts at 1.2 with no toilet, or at 2.3 with one, is unusual compared with similar places in Sydney. Call it a **candidate**, not unmet need. The model ranks a busy place without a toilet highly, and that is the useful output. It measures gaps against Sydney's own typical provision. If Sydney under-provides a whole type of area, the model learns that as normal, which is why we run the fairness audit.

We accept this for the MVP and state it in the demo. Stronger claims need a better target, such as planner-assessed provision against a shared rubric, which we do not have.

## Settled decisions

Each entry lists the decision, the reason, and the trade-off.

1. **Predict a count per res-9 hex.** A res-9 hex is about 0.1 km², roughly a couple of city blocks. Toilets serve a walking catchment, so a small cell fits. The trade-off is that one hex holds little data, and 88% of hexes have no toilet.

2. **Train on the study area with the `latest` feature set.** The data is `sydney_extended_features.csv` from PR #4. The `latest` set has 28 inputs: the 19 V1 features, the six 1 km counts, and three walking-network features. It beats V1 slightly (deviance 0.418 against 0.426, PR-AUC 0.519 against 0.511), and 92 of V1's 100 candidates stay. The growth-suburb and all-Sydney files are for scoring later, not training. Training on all of Greater Sydney did not improve predictions in the study area (0.428). One risk is that footpath mapping in OSM is more complete in some councils than others.

3. **Each infrastructure type lists its own inputs.** `TARGETS` in `src/pigeon_ai/model.py` maps a target to its label and feature sets. A future target drops any column built from its own label. A parks target, for example, would drop `park_*`. Toilets drop nothing except `population_density`.

4. **Use a random forest regressor.** On our data it matches or slightly beats gradient boosting. A forest averages 300 trees, each grown on a random sample of hexes and features. A forest cannot be drawn, so we also fit a depth-3 surrogate tree to the forest's predictions for the report. It matches them with R² 0.79.

5. **Control complexity with leaf size, not L1 or L2.** L1 and L2 shrink the coefficients of linear models, and a forest has none. It is kept simple with `min_samples_leaf=20` and `max_features=0.5`. Only 1,911 hexes have a toilet, so small leaves would memorise individual town centres.

6. **Read the output as an expected count and a probability.** The forest predicts an expected count, such as 1.2. The chance of at least one toilet is `1 - exp(-prediction)`, so 1.2 means about 70%.

7. **Do not rebalance the classes.** Oversampling, SMOTE, and undersampling all raise the share of toilet hexes the model sees. Every prediction then goes up, and "1.2" stops meaning 1.2. The candidate rule reads predictions literally, so they must stay on the real scale.

8. **Drop `population_density`.** It equals `population_est × 7.897` in every row.

9. **Keep the cumulative buffer features.** `shop_500m` includes the shops within 250 m and inside the hex. Rings (500 m minus 250 m) scored worse, and so did inside-only features.

10. **Give the model no location features.** No latitude, longitude, council, `hex_id`, or neighbouring toilet counts. Those let the model learn "this part of Sydney has few toilets", and it would then predict low for an under-served place. The trade-off is a lower accuracy score.

11. **Keep socioeconomic data out of the inputs.** SEIFA, age groups, and households come from PR #4's V7. Adding them did not improve the score (0.423), and they would teach the model historical provision patterns directly. They are used only in the fairness audit. Population projections (V8) also stay out, because they describe the future and our labels describe today.

12. **Validate on held-out geographic blocks.** Hexes are grouped by their res-6 H3 parent, about 36 km² each, giving 90 blocks. The blocks are dealt into 5 groups of 18. Each round trains on 4 groups and predicts the fifth, so every hex is predicted once by a model that never saw its area. A random split scored almost the same, so the score is not inflated by neighbours. The block split matters for the output, because a model that has seen a hex repeats its real count and hides the gap.

13. **Flag a candidate when the prediction is at least 1 more than the real count.** For an empty hex this means a prediction of 1 or more, which is at least a 63% chance of a toilet. For a hex with toilets it is a `shortfall`, such as 1 toilet predicted at 2.3. The threshold is a choice, not something learned. At 1 the rule flags 120 hexes: 106 with no toilet and 14 shortfalls, all of them hexes with 1 toilet predicted at 2.0 to 2.4. For empty hexes alone, a threshold of 0.5 would flag 633 and 1.5 would flag 24.

14. **Track every candidate in a review file.** `data/review/candidate_review.csv` is committed. A person sets `status` to `unreviewed`, `real_gap`, `toilet_not_on_map`, or `not_public_place`, and any other value fails the next run. Reruns never change human columns, and only the default configuration updates the file. The top candidates include large shopping centres such as Liverpool and Bondi Junction, which probably have toilets the public map does not list.

15. **Explain each prediction with SHAP.** Each hex gets its top three drivers, and the mean size per feature gives overall importance. Park area inside the hex and shops and food nearby lead. Importance means "helped predict existing toilets", not "causes need".

## Evals

`scripts/train_model.py` prints all of these and saves them under `data/model/`.

| Eval | Question | Current result |
|---|---|---|
| Poisson deviance | How far off are the predicted counts? | 0.418, against 0.719 for guessing the average |
| PR-AUC | Does the ranking put toilet hexes first? | 0.519, against 0.118 for random order |
| Top-100 hits | How many of the 100 highest predictions have a toilet? | 86 |
| Baselines | Is the forest better than a simple rule? | Ranking by shops within 500 m gets 65 of the top 100 and PR-AUC 0.29. Population alone gets 48 and 0.25. |
| Calibration | Can predictions be read literally? | Predicted 2,632 against 2,570 actual. Every prediction band matches its actual average within 0.06. |
| Per-fold | Is performance consistent across areas? | Deviance 0.37 to 0.45 and PR-AUC 0.46 to 0.58 across the 5 folds |
| Stability | Do candidates survive a different random seed or feature set? | 113 to 116 of 120 survive a new seed. 105 of V1's 115 survive the feature change. |
| Fairness | Do candidates or errors differ by disadvantage? | Predicted/actual ratio 0.91 to 1.14 in every SEIFA decile. Deciles 9 and 10 (least disadvantaged) have 1.5 candidates per 1,000 hexes, against 5 to 13 elsewhere. Not yet explained. |
| Review | Are candidates real gaps? | Not started. 120 candidates are `unreviewed`. |

The review eval is the one that decides whether the product works. Review at least the top 30 candidates and report the share that are `real_gap`.

## Out of scope for the MVP

- Scoring growth suburbs or new areas. That needs one final forest trained on all hexes, and a growth suburb's future shops and parks do not exist yet. Projections only support a what-if scenario.
- Monotonic constraints, hyperparameter tuning, and new features such as playgrounds or beaches.
- Other infrastructure types. Add an entry to `TARGETS` without that type's own features.
- The LLM report and the map front end.

## Open questions

- **Why do the least disadvantaged deciles get few candidates?** Their predictions match their actual totals, so the model is not under-predicting there. Possible reasons include fewer busy centres, or better existing coverage. Comparing similar hexes across deciles would separate these.
- **Are counts of 5 to 13 in one hex real?** They might be several records for one park or station. Checking needs the raw toilet file.
- **How complete is the National Public Toilet Map by council?** Uneven coverage would show up as false candidates in some councils. Review statuses of `toilet_not_on_map` by council will show it.
- **Should council be a feature?** It would absorb council policy and recording differences, but it would also hide a council that under-provides everywhere. Currently we leave it out.

## Change log

- 2026-11-02: First version. Random forest replaces the earlier gradient-boosting proposal after the spatial comparison.
- 2026-11-02: Moved to PR #4's extended dataset and the 28-column `latest` feature set. Added the target registry, the review file and its statuses, and the evals table. `load_experiment` returns counts again.
- 2026-11-02: Candidate rule now flags shortfalls too: a hex with toilets whose prediction is at least 1 higher. The review file gains `toilet_count` and `kind`.

## Dataset comparison extension (2026-11-06, revised 2026-11-09)

`compare_experiments.py` tests the declared V1–V10 datasets without changing the
production choices above. It deliberately retains density and enables V7's
independently sourced Census/SEIFA inputs and V8's projection inputs. The former
can reproduce provision bias. The latter is only an exploratory scenario. See the
README's comparison section for the outputs.

Every experiment is scored with held-out predictions from `model.cross_validate`
(seed 0). The first version also ran SHAP, seed stability and fold anchoring for
V9/V10. That was dropped to keep the comparison simple. V9 and V10 use their own
spatial folds and cover different hexes, so their numbers are not ranked against V1–V8.

The real-data audit found 370 missing values per V7 age-share column, 2,392
missing SEIFA values and 222 missing V8 growth-percentage values. These remain
missing in the source datasets and are imputed only inside training folds.
The density/population ratio actually ranges from 7.89365 to 7.90214 for
positive-population V1 cells: the production redundancy argument is approximate,
not exact. The comparison retains density as declared by the experiment registry.

## Local comparison page (2026-11-06, revised 2026-11-09)

The first version fit V1/V5/V6 forests on all hexes and predicted those same hexes.
A hex's own toilet count then shaped its own prediction, so gaps shrank and the
maps hid the places we want to find. We deleted those fits.

The page now shows held-out predictions: 5-fold spatial CV by res-6 block, seed 0,
so each hex is predicted by a forest that never saw its block. It compares V1, V5,
V6 and Latest (V5's 1 km features plus V6's walkability features, without
`population_density`; the production feature set). The predictions are committed
in `web/predictions.csv` with their metrics in `web/metrics.json`, so the server
trains nothing. The Latest map's 120 candidates equal the review file's 120.

The displayed gap is clamped at zero, with the unchanged candidate threshold 1.
Model-wide importance is mean absolute SHAP on held-out rows. A final model on
`latest` for scoring new areas is separate future work.

## V12: sports grounds, playgrounds and beaches; OSM toilets after the model (2026-11-10)

V12 is the default from this date. It is the same forest with the 28 `latest` columns plus 17 OpenStreetMap columns: sports grounds, playgrounds and beaches (counts, sports area and nearest distance). The label is still the official `toilet_count`. The tests are in `experiments/v2/`, and the numbers are in [findings.md](findings.md#v2-new-inputs-label-fix-400-m-walk-and-equity-10-nov-2026). All numbers are held-out, as the mean of seeds 0–2.

**Why V12.** It was the only change that beat the seed noise.

| | `latest` | V12 |
|---|---|---|
| PR-AUC | 0.520 | 0.569 (seed spread ±0.001) |
| Poisson deviance | 0.417 | 0.378 |
| Top-1000 hits | 617 | 677 |
| Council-planned sites in the top 10% | 26/42 | 30/42 |
| Growth-suburb toilet hexes in the top 100 | 24/35 | 22/35 |

The growth result is slightly worse, but this is 2 hexes of 35. The two biggest misses, Ken Birdsey Park and Anthony Skarratt Reserve, are still missed: OSM has no sports ground mapped at either.

**Why OSM toilets are applied after the model, not as labels.** OSM lists toilets that the official map misses, in 272 study hexes. We tried both uses:

- Retraining on `max(official, OSM public)` as the label made the model worse: PR-AUC 0.506, 29% too many toilets predicted, and 267 candidates.
- Keeping the official label and counting OSM toilets as existing only when building the list keeps the better model. Of the top 120 picks, those that already have an OSM public toilet fall from 39 to 9 (10 with the equity weight; `experiments/v2/combos/out/summary_table.csv`).

**The recommended list.** After the model: existing toilets = max(official, OSM public); gap = prediction − existing; priority = gap × (1 + disadvantage), where disadvantage is (11 − SEIFA IRSD decile) / 10; take the 120 highest priorities and keep those with gap ≥ 1. The equity weight moves picks from deciles 8–10 to deciles 1–3 (59 of the top 120 in deciles 1–3, 4 in 8–10). SEIFA is still never a model input.

**Why 400 m walking coverage is a column, not a filter.** As a filter, only 5–20 of its 120 picks were real gaps and 0–3 were near a council plan. It is kept as `uncovered_400m` for the map.
