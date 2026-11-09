from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data/raw"
REFERENCE = ROOT / "data/reference"
WEB = ROOT / "web"
INTERIM = ROOT / "data/interim"
PROCESSED = ROOT / "data/processed"
BASELINE = ROOT / "archive/before_simplification/data/processed"
CRS = "EPSG:7856"
