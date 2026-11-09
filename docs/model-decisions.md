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

## Experiments

These are not production. The production model and review file are unchanged.

### Good-areas model (2026-11-09)

The model is trained only on well-served blocks and applied everywhere, so gaps are measured against good provision instead of Sydney's average. Good blocks are the top third by the ratio of real toilets to the production model's held-out prediction, among blocks with at least 5 predicted toilets. Code: `src/pigeon_ai/good_areas.py`. Candidates go to `data/review/candidate_review_good_areas.csv`.

Caveats:

- Selection uses the production model, so its blind spots carry over.
- Choosing blocks where actual is above predicted partly picks luck. Some of those blocks would regress to the mean.
- Good blocks may only be councils that record toilets more completely. Then the model learns recording habits, not need.
- It predicts above today's counts by design. Higher deviance is expected.
- Only candidate review can show whether it is better.

## Change log

- 2026-11-02: First version. Random forest replaces the earlier gradient-boosting proposal after the spatial comparison.
- 2026-11-02: Moved to PR #4's extended dataset and the 28-column `latest` feature set. Added the target registry, the review file and its statuses, and the evals table. `load_experiment` returns counts again.
- 2026-11-02: Candidate rule now flags shortfalls too: a hex with toilets whose prediction is at least 1 higher. The review file gains `toilet_count` and `kind`.
- 2026-11-09: Added the good-areas experiment (not production) with its own review file.

## Dataset comparison extension (2026-11-06)

`compare_experiments.py` tests the declared V1–V10 datasets without changing the
production choices above. It deliberately retains density and enables V7's
independently sourced Census/SEIFA inputs and V8's projection inputs. The former
can reproduce provision bias; the latter is only an exploratory scenario. See
README's comparison section for fold anchoring, training-only imputation and
output definitions. Expanded-area full metrics are not ranked against V1–V8.

The real-data audit found 370 missing values per V7 age-share column, 2,392
missing SEIFA values and 222 missing V8 growth-percentage values. These remain
missing in the source datasets and are imputed only inside training folds.
The density/population ratio actually ranges from 7.89365 to 7.90214 for
positive-population V1 cells: the production redundancy argument is approximate,
not exact. The comparison retains density as declared by the experiment registry.

## Local comparison prototype (2026-11-06)

The prototype saves full-data V1/V5/V6 forests for interactive inference, reusing
the registered feature lists and existing forest settings at seed 0. V1 is the
baseline, V5 has the best ranking metrics, and V6 the lowest deviance in the saved
same-area experiment comparison. A median imputer is saved with each forest.
The page displays the existing spatial-CV metrics, rather than evaluating these
full-data fits on their own training rows. Its live heatmaps are in-sample and
may hide gaps; use them to compare behavior, not to claim validation performance.
The displayed gap is clamped at zero, with the unchanged candidate threshold 1.
For this simple prototype, model-wide impurity importance replaces expensive
per-request SHAP. No review-file updates or model-evaluation reruns are involved.
