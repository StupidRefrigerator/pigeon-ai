#!/usr/bin/env python3
from pathlib import Path
import argparse
import sys
import tempfile
import zipfile

import gdown

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pigeon_ai.paths import RAW

# Share link to pigeon-ai-raw.zip in the team Google Drive; see DATA.md.
DRIVE_URL = "https://drive.google.com/drive/folders/1mbuAEllISFlfmRX8O7300f_iwsCJ04cM?usp=sharing"

REQUIRED = [
    "national_toilets.csv",
    "census_2021/2021 Census GCP Statistical Area 1 for NSW/2021Census_G01_NSW_SA1.csv",
    "abs_sa1_2021/SA1_2021_AUST_GDA2020.shp",
    "abs_boundaries/GCCSA_2026_AUST_GDA2020.shp",
    "abs_suburbs/SAL_2026_AUST_GDA2020.shp",
    "osm/nsw.osm.pbf",
]


def main(url):
    if not url:
        sys.exit("No Drive link: set DRIVE_URL or pass the link as an argument.")
    RAW.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as temporary:
        archive = Path(temporary) / "pigeon-ai-raw.zip"
        gdown.download(url, str(archive))
        with zipfile.ZipFile(archive) as zipped:
            zipped.extractall(RAW)

    missing = [name for name in REQUIRED if not (RAW / name).exists()]
    if missing:
        sys.exit("Missing from data/raw/:\n  " + "\n  ".join(missing))
    print(f"Raw data ready in {RAW}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("url", nargs="?", default=DRIVE_URL, help="Drive share link")
    main(parser.parse_args().url)
