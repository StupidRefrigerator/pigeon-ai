# Data

Raw data is too large for Git and lives in the team Google Drive as one zip, `pigeon-ai-raw.zip`. You only need it to rebuild the dataset. Modelling uses the committed `data/processed/sydney_hex_features.csv`.

## Getting the data

```sh
python scripts/download_data.py "<share link to pigeon-ai-raw.zip itself>"
```

Get the ZIP-file share link from the [team Drive folder](https://drive.google.com/drive/folders/1mbuAEllISFlfmRX8O7300f_iwsCJ04cM?usp=sharing).
The folder URL itself is not a downloadable ZIP. You can optionally set the
file link as `DRIVE_URL` in the script.

This downloads the zip, extracts it into `data/raw/`, and checks that the required files exist. Manual alternative: download the zip from Drive and unzip it into `data/raw/`.

## Updating the data

1. Zip the contents of `data/raw/`, not the folder itself: `cd data/raw && zip -r ../../pigeon-ai-raw.zip .`
2. Upload it to the Drive folder, replacing the old version. Set sharing to "Anyone with the link can view".
3. Paste the share link into `DRIVE_URL` in `scripts/download_data.py`, and update the table below.

## Files

| Path in `data/raw/`    | Dataset                                  | Source                     | Downloaded |
| ---------------------- | ---------------------------------------- | -------------------------- | ---------- |
| `national_toilets.csv` | National Public Toilet Map               | data.gov.au                | 2026-10-18 |
| `census_2021/`         | ABS 2021 Census GCP, SA1, NSW (uses G01) | ABS Census DataPacks       | 2026-10-18 |
| `abs_sa1_2021/`        | ABS 2021 SA1 boundaries (ASGS Ed. 3)     | ABS digital boundary files | 2026-10-18 |
| `abs_boundaries/`      | ABS 2026 GCCSA boundaries                | ABS digital boundary files | 2026-10-18 |
| `abs_suburbs/`         | ABS 2026 Suburbs and Localities (SAL)    | ABS digital boundary files | 2026-10-18 |
| `osm/nsw.osm.pbf`      | OpenStreetMap NSW extract                | Geofabrik                  | 2026-10-18 |

The OSM extract changes daily, so download it again from the source and the features will differ slightly. Use the Drive copy to reproduce the committed dataset exactly.

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
