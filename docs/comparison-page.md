# V1–V10 experiments and the local comparison page

The older comparison tools. The live app replaces the comparison page for V12.

## Compare dataset experiments V1–V10

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

## Local comparison page

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
[data pipeline](../data/README.md#running-the-pipeline), then
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
osmium/GDAL tools described in [data/README.md](../data/README.md), then:

```sh
python scripts/download_data.py "<share link to pigeon-ai-raw.zip itself>"
python scripts/run_pipeline.py
python scripts/build_experiments.py --versions V5 V9 V10
python scripts/build_accessibility.py
python scripts/build_comparison_page.py
python scripts/serve_comparison.py
```

Alternatively, unzip the team's archive directly into `data/raw/` as described in
[DATA.md](../DATA.md). V9 and V10 are in the rebuild because the accessibility builder
checks their tables. Use the original Drive snapshot to keep the input values.
