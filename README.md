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

The model predicts how many public toilets a hexagon would typically have, given what is around it. A hexagon predicted to have at least one more toilet than it has is a **candidate**: a place to check for a missing toilet. Design decisions and their trade-offs are in [docs/model-decisions.md](docs/model-decisions.md).

### Train and evaluate

1. Complete [Setup](#setup).
2. Run the training script from the project root:

   ```sh
   python scripts/train_model.py
   ```

   The run takes about 2.5 minutes. It trains and tests the model, prints a report of every eval, and writes the output files.
3. Read the report. Check that the forest beats every baseline and that the predicted total is close to the actual total.
4. Open `data/review/candidate_review.csv` and review candidates from the top. See [Review candidates](#review-candidates).
5. Commit the review file. Keep generated evaluation outputs in `data/model/` uncommitted; the comparison page's `web/predictions.csv` and `web/metrics.json` are the only generated files in Git.

Optional flags:

| Flag | Default | Effect |
|---|---|---|
| `--features` | `latest` | Feature set: `latest` (28 columns) or `v1` (19 columns). |
| `--threshold` | `1.0` | How many more toilets than exist the prediction must be to flag a candidate. |
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
6. Flag candidates and update the review file. A candidate is a hexagon whose prediction is at least 1.0 more than its real toilet count: a place where similar places in Sydney typically have more toilets. There are two kinds:
   - `no_toilet`: the hexagon has no toilet and is predicted at 1.0 or more.
   - `shortfall`: the hexagon has toilets but is predicted at least 1.0 more, such as 1 toilet predicted at 2.3.
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
| Stability | Do candidates depend on chance? | Rerun with random seeds 1 and 2, and with the `v1` features. Count candidates in common. | 113 to 116 of 120 across seeds. |
| Fairness | Does the model treat areas differently by disadvantage? | Split hexagons into SEIFA IRSD deciles. Compare predicted with actual toilets and the candidate rate. SEIFA is never a model input. | Predicted/actual 0.91 to 1.14 in every decile. |
| Review | Are the candidates real gaps? | Share of reviewed candidates marked `real_gap`. | Not started. |

### Review candidates

`data/review/candidate_review.csv` has one row per candidate. The script fills the model columns. A reviewer fills the human columns.

| Column | Filled by | Values |
|---|---|---|
| `hex_id`, `lat`, `lng` | Script | Location of the hexagon. |
| `toilet_count`, `kind` | Script | Real toilet count, and `no_toilet` or `shortfall`. |
| `predicted_toilets`, `p_any_toilet`, `top_drivers` | Script | Updated on every default run. |
| `first_flagged` | Script | Date the hexagon first became a candidate. |
| `still_candidate` | Script | `False` if a later run no longer flags it. The row is kept. |
| `status` | Reviewer | Exactly one of the four statuses below. |
| `reviewer`, `reviewed_on`, `notes` | Reviewer | Free text. |

To review a candidate:

1. Open `lat`, `lng` in a map, such as Google Maps.
2. Set `status`:
   - `real_gap`: a public toilet (or, for a `shortfall`, another one) would plausibly belong here.
   - `toilet_not_on_map`: a toilet exists, such as inside a shopping centre, but the National Public Toilet Map does not list it. For a `shortfall`, this means extra toilets exist beyond those listed.
   - `not_public_place`: the area is not open to the public, such as private or industrial land.
   - `unreviewed`: not checked yet. This is the default.
3. Fill `reviewer`, `reviewed_on` and `notes`.

Each default run merges new results into the file. It updates the script columns, adds new candidates as `unreviewed`, and never changes the reviewer columns. Running it twice in a row gives the same file. A status outside the four values stops the run with an error naming the row.

## Docs

- [data/README.md](data/README.md): how the dataset is built, its columns and its assumptions.
- [DATA.md](DATA.md): getting the raw data from Google Drive.
- [docs/model-decisions.md](docs/model-decisions.md): model design decisions and their trade-offs.

The processed datasets in `data/processed/` are committed. You don't need raw data to work on the model.

### Compare dataset experiments V1–V10

```sh
python scripts/compare_experiments.py
```

Every experiment is scored with held-out predictions: 5-fold spatial cross-validation
by res-6 block, so each hex is predicted by a forest that never saw its block. It uses
the same forest (300 trees, leaf size 20, max_features 0.5), seed 0, metrics and
candidate rule as `train_model.py`. Outputs go only to the git-ignored
`data/model/experiments/` directory. The review file is untouched.

- `comparison.csv`: one row per experiment with deviance, PR-AUC, top-100 hits,
  candidates, and hex and feature counts.
- `V1_predictions.csv` through `V10_predictions.csv`: hex ID, toilet count,
  held-out prediction and fold.

Options: `--versions V2 V5` to run some experiments, `--out-dir` to write elsewhere.
`latest` is also accepted: the production feature set from `train_model.py`.

Experiments use exactly the registered inputs from `load_experiment`, including
`population_density`, which the production model omits as redundant. So the
experiment V1 is not identical to `train_model.py --features v1`. V7 includes
Census age/households and SEIFA. These do not come from the toilet labels, but they
can encode historical provision inequalities. That does not recommend them for
production. V8 uses future population scenarios and is exploratory. Missing
predictors are imputed with training-fold medians only.

V1–V8 share the same 16,228 hexes. V9 and V10 cover different hex sets and use
their own spatial folds, so their numbers are not comparable to V1–V8. Every
comparison is one spatial partition, with no confidence intervals or tuning.
PR-AUC is average precision. Top-100 hits count existing toilets, not need.

### Comparison page

The page is a static site in `web/`. It is deployed on Vercel. To run it locally, see [Running the Model Comparison Webpage](#running-the-model-comparison-webpage).
It shows four models side by side: V1, V5, V6 and Latest. Latest is the production
feature set: V5's 1 km features plus V6's walkability features, without
`population_density`.

Choose a Sydney suburb or listed landmark (for
example Town Hall, Parramatta or Bondi Junction), set a radius in km, and click
**Analyze**. You can also enter `latitude, longitude`. Pan or zoom any map to move
all of them together. Click a hexagon to see its actual count, every model's
prediction, gap, candidate flag and model-wide importance.

The maps show held-out predictions. Each hex is predicted by a forest that never
saw its res-6 block (about 36 km²), so a hex's own toilet count cannot shrink its
own gap. Gap is `max(0, predicted - actual)`. A candidate has
`predicted - actual >= 1`, the same rule as `model.is_candidate`. The Latest map's
candidates are the 120 hexes in `data/review/candidate_review.csv`. The same fixed
colour bins are used on every map. Importance is mean absolute SHAP over the
held-out rows. It is not a local explanation or causal evidence. Gaps are
candidates to investigate, not measured need. Cells are selected by the distance
from the location to the hex centre, so circles near the study boundary may be
partly covered. The page never changes the review file.

The browser loads three committed files and does the lookup itself, in `web/analyze.js`. Nothing is trained:

- `web/predictions.csv`: `hex_id`, `toilet_count`, `fold`, then one held-out
  prediction column per model.
- `web/metrics.json`: per-model deviance, PR-AUC, top-100 hits, candidates and
  importance, with a `source` note.
- `web/places.json`: 937 Sydney suburb representative points and selected landmarks.

To rebuild them after the processed features or the forest settings change (about
10 minutes):

```sh
python scripts/build_comparison_page.py
```

There is no saved final model yet. A final model on the `latest` features, fit on all
hexes to score new areas, is separate future work. It must not feed these maps,
because predicting the hexes it was trained on hides gaps.

Required local feature tables:

- `data/processed/sydney_hex_features.csv` for V1.
- `data/processed/sydney_extended_features.csv` with the 1 km and accessibility
  columns for V5, V6 and Latest.

These files are already in the repository. To rebuild them, use the existing
[data pipeline](data/README.md#running-the-pipeline), then
`python scripts/build_experiments.py --versions V5` and
`python scripts/build_accessibility.py`. Raw inputs come from the team's shared
Drive as described in `DATA.md`.

To rebuild `web/places.json` from the existing
raw ABS suburb and Greater Sydney boundary files, run `python scripts/build_places.py`.
Unlisted landmarks and addresses need coordinates. Leaflet 1.9.4 and h3-js 4.5.0,
with their licenses, are in `web/vendor/`. OpenStreetMap basemap tiles need
internet access. There is no frontend build, database or web framework.

## Running the Model Comparison Webpage

The page is static, so any file server works. From the repository root:

```sh
python -m http.server 8000 --directory web
```

Open **http://127.0.0.1:8000**. Select a place and radius, then click **Analyze**.
No packages, processed tables, raw data or training are needed.

To deploy, `vercel.json` publishes `web/` with no build step. From the repository
root, run `npx vercel --prod`. To test the lookup, run
`node --test tests/analyze.test.js`. The V1–V10
table at the top of the page is a static snapshot in `web/index.html` (V10 pending).

To rebuild the processed tables from the team's raw snapshot, install the native
osmium/GDAL tools described in [data/README.md](data/README.md), then:

```sh
python scripts/download_data.py "<share link to pigeon-ai-raw.zip itself>"
python scripts/run_pipeline.py
python scripts/build_experiments.py --versions V5 V9 V10
python scripts/build_accessibility.py
python scripts/build_comparison_page.py
```

Alternatively, unzip the team's archive directly into `data/raw/` as described in
[DATA.md](DATA.md). V9 and V10 are in the rebuild because the accessibility builder
checks their tables. Use the original Drive snapshot to keep the input values.
