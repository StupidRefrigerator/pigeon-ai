# Data

Raw data is too large for Git and lives in the team Google Drive as two zips:

- `pigeon-ai-raw.zip`: everything except the V12 OpenStreetMap layers.
- `pigeon-ai-raw-v12-osm.zip`: the Overpass downloads behind the V12 features (sports grounds, playgrounds, beaches, OSM toilets). About 2 MB.

> **TODO(drive):** `pigeon-ai-raw-v12-osm.zip` is not on the Drive yet. Until someone uploads it and sets `V12_OSM_DRIVE_URL` in `scripts/download_data.py`, ask Summit for the zip.

You only need them to rebuild the dataset. Modelling uses the committed CSVs in `data/processed/`.

## Getting the data

```sh
python scripts/download_data.py
```

This downloads both zips using the links in the script. To pass links yourself, run `python scripts/download_data.py "<pigeon-ai-raw.zip link>" --v12-osm "<pigeon-ai-raw-v12-osm.zip link>"`. To get only the V12 zip, add `--v12-osm-only`.

Get the ZIP-file share link from the [team Drive folder](https://drive.google.com/drive/folders/1mbuAEllISFlfmRX8O7300f_iwsCJ04cM?usp=sharing).
The folder URL itself is not a downloadable ZIP. Set the
file links as `DRIVE_URL` and `V12_OSM_DRIVE_URL` in the script.

This downloads each zip, extracts it into `data/raw/`, and checks that the required files exist. Manual alternative: download the zips from Drive and unzip them into `data/raw/`.

## Updating the data

1. Zip the contents of `data/raw/` without the V12 folder, not the folder itself: `cd data/raw && zip -r ../../pigeon-ai-raw.zip . -x 'osm_overpass_v12/*'`
2. Zip the V12 folder on its own: `cd data/raw && zip -r ../../pigeon-ai-raw-v12-osm.zip osm_overpass_v12`
3. Upload the changed zip to the Drive folder, replacing the old version. Set sharing to "Anyone with the link can view".
4. Paste the share link into `DRIVE_URL` or `V12_OSM_DRIVE_URL` in `scripts/download_data.py`, and update the table below.

To refresh the V12 layers from today's OpenStreetMap, run `python scripts/fetch_overpass.py --out-dir data/raw/osm_overpass_v12_new`, check it, then replace `data/raw/osm_overpass_v12/` with it. The public Overpass servers are often overloaded: the first download took about 3 hours, with many HTTP 502/504 errors. The script retries, rotates between mirrors and splits failing tiles. Rerun it to resume. The new download gives different feature values, because OSM changes.

## Files

| Path in `data/raw/`    | Dataset                                  | Source                     | Downloaded |
| ---------------------- | ---------------------------------------- | -------------------------- | ---------- |
| `national_toilets.csv` | National Public Toilet Map               | data.gov.au                | 2026-10-18 |
| `census_2021/`         | ABS 2021 Census GCP, SA1, NSW (uses G01) | ABS Census DataPacks       | 2026-10-18 |
| `abs_sa1_2021/`        | ABS 2021 SA1 boundaries (ASGS Ed. 3)     | ABS digital boundary files | 2026-10-18 |
| `abs_boundaries/`      | ABS 2026 GCCSA boundaries                | ABS digital boundary files | 2026-10-18 |
| `abs_suburbs/`         | ABS 2026 Suburbs and Localities (SAL)    | ABS digital boundary files | 2026-10-18 |
| `osm/nsw.osm.pbf`      | OpenStreetMap NSW extract                | Geofabrik                  | 2026-10-18 |
| `osm_overpass_v12/`    | OpenStreetMap sports, playgrounds, beaches, surf clubs and toilets, in 39 tiles plus one surf-club query (in `pigeon-ai-raw-v12-osm.zip`) | Overpass API (`scripts/fetch_overpass.py`) | 2026-11-09 |

### Water fountains (`data/raw/bubblers/`)

`python scripts/fetch_bubblers.py` downloads the council layers and the OpenStreetMap features (`--skip-osm` for the council layers only). Then `python -I scripts/build_bubblers.py` writes `data/processed/bubbler_labels.csv` and `bubbler_points.csv`. Each council layer is queried with `query?where=1=1&outFields=*&outSR=4326&f=geojson`.

| Path in `data/raw/bubblers/` | Dataset | Source | Downloaded |
| --- | --- | --- | --- |
| `official/cos_fountains.geojson` | City of Sydney drinking fountains (273) | [ArcGIS layer](https://services1.arcgis.com/cNVyNtjGVZybOQWZ/arcgis/rest/services/Drinking_fountains/FeatureServer/0) | 2026-11-16 |
| `official/parramatta_fountains.geojson` | City of Parramatta drinking fountains (132) | [ArcGIS layer](https://services6.arcgis.com/NrOjMi9LSYL3MUze/arcgis/rest/services/Drinking_Fountains/FeatureServer/0) | 2026-11-16 |
| `official/fairfield_bubblers.geojson` | Fairfield bubbler inspections (12, partial) | [ArcGIS layer](https://services9.arcgis.com/ptMeJSvCigyke2Tt/arcgis/rest/services/Bubbler_Inspection_Data_View_Layer/FeatureServer/0) | 2026-11-16 |
| `official/northern_beaches_bubblers.geojson` | Northern Beaches bubblers (239) | [ArcGIS layer](https://maps.northernbeaches.nsw.gov.au/arcgis/rest/services/Bubblers/MapServer/0) | 2026-11-16 |
| `official/penrith_bubblers.geojson` | Penrith bubbler locations (14, partial) | [ArcGIS layer](https://services-ap1.arcgis.com/2ifYh4l3ar2sldJb/arcgis/rest/services/Bubbler_Locations/FeatureServer/0) | 2026-11-16 |
| `osm/drinking_water.json` | OpenStreetMap drinking water, taps and fountains | Overpass API | 2026-11-16 |
| `lga/lga.geojson` | NSW local government area boundaries (`lganame`) | Downloaded by hand; source not recorded | 2026-11-16 |

Other councils publish no fountain layer we found, so their fountains come from OpenStreetMap only. Western councils record few: Penrith, Blacktown, Liverpool, Campbelltown, Fairfield and Hawkesbury have 163 fountains in the label where the model predicts 479.

OSM changes daily, so a new download gives slightly different features. Use the Drive copies to reproduce the committed dataset exactly. In `osm_overpass_v12/`, `fetch_log.json` and the `.meta.json` files record each tile's server and OSM snapshot time. Some mirror tiles are snapshots from 2026-05-31 to 2026-07-28, not 2026-11-09.

The archived baseline (`archive/before_simplification/`) is also in the Drive folder. It's only needed for `--check-baseline`.

## Experiment outputs

Three large per-hexagon outputs from `experiments/` are not in Git (12.7 MB). They are in `pigeon-ai-experiment-outputs.zip` on the team Drive:

| File | Made by | Read by |
| --- | --- | --- |
| `experiments/v2/combos/out/study_oof_predictions.csv` | `experiments/v2/combos/study_cv.py` (about 3 min) | `experiments/v2/combos/evaluate_study.py` |
| `experiments/future/aero_predictions.csv` | `experiments/future/run_aero.py` | Nothing; kept for reference |
| `experiments/future/aero_features.csv` | `experiments/future/run_aero.py` | `experiments/v2/data/scripts/hexsets.py` |

Unzip it at the repo root (`unzip pigeon-ai-experiment-outputs.zip`), or rerun the script that makes the file. You don't need them to train the model or run the app; the summary CSVs that the findings page and the app read are committed.

> **TODO(drive):** `pigeon-ai-experiment-outputs.zip` is not on the Drive yet. Until it is, ask Summit for it.

## Bike-lane experiment downloads

`experiments/bike/` needs about 1.1 GB of downloads that are not in Git. Keep them in `experiments/bike/downloads/` (ignored) or any folder outside the repo, and pass that folder to `experiments/bike/run_all.sh`. Every file is public and the scripts re-download all of them except the PBF and the TfNSW zip:

| Path in the downloads folder | Dataset | Source | Downloaded |
| --- | --- | --- | --- |
| `overpass/bike_tile_*.json` (12 tiles, 28 MB) | OSM cycleways, cycle lanes and `bicycle=designated` ways | Overpass API (`experiments/bike/scripts/fetch_bike_osm.py`) | 2026-11-14; all tiles OSM snapshot 2026-11-14 (`fetch_log.json`) |
| `pbf/australia-261113.osm.pbf` (930 MB) | Geofabrik Australia extract, for roads, junctions, schools, universities, stations and planned cycleways | https://download.geofabrik.de/australia-oceania/australia-261113.osm.pbf (MD5 `77be6f23bf858d170c89954f515b8fd2`) | 2026-11-14 |
| `tfnsw/existing_bicycle_network.zip` (13 MB), unzipped to `tfnsw/shp/` | TfNSW Existing Bicycle Network (CC BY), for comparison only | [TfNSW Open Data Hub, Infrastructure Cycleway Data](https://opendata.transport.nsw.gov.au/dataset/infrastructure-cycleway-data) | 2026-11-14 (dataset updated 2026-10-31) |
| `dem/12_*_*.png` (99 tiles, 3.5 MB) | AWS Terrain Tiles, Terrarium encoding, zoom 12 | `experiments/bike/scripts/fetch_dem.py` | 2026-11-14 |

The per-hex outputs built from them (`experiments/bike/data/*.csv`) are committed, so the experiments run without the downloads: start from `experiments/bike/scripts/run_experiments.py`. The scripts also need `pip install osmium`.
