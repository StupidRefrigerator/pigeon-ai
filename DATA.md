# Data

Raw data is too large for Git and lives in the team Google Drive as two zips:

- `pigeon-ai-raw.zip`: everything except the V12 OpenStreetMap layers.
- `pigeon-ai-raw-v12-osm.zip`: the Overpass downloads behind the V12 features (sports grounds, playgrounds, beaches, OSM toilets). About 2 MB.

You only need them to rebuild the dataset. Modelling uses the committed CSVs in `data/processed/`.

## Getting the data

```sh
python scripts/download_data.py "<share link to pigeon-ai-raw.zip>" --v12-osm "<share link to pigeon-ai-raw-v12-osm.zip>"
```

To get only the V12 zip, run `python scripts/download_data.py --v12-osm-only --v12-osm "<share link>"`.

Get the ZIP-file share link from the [team Drive folder](https://drive.google.com/drive/folders/1mbuAEllISFlfmRX8O7300f_iwsCJ04cM?usp=sharing).
The folder URL itself is not a downloadable ZIP. You can optionally set the
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

OSM changes daily, so a new download gives slightly different features. Use the Drive copies to reproduce the committed dataset exactly. In `osm_overpass_v12/`, `fetch_log.json` and the `.meta.json` files record each tile's server and OSM snapshot time. Some mirror tiles are snapshots from 2026-05-31 to 2026-07-28, not 2026-11-09.

The archived baseline (`archive/before_simplification/`) is also in the Drive folder. It's only needed for `--check-baseline`.
