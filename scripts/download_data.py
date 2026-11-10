#!/usr/bin/env python3
from pathlib import Path
import argparse
import sys
import tempfile
import zipfile

import gdown

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pigeon_ai.paths import RAW

# Optional share links to the ZIP files themselves, not their Drive folder; see DATA.md.
DRIVE_URL = ""
V12_OSM_DRIVE_URL = ""

REQUIRED = [
    "national_toilets.csv",
    "census_2021/2021 Census GCP Statistical Area 1 for NSW/2021Census_G01_NSW_SA1.csv",
    "abs_sa1_2021/SA1_2021_AUST_GDA2020.shp",
    "abs_boundaries/GCCSA_2026_AUST_GDA2020.shp",
    "abs_suburbs/SAL_2026_AUST_GDA2020.shp",
    "osm/nsw.osm.pbf",
]
V12_OSM_REQUIRED = [
    "osm_overpass_v12/fetch_log.json",
    "osm_overpass_v12/overpass_tile_0_0.json",
    "osm_overpass_v12/overpass_slsc_names.json",
]


def download(url, name, required):
    RAW.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as temporary:
        archive = Path(temporary) / name
        gdown.download(url, str(archive))
        with zipfile.ZipFile(archive) as zipped:
            zipped.extractall(RAW)
    missing = [path for path in required if not (RAW / path).exists()]
    if missing:
        sys.exit(f"Missing from data/raw/ after extracting {name}:\n  " + "\n  ".join(missing))


def main(url, v12_osm_url, v12_osm_only):
    if not v12_osm_only:
        if not url:
            sys.exit("Pass the share link to pigeon-ai-raw.zip (not the Drive folder); see DATA.md.")
        download(url, "pigeon-ai-raw.zip", REQUIRED)
    if v12_osm_url:
        download(v12_osm_url, "pigeon-ai-raw-v12-osm.zip", V12_OSM_REQUIRED)
    elif v12_osm_only:
        sys.exit("Pass --v12-osm with the share link to pigeon-ai-raw-v12-osm.zip; see DATA.md.")
    else:
        print("Skipped pigeon-ai-raw-v12-osm.zip (no --v12-osm link); only needed to rebuild the V12 features.")
    print(f"Raw data ready in {RAW}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("url", nargs="?", default=DRIVE_URL, help="Drive share link to pigeon-ai-raw.zip")
    parser.add_argument("--v12-osm", default=V12_OSM_DRIVE_URL,
                        help="Drive share link to pigeon-ai-raw-v12-osm.zip (Overpass tiles for V12)")
    parser.add_argument("--v12-osm-only", action="store_true",
                        help="download only pigeon-ai-raw-v12-osm.zip")
    args = parser.parse_args()
    main(args.url, args.v12_osm, args.v12_osm_only)
