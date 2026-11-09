#!/usr/bin/env python3
"""Rebuild the small offline Sydney location lookup from existing ABS boundaries."""
from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import geopandas as gpd
from pigeon_ai.paths import RAW, WEB

if __name__ == "__main__":
    city = gpd.read_file(RAW / "abs_boundaries/GCCSA_2026_AUST_GDA2020.shp")
    city = city[city.GCC_NAME26 == "Greater Sydney"].to_crs(4326).geometry.union_all()
    suburbs = gpd.read_file(RAW / "abs_suburbs/SAL_2026_AUST_GDA2020.shp").to_crs(4326)
    suburbs = suburbs[suburbs.STE_NAME26 == "New South Wales"].copy()
    points = suburbs.geometry.representative_point()
    places = {name: [round(point.y, 6), round(point.x, 6)]
              for name, point in zip(suburbs.SAL_NAME26, points)
              if point is not None and not point.is_empty and point.intersects(city)}
    places.update({"Sydney Opera House": [-33.8568, 151.2153],
                   "Town Hall": [-33.8732, 151.2069], "Central Station": [-33.8830, 151.2067],
                   "Circular Quay": [-33.8611, 151.2126], "Darling Harbour": [-33.8737, 151.2006],
                   "Sydney Olympic Park": [-33.8473, 151.0688]})
    path = WEB / "places.json"
    path.write_text(json.dumps({"source": "ABS 2026 Suburbs and Localities, representative points within Greater Sydney; six manually located landmarks", "places": dict(sorted(places.items()))}, indent=2) + "\n")
    print(f"Saved {len(places)} locations to {path}")
