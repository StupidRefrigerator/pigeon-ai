"""Download AWS Terrain Tiles (Terrarium PNG, zoom 12, about 32 m pixels) covering the study bbox.

Usage: python -I fetch_dem.py OUT_DIR
Source: https://registry.opendata.aws/terrain-tiles/ (SRTM-based in Australia; no key needed).
"""
import math
import sys
from pathlib import Path

import requests

BBOX = (150.4939, -34.1406, 151.3624, -33.5211)
ZOOM = 12
URL = "https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png"


def tile_xy(lon, lat, z=ZOOM):
    n = 2 ** z
    x = (lon + 180) / 360 * n
    y = (1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n
    return int(x), int(y)


def main(out_dir):
    out_dir.mkdir(parents=True, exist_ok=True)
    west, south, east, north = BBOX
    x0, y0 = tile_xy(west, north)
    x1, y1 = tile_xy(east, south)
    for x in range(x0, x1 + 1):
        for y in range(y0, y1 + 1):
            path = out_dir / f"{ZOOM}_{x}_{y}.png"
            if not path.exists():
                r = requests.get(URL.format(z=ZOOM, x=x, y=y), timeout=60)
                r.raise_for_status()
                path.write_bytes(r.content)
    print(f"tiles x {x0}-{x1}, y {y0}-{y1}")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
