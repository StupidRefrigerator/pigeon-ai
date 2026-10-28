# PIGEON-AI dataset

How `data/processed/sydney_hex_features.csv` is built. Paths are relative to the project root.

## Project structure

```text
data/raw/            Original datasets; never edited by the pipeline
data/reference/      Approved SA1/H3 IDs and growth-suburb names
data/interim/        Rebuilt OSM extracts and selected study-area geometry
data/processed/      Final feature table and geospatial exports
src/pigeon_ai/       Geography, population, OSM and validation functions
scripts/             Pipeline execution, validation, notebook checks and data download
notebooks/           Five short notebooks with checks and visualizations
archive/             Historical code, documentation, datasets and baselines
```

## Data pipeline

1. Read Census G01 population and join it to the original 2021 SA1 boundaries.
2. Select the approved preliminary SA1s and exclude the named growth suburbs.
3. Generate complete H3 resolution-9 cells and assign national toilet records.
4. Estimate population inside each cell using area-weighted SA1 overlaps.
5. Extract Sydney OSM data from the NSW PBF and convert selected objects to a GeoPackage.
6. Calculate shop, food, bus-stop, station and park features.
7. Estimate population within 250 m and 500 m, validate the results and save exports.

`scripts/run_pipeline.py` shows these steps in order. Processing functions are in `src/pigeon_ai/`. Only the study geometry and OSM intermediates are saved for notebook inspection; other intermediate tables remain in memory.

## Data sources

- National Public Toilet Map: `data/raw/national_toilets.csv`.
- ABS 2021 Census G01: the NSW SA1 data pack under `data/raw/census_2021/`.
- ABS 2021 SA1 boundaries: `data/raw/abs_sa1_2021/`.
- ABS 2026 Greater Sydney and suburb boundaries: `data/raw/abs_boundaries/` and `data/raw/abs_suburbs/`.
- Geofabrik NSW OSM extract: `data/raw/osm/nsw.osm.pbf`, snapshot timestamp `2026-10-18T20:25:06Z`.

Raw datasets and the archive are not stored in Git; see `DATA.md` for downloading them from the team Google Drive. Optional baseline comparisons use the corrected dataset preserved in `archive/before_simplification/data/processed/`.

## Setup

Tested with Python 3.14.3, osmium 1.19.1 and GDAL CLI 3.13.3. Install the native tools first; on macOS:

```sh
brew install osmium-tool gdal
```

From the project root:

```sh
python3.14 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Scripts and notebooks import the checked-out `pigeon_ai` package directly; no editable package installation is needed.

## Running the pipeline

```sh
python scripts/download_data.py
python scripts/run_pipeline.py
python scripts/validate_outputs.py
python scripts/check_notebooks.py
```

The pipeline rebuilds the OSM extracts each time and takes a few minutes. Validation checks population, park bounds, nested buffers, schemas and export consistency. Row, toilet and occupied-hexagon counts are printed, along with any difference from `data/reference/approved_hex_ids.txt`, but they don't fail validation, so features and study areas can change.

Pass `--check-baseline` to `run_pipeline.py` or `validate_outputs.py` to also compare every final column against the preserved baseline by `hex_id`. Use it to confirm a refactor didn't change results. Floating-point tolerance is `1e-6` absolute and `1e-10` relative. Run Python normally, without `-O`, so assertions remain enabled.

Use `jupyter lab` to explore the five notebooks after generating the outputs. Each runs independently from the project root or `notebooks/`; notebook checks use fresh kernels and leave source outputs empty.

## Final output

`data/processed/sydney_hex_features.csv` contains **16,228 rows**: `hex_id`, the existing target/placement proxy `toilet_count`, and these **20 predictors**:

- `population_est`, `population_density`: estimated residents per cell and residents/km².
- `shop_inside`, `shop_250m`, `shop_500m`: shop object counts inside the cell and centre buffers.
- `food_inside`, `food_250m`, `food_500m`: cafe/restaurant object counts.
- `bus_stop_inside`, `bus_stop_250m`, `bus_stop_500m`: bus-stop object counts.
- `train_station_inside`, `train_station_250m`, `train_station_500m`: station object counts.
- `park_area_inside_m2`, `park_area_250m_m2`, `park_area_500m_m2`: unioned park footprint areas in m².
- `distance_nearest_park_m`: straight-line centroid distance to the nearest available park polygon.
- `population_250m`, `population_500m`: estimated residents in centre buffers.

Equivalent `.gpkg` and `.geojson` files include geometry. The GeoPackage uses EPSG:7856, layer `hex_features`; GeoJSON uses EPSG:4326. Use `FEATURES` in `pigeon_ai.validation` to select predictors; keep the identifier, target and geometry separate. No model training is included.

## Dataset Experiments

PIGEON-AI contains 10 dataset experiments to compare how different features and geographic coverage affect predictions of existing public toilet locations.

### Experiments

| Version | Description                                          | Features | Hexagons |
| ------- | ---------------------------------------------------- | -------: | -------: |
| V1      | Baseline: population, amenities, transport and parks |       20 |   16,228 |
| V2      | Population only                                      |        4 |   16,228 |
| V3      | Amenities, transport and parks only                  |       16 |   16,228 |
| V4      | Local features (within hexagon and 250 m)            |       13 |   16,228 |
| V5      | Baseline + 1 km surrounding features                 |       26 |   16,228 |
| V6      | Baseline + pedestrian accessibility                  |       23 |   16,228 |
| V7      | Baseline + demographics and socioeconomic data       |       26 |   16,228 |
| V8      | Baseline + future population projections             |       24 |   16,228 |
| V9      | Baseline with growth suburbs included                |       20 |   17,336 |
| V10     | Baseline across all Greater Sydney                   |       20 |   97,733 |

### Usage

```python
from pigeon_ai.experiments import load_experiment

