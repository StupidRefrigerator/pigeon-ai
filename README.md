# PIGEON-AI

Pigeon AI helps government infrastructure planners decide where to place new public infrastructure, starting with public toilets in Greater Sydney.

A planner gives an area, radius, infrastructure type and budget. An ML model scores each part of the city, and an LLM turns those scores into location recommendations with plain-text justifications.

## Structure

```text
data/        Dataset: processed features (committed), reference IDs, raw data (Drive)
src/         Python package (pigeon_ai)
scripts/     Command-line entry points
notebooks/   Exploration and visualisation
```

## Setup

```sh
python3.14 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Model

The model predicts how many public toilets a hexagon would typically have, given what is around it. A hexagon with a high prediction and no toilet is a **candidate**: a place to check for a missing toilet. Design decisions and their trade-offs are in [docs/model-decisions.md](docs/model-decisions.md).

### Train and evaluate

1. Complete [Setup](#setup).
2. Run the training script from the project root:

   ```sh
   python scripts/train_model.py
   ```

   The run takes about 2.5 minutes. It trains and tests the model, prints a report of every eval, and writes the output files.
3. Read the report. Check that the forest beats every baseline and that the predicted total is close to the actual total.
4. Open `data/review/candidate_review.csv` and review candidates from the top. See [Review candidates](#review-candidates).
5. Commit the review file. Do not commit `data/model/`; the script regenerates it.

Optional flags:

| Flag | Default | Effect |
|---|---|---|
| `--features` | `latest` | Feature set: `latest` (28 columns) or `v1` (19 columns). |
| `--threshold` | `1.0` | Predicted count at or above which an empty hexagon is a candidate. |
| `--target` | `toilets` | Infrastructure type. Only `toilets` exists today. |

A run with non-default flags is an experiment. It prints the report and writes `data/model/`, but leaves the review file unchanged.

### Architecture

**Input.** `data/processed/sydney_extended_features.csv` has one row per H3 resolution-9 hexagon (about 0.1 km²) in the study area: 16,228 rows. The label is `toilet_count`. The `latest` feature set has 28 columns:

- Population inside the hexagon and within 250 m, 500 m and 1 km.
- Shops, cafes and restaurants, bus stops and train stations inside and within 250 m, 500 m and 1 km.
- Park area inside and within 250 m, 500 m and 1 km, and distance to the nearest park.
- Walkable path length, pedestrian junctions and distance to the nearest footpath.

The model never sees location (`hex_id`, coordinates or council), SEIFA, demographics or population projections. Each infrastructure type lists its own inputs in `TARGETS` in `src/pigeon_ai/model.py`, so a future target can leave out columns built from its own label.

**Model.** A random forest regressor: 300 decision trees, each grown on a random sample of hexagons and features, with at least 20 hexagons per leaf. The forest's prediction is the average of the trees' predictions, read as an expected toilet count. The chance of at least one toilet is `1 - exp(-prediction)`.

**Training and testing.** Resolution 9 is the unit the model predicts: each row, each prediction and each candidate is one res-9 hexagon. Resolution 6 is used only to decide which hexagons are tested together.

The script uses 5-fold spatial cross-validation. Instead of one fixed test set, it takes 5 turns, and each turn uses a different fifth of Sydney as the test set. After 5 turns, every hexagon has been tested exactly once, by a model that never saw it or its surrounding area.

1. Load the 16,228 hexagons with their 28 input columns and their real toilet count.
2. Put each hexagon in its res-6 block (about 36 km²), then split the 90 blocks into 5 groups of 18.
3. For each group, train a forest on the other 4 groups. Predict this group's hexagons, which are the test set for this turn, and record why each prediction came out as it did (SHAP).
4. Combine the 5 test sets. Each hexagon now has one prediction from a model that never saw it.
5. Compute the evals by comparing those predictions with the real toilet counts. Per-fold evals use each turn's test set on its own.
6. Flag candidates and update the review file. A candidate is a hexagon predicted at 1.0 or more that has no toilet: a place where a toilet would be typical but is missing.
7. Draw the depth-3 decision tree that summarises the forest.

Each run retrains from scratch. The script does not save a trained model file, because every prediction it reports comes from the cross-validation models.

**Outputs.** In `data/model/` (regenerated each run, not committed):

| File | Contents |
|---|---|
| `hex_predictions.csv` | Prediction, chance of a toilet, gap, candidate flag, fold and top three drivers for each hexagon. |
| `metrics.csv` | Headline metrics for the forest and each baseline. |
| `calibration.csv`, `folds.csv`, `stability.csv`, `fairness.csv` | One file per eval below. |
| `shap_values.csv` | SHAP value of every feature for every hexagon: how far each feature pushed that prediction up or down, in toilets. |
| `feature_importance.csv` | Mean absolute SHAP value per feature. |
| `decision_tree.png` | The depth-3 summary tree. |

### Evals

All evals use the held-out predictions. Results are from the current `latest` run.

| Eval | Question it answers | How it is measured | Result |
|---|---|---|---|
| Poisson deviance | How far off are the predicted counts? | Average error for count data. Lower is better. | 0.418. Predicting the average everywhere scores 0.719. |
| PR-AUC | Does the ranking put toilet hexagons first? | Sort hexagons by prediction, highest first, and measure how early the toilet hexagons appear. 1.0 is perfect. | 0.519. Random order scores 0.118. |
| Top-100 hits | Are the most confident predictions right? | Number of the 100 highest predictions that have a toilet. | 86 |
| Baselines | Is the forest better than a simple rule? | The same metrics for ranking by shops within 500 m, a population-only forest, and the average. | Shops ranking 65 top-100 hits. Population-only 48. |
| Calibration | Can a prediction be read literally? | Group hexagons by predicted count, then compare the average prediction with the average actual count. | Every band within 0.06. Total 2,632 predicted, 2,570 actual. |
| Per-fold | Is the model consistent across areas? | Deviance and PR-AUC for each fold. | Deviance 0.37 to 0.45. |
| Stability | Do candidates depend on chance? | Rerun with random seeds 1 and 2, and with the `v1` features. Count candidates in common. | 101 to 103 of 106 across seeds. |
| Fairness | Does the model treat areas differently by disadvantage? | Split hexagons into SEIFA IRSD deciles. Compare predicted with actual toilets and the candidate rate. SEIFA is never a model input. | Predicted/actual 0.91 to 1.14 in every decile. |
| Review | Are the candidates real gaps? | Share of reviewed candidates marked `real_gap`. | Not started. |

### Review candidates

`data/review/candidate_review.csv` has one row per candidate. The script fills the model columns. A reviewer fills the human columns.

| Column | Filled by | Values |
|---|---|---|
| `hex_id`, `lat`, `lng` | Script | Location of the hexagon. |
| `predicted_toilets`, `p_any_toilet`, `top_drivers` | Script | Updated on every default run. |
| `first_flagged` | Script | Date the hexagon first became a candidate. |
| `still_candidate` | Script | `False` if a later run no longer flags it. The row is kept. |
| `status` | Reviewer | Exactly one of the four statuses below. |
| `reviewer`, `reviewed_on`, `notes` | Reviewer | Free text. |

To review a candidate:

1. Open `lat`, `lng` in a map, such as Google Maps.
2. Set `status`:
   - `real_gap`: a public toilet would plausibly belong here and none exists.
   - `toilet_not_on_map`: a toilet exists, such as inside a shopping centre, but the National Public Toilet Map does not list it.
   - `not_public_place`: the area is not open to the public, such as private or industrial land.
   - `unreviewed`: not checked yet. This is the default.
3. Fill `reviewer`, `reviewed_on` and `notes`.

Each default run merges new results into the file. It updates the script columns, adds new candidates as `unreviewed`, and never changes the reviewer columns. Running it twice in a row gives the same file. A status outside the four values stops the run with an error naming the row.

## Docs

- [data/README.md](data/README.md): how the dataset is built, its columns and its assumptions.
- [DATA.md](DATA.md): getting the raw data from Google Drive.
- [docs/model-decisions.md](docs/model-decisions.md): model design decisions and their trade-offs.

The processed datasets in `data/processed/` are committed. You don't need raw data to work on the model.
