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

The model predicts how many public toilets a hexagon would typically have, given what is around it. A hexagon predicted to have at least one more toilet than it has is a **candidate**: a place to check for a missing toilet. After the model, a few post-processing steps turn the predictions into the **recommended list**. The default model is **V12**. Design decisions and their trade-offs are in [docs/model-decisions.md](docs/model-decisions.md).

### Train and evaluate

1. Complete [Setup](#setup).
2. Run the training script from the project root:

   ```sh
   python scripts/train_model.py
   ```

   The run takes about 2.5 minutes. It trains and tests the model, prints a report of every eval, and writes the output files, including the recommended list `data/model/recommendations.csv`.
3. Read the report. Check that the forest beats every baseline and that the predicted total is close to the actual total.
4. Open `data/review/candidate_review.csv` and review candidates from the top. See [Review candidates](#review-candidates).
5. Commit the review file. Keep generated evaluation outputs in `data/model/` uncommitted; only the three shared inference models under `data/model/final/` are included in Git.

Optional flags:

| Flag | Default | Effect |
|---|---|---|
| `--features` | `v12` | Feature set: `v12` (45 columns), `latest` (the previous 28-column default) or `v1` (19 columns). |
| `--threshold` | `1.0` | How many more toilets than exist the prediction must be to flag a candidate. |
| `--target` | `toilets` | Infrastructure type. Only `toilets` exists today. |

A run with non-default flags is an experiment. It prints the report and writes `data/model/`, but leaves the review file unchanged.

### Architecture

**Input.** `data/processed/sydney_extended_features.csv` has one row per H3 resolution-9 hexagon (about 0.1 km²) in the study area: 16,228 rows. The script joins `data/processed/sydney_recreation_features.csv` to it by `hex_id`. The label is `toilet_count`, from the National Public Toilet Map.

| Feature set | Columns | Contents |
|---|---:|---|
| `v12` (default) | 45 | `latest` plus the 17 OpenStreetMap columns below. |
| `latest` | 28 | `v1` plus 1 km buffers and walkability. |
| `v1` | 19 | Population, shops, food, transport and parks inside and within 250 m and 500 m. |

The 45 `v12` columns:

- Population inside the hexagon and within 250 m, 500 m and 1 km.
- Shops, cafes and restaurants, bus stops and train stations inside and within 250 m, 500 m and 1 km.
- Park area inside and within 250 m, 500 m and 1 km, and distance to the nearest park.
- Walkable path length, pedestrian junctions and distance to the nearest footpath.
- Sports grounds (pitches, sports centres, stadiums, tracks) inside and within 250 m, 500 m and 1 km, sports area inside and within 500 m, and distance to the nearest one.
- Playgrounds inside and within 250 m, 500 m and 1 km, and distance to the nearest one.
- Beaches and surf clubs inside and within 250 m, 500 m and 1 km, and distance to the nearest one.

The exact lists, in order, are in `TARGETS` in `src/pigeon_ai/model.py`. The order matters: changing it changes the forest. The OSM toilet counts (`osm_toilets_*`) are never inputs, because they nearly copy the label. They are used only in the recommended list.

The model never sees location (`hex_id`, coordinates or council), SEIFA, demographics or population projections. Each infrastructure type lists its own inputs in `TARGETS` in `src/pigeon_ai/model.py`, so a future target can leave out columns built from its own label.

**Model.** A random forest regressor: 300 decision trees, each grown on a random sample of hexagons and features, with at least 20 hexagons per leaf. The forest's prediction is the average of the trees' predictions, read as an expected toilet count. The chance of at least one toilet is `1 - exp(-prediction)`.

**Training and testing.** Resolution 9 is the unit the model predicts: each row, each prediction and each candidate is one res-9 hexagon. Resolution 6 is used only to decide which hexagons are tested together.

The script uses 5-fold spatial cross-validation. Instead of one fixed test set, it takes 5 turns, and each turn uses a different fifth of Sydney as the test set. After 5 turns, every hexagon has been tested exactly once, by a model that never saw it or its surrounding area.

1. Load the 16,228 hexagons with their 45 input columns and their real toilet count.
2. Put each hexagon in its res-6 block (about 36 km²), then split the 90 blocks into 5 groups of 18.
3. For each group, train a forest on the other 4 groups. Predict this group's hexagons, which are the test set for this turn, and record why each prediction came out as it did (SHAP).
4. Combine the 5 test sets. Each hexagon now has one prediction from a model that never saw it.
5. Compute the evals by comparing those predictions with the real toilet counts. Per-fold evals use each turn's test set on its own.
6. Flag candidates and update the review file. A candidate is a hexagon whose prediction is at least 1.0 more than its real toilet count: a place where similar places in Sydney typically have more toilets. There are two kinds:
   - `no_toilet`: the hexagon has no toilet and is predicted at 1.0 or more.
   - `shortfall`: the hexagon has toilets but is predicted at least 1.0 more, such as 1 toilet predicted at 2.3.
7. Draw the depth-3 decision tree that summarises the forest.
8. Build the recommended list. See [Recommended list](#recommended-list).

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
| `recommendations.csv` | The recommended list, best first. See [Recommended list](#recommended-list). |

### Recommended list

The candidates rank hexagons by gap alone. The recommended list adjusts that ranking for toilets the official map misses and for disadvantage. It uses the seed-0 held-out predictions:

1. **OSM toilets count as existing.** Existing toilets = the larger of the official count and the OSM public toilets in the hexagon. Gap = prediction − existing toilets, floored at 0.
2. **Equity weight.** Priority = gap × (1 + disadvantage). Disadvantage is (11 − SEIFA IRSD decile) / 10, so decile 1 (most disadvantaged) gets 1.0 and decile 10 gets 0.1. Hexagons without SEIFA get the average.
3. **Shortlist.** Take the 120 highest priorities and keep those with a gap of at least 1. This gives 87 hexagons.
4. **400 m walking coverage is a column, not a filter.** `uncovered_400m` is `True` when neither the hexagon nor its 6 neighbours has an existing toilet. One ring of res-9 hexagons is about 400 m of walking.

| Column | Contents |
|---|---|
| `hex_id`, `lat`, `lng` | The hexagon and its centre. |
| `rank` | Priority rank among all 16,228 hexagons. Numbers are skipped where a hexagon was dropped for a gap below 1. |
| `priority`, `gap` | As defined above. |
| `predicted_toilets` | Held-out prediction. |
| `toilet_count`, `osm_toilets_public`, `existing_toilets` | Official count, OSM public toilets, and the larger of the two. |
| `seifa_decile`, `disadvantage` | SEIFA IRSD decile (1 = most disadvantaged; empty if unknown) and the weight above. |
| `uncovered_400m` | No existing toilet within about 400 m of walking. |

The code is in `src/pigeon_ai/postprocess.py`. SEIFA and OSM toilets are used only here, never as model inputs. Missing OSM data is a blind spot: OSM has no sports ground mapped at Ken Birdsey Park or Anthony Skarratt Reserve, two council-planned sites, so the model does not flag them.

### Rebuild the V12 features

The V12 columns are committed in `data/processed/`, so you don't need this to train. To rebuild them from the raw Overpass download:

```sh
python scripts/download_data.py --v12-osm-only
python -I scripts/build_recreation.py
```

The Drive link for this zip is still a TODO; see [DATA.md](DATA.md). The second command writes `sydney_recreation_features.csv`, `sydney_growth_recreation_features.csv` and `osm_toilets.csv`, byte-identical to the committed files. To refresh from today's OpenStreetMap, use `scripts/fetch_overpass.py`; see [DATA.md](DATA.md#updating-the-data). Columns, sources and caveats are in [data/README.md](data/README.md#v12-osm-features-sports-grounds-playgrounds-beaches-and-osm-toilets).

### Evals

All evals use the held-out predictions. Results are from the default `v12` run (seed 0). The `latest` column is the same run's comparison forest.

| Eval | Question it answers | How it is measured | `v12` | `latest` |
|---|---|---|---|---|
| Poisson deviance | How far off are the predicted counts? | Average error for count data. Lower is better. | 0.378. Predicting the average everywhere scores 0.719. | 0.418 |
| PR-AUC | Does the ranking put toilet hexagons first? | Sort hexagons by prediction, highest first, and measure how early the toilet hexagons appear. 1.0 is perfect. | 0.569. Random order scores 0.118. | 0.520 |
| Top-100 hits | Are the most confident predictions right? | Number of the 100 highest predictions that have a toilet. | 85 | 86 |
| Top-1000 hits | Does the ranking hold further down? | Number of the 1,000 highest predictions that have a toilet. | 671 | 616 |
| Baselines | Is the forest better than a simple rule? | The same metrics for ranking by shops within 500 m, a population-only forest, and the average. | Shops ranking 65 top-100 hits. Population-only 48. | |
| Calibration | Can a prediction be read literally? | Group hexagons by predicted count, then compare the average prediction with the average actual count. | Every band within 0.04. Total 2,624 predicted, 2,570 actual. | 2,632 predicted |
| Per-fold | Is the model consistent across areas? | Deviance and PR-AUC for each fold. | Deviance 0.34 to 0.42. | |
| Stability | Do candidates depend on chance? | Rerun with random seeds 1 and 2, and with the `latest` features. Count candidates in common. | 129 to 131 of 135 across seeds. | 120 candidates |
| Fairness | Does the model treat areas differently by disadvantage? | Split hexagons into SEIFA IRSD deciles. Compare predicted with actual toilets and the candidate rate. SEIFA is never a model input. | Predicted/actual 0.91 to 1.17 in every decile. | |
| Recommended list | Does the list avoid existing toilets and favour need? | Of the 120 highest priorities: how many have an OSM toilet, and how many are in SEIFA deciles 1–3 and 8–10. | 87 listed. 10/120 with an OSM toilet; deciles 1–3: 59/120; 8–10: 4/120. | |
| Review | Are the candidates real gaps? | Share of reviewed candidates marked `real_gap`. | Not started. | |

Across seeds 0–2, `v12` averages PR-AUC 0.569 (0.569 to 0.570), deviance 0.378, 85 top-100 hits and 677 top-1000 hits. The v2 experiments behind these numbers are in [docs/findings.md](docs/findings.md#v2-new-inputs-label-fix-400-m-walk-and-equity-10-nov-2026).

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

This reuses the count forest (300 trees, leaf size 20, max_features 0.5),
res-6 spatial CV, seeds 0/1/2, metrics, candidate rule and held-out SHAP.
Outputs go only to the git-ignored `data/model/experiments/` directory; the
review file and default training outputs are untouched.

- `comparison.csv`: one full-coverage row per experiment, including feature/row
  counts, metrics and comparability notes.
- `comparison_v1_area.csv`: all experiments scored on the original V1 hexagons.
- `V1_predictions.csv` through `V10_predictions.csv`: the same schema as the
  default hex predictions (IDs, actual/predicted counts, gap, candidate, fold,
  probability, kind and top three held-out SHAP drivers), ready for a future map.
- `V*_folds.csv`, `V*_feature_importance.csv`, `V*_stability.csv`: fold metrics,
  mean absolute held-out SHAP and candidate overlap across seeds.
- `report.txt`: readable comparison and improvements over V1 by deviance.

For a smoke run use `--versions V2 --no-shap --no-stability --out-dir /tmp/pigeon-smoke`.
Omitting SHAP leaves `top_drivers` empty; normal runs include it.

Experiments use exactly the registered inputs from `load_experiment`, including
`population_density`, which the production model omits as redundant. Thus the
experiment V1 is not identical to `train_model.py --features v1`. V7 explicitly
includes Census age/households and SEIFA for feature comparison: these are
independent of toilet labels, but can encode historical provision inequalities.
Their inclusion is not a recommendation to change production inputs. V8 includes
future population scenarios and is exploratory, not evidence of forecasting
future toilets from historical data. Missing predictors use training-fold median
imputation only (a feature entirely absent from training is filled with zero).
No labels, toilet-derived variables, IDs or location columns enter the forest.

V1–V8 have identical test hexagons and res-6 fold assignments. V9/V10 retain those
assignments for every shared block; new blocks keep their full-area GroupKFold
assignment. The resulting expanded folds can be uneven. All rows in a held-out
block, including added rows, are excluded from training. Full-area V9/V10 metrics
have different populations and must be assessed separately. Their V1-area metrics
compare the same test population, with different training coverage. They do not
measure extrapolation to entirely unseen growth suburbs. All comparisons remain
single spatial partitions, without confidence intervals or hyperparameter tuning;
PR-AUC is average precision, and top-100 hits measure existing toilets, not need.

### Local V1 / V5 / V6 comparison page

For installation and launch commands, see [Running the Model Comparison Webpage](#running-the-model-comparison-webpage). To regenerate the shared models when needed:

```sh
python scripts/train_final_models.py
```

Open **http://127.0.0.1:8000**. Choose a Sydney suburb or listed landmark (for
example Town Hall, Parramatta or Bondi Junction), set a radius in km, and click
**Analyze area**. You can also enter `latitude, longitude`. Pan/zoom any map to
move all three together. Click a hexagon to see its actual count, all three
predictions, nonnegative gaps, candidate flags and model-wide feature importance.
Use `--port 8001` on the server command if port 8000 is occupied; Ctrl+C stops it.

Training performs just one full-data fit per version, using `load_experiment()`
and the existing `make_forest(seed=0)` settings. It preserves the exact registered
20/26/23 features (including density), fits median imputation, and writes
`V1.pkl`, `V5.pkl`, `V6.pkl` and matching readable JSON metadata under
`data/model/final/`. Metadata includes the ordered features, source dataset,
training time, seed, scikit-learn version and feature importance. These six inference artifacts are allowed into Git for teammates to use.
Load only trusted repository or locally trained pickles; regenerate after changing
processed features or the Python/scikit-learn environment.
The server loads them once at startup and never trains on an Analyze request.

Required local feature tables:

- `data/processed/sydney_hex_features.csv` for V1.
- `data/processed/sydney_extended_features.csv` with the 1 km and accessibility
  columns for V5/V6.

These processed files are already in the repository. If rebuilding, use the
existing [data pipeline](data/README.md#running-the-pipeline), then
`python scripts/build_experiments.py --versions V5` and
`python scripts/build_accessibility.py`. The accessibility builder also checks
the existing V9/V10 tables; see [data README](data/README.md) for its prerequisites.
Raw inputs come from the team's shared Drive as described in `DATA.md`.

The committed `data/reference/sydney_places.json` contains 937 Sydney suburb
representative points and selected landmarks. To rebuild it from the existing
raw ABS suburb and Greater Sydney boundary files, run `python scripts/build_places.py`.
Lookup is local; unlisted landmarks/addresses require coordinates. Leaflet 1.9.4 and its license are included in `web/vendor/leaflet/`.
OpenStreetMap basemap tiles need internet access; lookup, inference and hexagon
overlays run locally.
No Node install, frontend build, database or web framework is needed.

The summary's `web/metrics.json` is a small checked-in snapshot of the completed
V1/V5/V6 spatial-CV comparison, with its provenance. Ignored experiment CSVs are
not needed to run the app. Heatmaps run the final full-data models on existing
study-area feature rows; their predictions are in-sample, so use the spatial-CV
metrics for evaluation. Cells are selected by center-to-location great-circle
distance, and circles near the study boundary may have partial coverage.
The same fixed color bins are used on every map. Gap is
`max(0, predicted_count - actual_count)`; candidates have a gap of at least 1.
Feature importance is global forest impurity importance, not a local explanation
or causal evidence. Gaps remain candidates for investigation, not measured need.
This local prototype supports only V1/V5/V6 and does not modify review records.


## Running the Model Comparison Webpage

From the repository root after cloning/pulling, use Python 3.14 (tested with
3.14.3) and the pinned dependencies, especially scikit-learn 1.9.1:

```sh
python3.14 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python scripts/serve_comparison.py
```

On Windows, activate with `.venv\Scripts\activate` instead. Open
**http://127.0.0.1:8000**. Select a place and radius, then click **Analyze**.
No Node installation or frontend build is needed. Internet access is needed for
OpenStreetMap tiles; the interface, location lookup and predictions are local.

The repository must include:

- `data/processed/sydney_hex_features.csv` and
  `data/processed/sydney_extended_features.csv` (with 1 km/accessibility columns).
- `data/model/final/V1.pkl`, `V5.pkl`, `V6.pkl` and their matching `.json` files.
- `data/reference/sydney_places.json`, `web/` (including vendored Leaflet and its
  license), `src/pigeon_ai/` and the server script.

The processed tables are already tracked. The six saved-model files are about
29 MB total and are explicitly allowed by `.gitignore`; include them in the
commit along with the new webpage source. No raw data or ignored experiment
outputs are required for normal startup. The V1–V10 report table is a static
snapshot in `web/index.html` (V10 pending); `web/metrics.json` supplies the saved
V1/V5/V6 evaluation metadata. Neither reads local experiment CSVs at runtime.

If the saved models are absent or need replacing, run this once before serving:

```sh
python scripts/train_final_models.py
```

If rebuilding processed tables from the team's original raw snapshot is necessary,
install the native osmium/GDAL tools described in [data/README.md](data/README.md),
then use the existing pipeline:

```sh
python scripts/download_data.py "<share link to pigeon-ai-raw.zip itself>"
python scripts/run_pipeline.py
python scripts/build_experiments.py --versions V5 V9 V10
python scripts/build_accessibility.py
python scripts/train_final_models.py
python scripts/serve_comparison.py
```

Alternatively, unzip the team's archive directly into `data/raw/` as described in
[DATA.md](DATA.md). V9/V10 feature tables are included in the rebuild command
because the existing accessibility builder checks them; this does not train or
evaluate those models. Use the original Drive snapshot to preserve input values.
Do not run `compare_experiments.py` just to launch the webpage.
