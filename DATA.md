# Data

Raw data is too large for Git and lives in the team Google Drive as one zip, `pigeon-ai-raw.zip`. You only need it to rebuild the dataset. Modelling uses the committed `data/processed/sydney_hex_features.csv`.

## Getting the data

```sh
python scripts/download_data.py            # uses DRIVE_URL in the script
python scripts/download_data.py "<link>"   # or pass the share link
```

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
