"""Hex sets (study, growth, future) as H3 res-9 polygons in EPSG:7856, built the way geography.py does."""
import geopandas as gpd
import h3
import pandas as pd
from shapely.geometry import Polygon

REPO = "/Users/summitsetia/Desktop/University/26T3/PIGEON-AI-DATASET"
OUT = "/Users/summitsetia/Desktop/University/26T3/pigeon-v2/data"
CRS = "EPSG:7856"


def hex_ids():
    study = pd.read_csv(f"{REPO}/data/processed/sydney_extended_features.csv", usecols=["hex_id", "toilet_count"])
    growth = pd.read_csv(f"{REPO}/data/processed/sydney_growth_features.csv", usecols=["hex_id"])
    aero = pd.read_csv(f"{REPO}/experiments/future/aero_features.csv", usecols=["hex_id"]).hex_id.unique()
    lepp = pd.read_csv(f"{REPO}/experiments/future/leppington_features.csv", usecols=["hex_id"]).hex_id.unique()
    future = pd.DataFrame({"hex_id": list(aero) + list(lepp),
                           "area": ["aerotropolis"] * len(aero) + ["leppington"] * len(lepp)})
    return study, growth.hex_id.drop_duplicates().tolist(), future


def grid(ids):
    geoms = [Polygon([(lng, lat) for lat, lng in h3.cell_to_boundary(c)]) for c in ids]
    return gpd.GeoDataFrame({"hex_id": list(ids)}, geometry=geoms, crs=4326).to_crs(CRS)