X, y = load_experiment("V1")
```

- `X`: Feature DataFrame indexed by `hex_id`.
- `y`: Binary target (`1` = public toilet present, `0` = absent).
- Experiment definitions are in `src/pigeon_ai/experiments.py`.

### Data Files

All datasets are stored in `data/processed/`.

| File                           | Experiments |
| ------------------------------ | ----------- |
| `sydney_hex_features.csv`      | V1–V4       |
| `sydney_extended_features.csv` | V5–V8       |
| `sydney_growth_features.csv`   | V9          |
| `sydney_all_features.csv`      | V10         |

### Additional Features

- **V5:** Population, amenities, transport and park features within 1 km.
- **V6:** Walkable network length, pedestrian junctions and distance to the nearest footpath.
- **V7:** Four age groups (0–17, 18–25, 26–64, 65+), household estimates and SEIFA IRSD scores.
- **V8:** Projected population for 2031 and 2041, plus population growth estimates using NSW 2024 projections.

### Rebuilding Datasets

Run the relevant scripts in order:

```bash
python scripts/build_experiments.py
python scripts/build_accessibility.py
python scripts/build_demographics.py
python scripts/build_projections.py
```

### Important Notes

- V7 contains missing demographic values (`NaN`), which must be handled during model training.
- V8 is a future-planning scenario, not a valid historical prediction benchmark. It assumes future population growth follows existing population distributions.
- Demographic and population projections are geographically estimated, not exact hexagon-level observations.
- OSM pedestrian features reflect mapped infrastructure, not actual walking routes or wheelchair accessibility.
- Existing toilet locations are used only as target labels, not predictors.

## Important methodology notes

- The approved study area contains **10,503 SA1s**. Historical selection used **50 people/km²**, not 500. Approved preliminary membership is frozen in `data/reference/`; growth exclusions are recalculated using suburb and SA1 representative points.
- H3 cells remain whole and can cross the study boundary. They contain **2,570 toilet records across 1,911 occupied cells**. Existing toilets describe historical placement, not a direct measure of infrastructure need.
- Metric calculations use **EPSG:7856**. Population contributions are `SA1 population × overlap area / complete original SA1 area`. Residents are assumed uniformly distributed within each SA1. Context may extend outside the prediction area; overlapping buffers must not be summed as unique residents.
- OSM excludes `shop=vacant`, counts cafes/restaurants as food, and preserves distinct objects even when names match. Polygon destinations become representative points before projection; inside counts use `within`, buffer counts use `intersects`.
- Park areas use unioned original polygons. Their historical Shapely buffers use 8 segments per quadrant; population/count buffers use GeoPandas's 16. These definitions are deliberately preserved.
- Nearest-park queries use **all available park polygons**, retaining the corrected distances. OSM extraction uses bbox `150.45,-34.25,151.40,-33.35`, `complete_ways`, and shop/food/bus/station/park tag filters with referenced objects. Mapping and relation coverage can be incomplete; distances are not walking distances or globally complete park access estimates.
