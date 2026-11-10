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
5. Commit the review file. Keep generated evaluation outputs in `data/model/` uncommitted; the comparison page's `web/predictions.csv` and `web/metrics.json` are the only generated files in Git.

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

### Local comparison page

To run the page, see [Running the Model Comparison Webpage](#running-the-model-comparison-webpage).
It shows four models side by side: V1, V5, V6 and Latest. Latest is the production
feature set: V5's 1 km features plus V6's walkability features, without
`population_density`.

Open **http://127.0.0.1:8000**. Choose a Sydney suburb or listed landmark (for
example Town Hall, Parramatta or Bondi Junction), set a radius in km, and click
**Analyze**. You can also enter `latitude, longitude`. Pan or zoom any map to move
all of them together. Click a hexagon to see its actual count, every model's
prediction, gap, candidate flag and model-wide importance. Use `--port 8001` on
the server command if port 8000 is busy. Ctrl+C stops it.

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

The server only reads two committed files, so it trains nothing at startup:

- `web/predictions.csv`: `hex_id`, `toilet_count`, `fold`, then one held-out
  prediction column per model.
- `web/metrics.json`: per-model deviance, PR-AUC, top-100 hits, candidates and
  importance, with a `source` note.

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

The committed `data/reference/sydney_places.json` contains 937 Sydney suburb
representative points and selected landmarks. To rebuild it from the existing
raw ABS suburb and Greater Sydney boundary files, run `python scripts/build_places.py`.
Lookup is local. Unlisted landmarks and addresses need coordinates. Leaflet 1.9.4
and its license are in `web/vendor/leaflet/`. OpenStreetMap basemap tiles need
internet access. Lookup and the hexagon overlays run locally. No Node install,
frontend build, database or web framework is needed.

## Running the Model Comparison Webpage

From the repository root after cloning or pulling, use Python 3.14 (tested with
3.14.3) and the pinned dependencies, especially scikit-learn 1.9.1:

```sh
python3.14 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python scripts/serve_comparison.py
```

On Windows, activate with `.venv\Scripts\activate` instead. Open
**http://127.0.0.1:8000**. Select a place and radius, then click **Analyze**.
Internet access is needed for OpenStreetMap tiles. The rest runs locally.

The repository must include `web/` (with `predictions.csv`, `metrics.json` and the
vendored Leaflet), `data/reference/sydney_places.json` and `src/pigeon_ai/`. No
processed tables, raw data or training are needed to serve the page. The V1–V10
table at the top of the page is a static snapshot in `web/index.html` (V10 pending).

To rebuild the processed tables from the team's raw snapshot, install the native
osmium/GDAL tools described in [data/README.md](data/README.md), then:

```sh
python scripts/download_data.py "<share link to pigeon-ai-raw.zip itself>"
python scripts/run_pipeline.py
python scripts/build_experiments.py --versions V5 V9 V10
python scripts/build_accessibility.py
python scripts/build_comparison_page.py
python scripts/serve_comparison.py
```

Alternatively, unzip the team's archive directly into `data/raw/` as described in
[DATA.md](DATA.md). V9 and V10 are in the rebuild because the accessibility builder
checks their tables. Use the original Drive snapshot to keep the input values.
