import requests
import geopandas as gpd

NATIONAL_URL = (
    "https://portal.data.nsw.gov.au/arcgis/rest/services/"
    "Hosted/National_Public_Toilet_Map/FeatureServer/0/query"
)

def download_national_toilets():
    records = []
    offset = 0
    limit = 2000

    while True:
        params = {
            "where": "1=1",
            "outFields": "*",
            "returnGeometry": "true",
            "outSR": 4326,
            "f": "geojson",
            "resultOffset": offset,
            "resultRecordCount": limit
        }

        response = requests.get(NATIONAL_URL, params=params)
        response.raise_for_status()
        data = response.json()

        features = data.get("features", [])
        records.extend(features)

        print(f"Downloaded {len(records)} records")

        if len(features) < limit:
            break

        offset += limit

    return gpd.GeoDataFrame.from_features(
        records, crs="EPSG:4326"
    )


national = download_national_toilets()
national.to_file("national_toilets.geojson", driver="GeoJSON")