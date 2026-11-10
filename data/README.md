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
- `y`: `toilet_count`, the number of public toilets in each hexagon. Use `y > 0` if you need a present/absent label.
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

## V12 OSM features: sports grounds, playgrounds, beaches and OSM toilets

The default model (V12) adds 17 OpenStreetMap columns to the 28 `latest` columns. The build also counts OSM public toilets, which the recommended list uses after the model.

### Files

| File in `data/processed/` | Rows | Contents |
|---|---:|---|
| `sydney_recreation_features.csv` | 16,228 | The 17 V12 columns and 3 `osm_toilets_*` columns for the study hexagons (same hexagons as `sydney_extended_features.csv`). |
| `sydney_growth_recreation_features.csv` | 17,336 | The same columns for the growth set (same hexagons as `sydney_growth_features.csv`). |
| `osm_toilets.csv` | 2,462 | One row per OSM `amenity=toilets`: `lat`, `lng`, `access`, `fee`, `name`, `operator`, `osm_type`, `osm_id`, `hex_id`, `is_public`, `is_public_tagged`, `is_private`. |

Every hexagon has a value in every column. The model joins `sydney_recreation_features.csv` to `sydney_extended_features.csv` by `hex_id`.

### Rebuilding

```sh
python -I scripts/build_recreation.py
```

It reads the Overpass tiles in `data/raw/osm_overpass_v12/` (see [DATA.md](../DATA.md)) and writes the three files above in about 40 seconds. Run it with `-I`, because it reads downloaded files. With the Drive copy of the tiles, the output is byte-identical to the committed files. `scripts/fetch_overpass.py` downloads new tiles from today's OSM. These give different values.

### Source and query dates

- OpenStreetMap through the Overpass API, queried 2026-11-09 from 12:13 to 15:07 UTC.
- Bbox: 150.4939, -34.1406, 151.3624, -33.5211 (W, S, E, N). This is the bounds of all study, growth and future hexagons plus 1.5 km.
- The bbox was split into a 4 × 3 grid. Tiles that failed were split 2 × 2, and some again, which gives 39 tiles. Elements on tile edges are counted once, by OSM type and id.
- Of the 40 responses (39 tiles and the surf-club query), 25 came from overpass-api.de, 8 from overpass.kumi.systems and 7 from overpass.private.coffee.
- **Freshness varies by tile.** overpass-api.de tiles are from 2026-11-09. Mirror tiles 0_2, 1_0, 2_0, 2_1_10, 2_2_01, 2_2_11, 3_0_00, 3_0_10, 3_0_11, 3_1_10_01, 3_1_10_10, 3_2_01_01, 3_2_01_10 and 3_2_11 are snapshots from 2026-05-31 to 2026-07-28. OSM edits made after those dates are missing there.
- Query per tile: `leisure` = pitch, sports_centre, stadium, track, golf_course, playground or beach_resort; `natural=beach`; lifeguard and surf-club tags; and `amenity=toilets`. One extra query found surf clubs by name over the coast east of 151.10°.

### Columns

| Column | Definition |
|---|---|
| `sports_inside`, `sports_250m`, `sports_500m`, `sports_1000m` | Count of `leisure` = pitch, sports_centre, stadium or track (12,871 features). Golf courses are left out. |
| `sports_area_inside_m2`, `sports_area_500m_m2` | Area (m²) of the union of sports polygons in the hexagon or a 500 m circle. The union stops a pitch inside a stadium from counting twice. |
| `distance_nearest_sports_m` | Metres from the hexagon centre to the nearest sports feature. 0 if the centre is inside one. |
| `playground_inside`, `playground_250m`, `playground_500m`, `playground_1000m` | Count of `leisure=playground` (3,575). |
| `distance_nearest_playground_m` | Metres to the nearest playground. |
| `beach_inside`, `beach_250m`, `beach_500m`, `beach_1000m` | Count of `natural=beach` (322) plus surf lifesaving clubs and lifeguard posts (63). A surf beach usually scores 2 or 3. Harbour, bay and river beaches count too. |
| `distance_nearest_beach_m` | Metres to the nearest beach feature. |
| `osm_toilets_public` | OSM toilets in the hexagon whose `access` is yes, permissive, public or missing. **Not a model input.** |
| `osm_toilets_public_tagged` | The same, but `access` is set to yes, permissive or public. Not a model input. |
| `osm_toilets_private` | OSM toilets whose `access` is customers, private or no. Not a model input. |

Counts, areas and distances follow the conventions of the park features: EPSG:7856, representative points taken before projection, `within` for inside counts, 16-segment circles for counts and 8-segment circles for areas. Nodes count as points. Ways and multipolygon relations are rebuilt as polygons, or as lines for unclosed ways such as running tracks.

### Caveats

- **Missing OSM data is a blind spot.** OSM has no sports ground mapped at Ken Birdsey Park (Schofields) or Anthony Skarratt Reserve (Box Hill), two council-planned sites. Both hexagons have zero sports and zero playgrounds, so the model cannot flag them.
- The `osm_toilets_*` columns nearly copy the label (Spearman 0.57 with `toilet_count`). As inputs, the model would learn to copy the label. They are used only after the model.
- In the study hexagons, OSM lists 1,862 public toilets and the official map 2,570. 272 hexagons have an OSM public toilet but an official count of 0.
- A playground node inside a playground polygon counts twice. Duplicate mapping is not merged.

## Important methodology notes

- The approved study area contains **10,503 SA1s**. Historical selection used **50 people/km²**, not 500. Approved preliminary membership is frozen in `data/reference/`; growth exclusions are recalculated using suburb and SA1 representative points.
- H3 cells remain whole and can cross the study boundary. They contain **2,570 toilet records across 1,911 occupied cells**. Existing toilets describe historical placement, not a direct measure of infrastructure need.
- Metric calculations use **EPSG:7856**. Population contributions are `SA1 population × overlap area / complete original SA1 area`. Residents are assumed uniformly distributed within each SA1. Context may extend outside the prediction area; overlapping buffers must not be summed as unique residents.
- OSM excludes `shop=vacant`, counts cafes/restaurants as food, and preserves distinct objects even when names match. Polygon destinations become representative points before projection; inside counts use `within`, buffer counts use `intersects`.
- Park areas use unioned original polygons. Their historical Shapely buffers use 8 segments per quadrant; population/count buffers use GeoPandas's 16. These definitions are deliberately preserved.
- Nearest-park queries use **all available park polygons**, retaining the corrected distances. OSM extraction uses bbox `150.45,-34.25,151.40,-33.35`, `complete_ways`, and shop/food/bus/station/park tag filters with referenced objects. Mapping and relation coverage can be incomplete; distances are not walking distances or globally complete park access estimates.

## Model

Training, the model architecture, the evals and the candidate review file are described in the [project README](../README.md#model).

### Local comparison page

The [local comparison page](../README.md#local-comparison-page) shows V1, V5, V6 and
Latest from held-out predictions. `scripts/build_comparison_page.py` reads the
baseline and extended CSVs above and writes `web/predictions.csv` and
`web/metrics.json`. Both are committed. `scripts/serve_comparison.py` serves them
and needs no raw files or processed tables. See
[Running the Model Comparison Webpage](../README.md#running-the-model-comparison-webpage)
for teammate setup.
