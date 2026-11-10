"""Cached downloads: ArcGIS REST envelope queries and Overpass. Writes only to downloads/."""
import hashlib
import json
import sys
import time
from pathlib import Path

import geopandas as gpd
import requests

DOWNLOADS = Path("/tmp/pigeon-eval/future/downloads")
UA = {"User-Agent": "pigeon-ai-uni-project"}
ZONING = ("https://mapprod3.environment.nsw.gov.au/arcgis/rest/services/ePlanning/"
          "Planning_Portal_Principal_Planning/MapServer/19")
ABS_SA2 = "https://geo.abs.gov.au/arcgis/rest/services/ASGS2021/SA2/MapServer/0"
ABS_SAL = "https://geo.abs.gov.au/arcgis/rest/services/ASGS2021/SAL/MapServer/0"
OVERPASS = "https://overpass-api.de/api/interpreter"


def _cache(name):
    DOWNLOADS.mkdir(parents=True, exist_ok=True)
    return DOWNLOADS / name


def arcgis_envelope(layer_url, bbox, out_fields="*", where="1=1", tag="", order_by="OBJECTID"):
    """bbox = (minx, miny, maxx, maxy) in lon/lat. Returns GeoDataFrame in EPSG:4326."""
    key = hashlib.sha1(f"{layer_url}|{bbox}|{out_fields}|{where}".encode()).hexdigest()[:12]
    path = _cache(f"arcgis_{tag}_{key}.geojson")
    if not path.exists():
        features, offset = [], 0
        while True:
            params = dict(
                geometry=",".join(map(str, bbox)), geometryType="esriGeometryEnvelope", inSR=4326,
                spatialRel="esriSpatialRelIntersects", outFields=out_fields, where=where,
                returnGeometry="true", outSR=4326, f="geojson", resultOffset=offset,
                resultRecordCount=1000, orderByFields=order_by,
            )
            for attempt in range(4):
                r = requests.get(f"{layer_url}/query", params=params, headers=UA, timeout=180)
                if r.ok:
                    break
                time.sleep(5 * (attempt + 1))
            r.raise_for_status()
            page = r.json()
            if "error" in page:
                raise RuntimeError(page["error"])
            features += page["features"]
            if len(page["features"]) < 1000 and not page.get("exceededTransferLimit"):
                break
            offset += len(page["features"])
        path.write_text(json.dumps({"type": "FeatureCollection", "features": features}))
    gdf = gpd.read_file(path)
    return gdf.set_crs(4326, allow_override=True)


def overpass(query, tag):
    key = hashlib.sha1(query.encode()).hexdigest()[:12]
    path = _cache(f"overpass_{tag}_{key}.json")
    if not path.exists():
        for attempt in range(4):
            r = requests.post(OVERPASS, data={"data": query}, headers=UA, timeout=300)
            if r.ok:
                break
            time.sleep(20 * (attempt + 1))
        r.raise_for_status()
        path.write_bytes(r.content)
    return json.loads(path.read_text())


def download(url, name):
    path = _cache(name)
    if not path.exists():
        r = requests.get(url, headers=UA, timeout=300)
        r.raise_for_status()
        path.write_bytes(r.content)
    return path


if __name__ == "__main__":
    print(arcgis_envelope(ZONING, tuple(map(float, sys.argv[1:5])), tag="zoning").head())
