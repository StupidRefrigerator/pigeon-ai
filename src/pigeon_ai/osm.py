import re
import subprocess

import geopandas as gpd
import pandas as pd
from shapely import area, buffer, intersection

from .paths import CRS, INTERIM, RAW

CATEGORIES = {
    "shop": "is_shop",
    "food": "is_food",
    "bus_stop": "is_bus_stop",
    "train_station": "is_train_station",
}


def prepare_osm(folder=None, full_nsw=False):
    folder = INTERIM / "osm" if folder is None else folder
    folder.mkdir(parents=True, exist_ok=True)
    sydney_path = folder / "sydney.osm.pbf"
    poi_path = folder / "sydney_pois.osm.pbf"
    geopackage_path = folder / "sydney_pois.gpkg"

    if not full_nsw:
        subprocess.run(
            [
                "osmium", "extract", "-b", "150.45,-34.25,151.40,-33.35",
                "-s", "complete_ways", str(RAW / "osm/nsw.osm.pbf"),
                "-o", str(sydney_path), "--overwrite",
            ],
            check=True,
        )
    # Expanded experiments use the existing full NSW source, avoiding the
    # original Sydney bbox truncation at rural edges and 1 km buffers.
    source_path = RAW / "osm/nsw.osm.pbf" if full_nsw else sydney_path
    subprocess.run(
        [
            "osmium", "tags-filter", str(source_path),
            "nwr/shop", "nwr/amenity=cafe,restaurant",
            "nwr/highway=bus_stop", "nwr/railway=station", "nwr/leisure=park",
            "-o", str(poi_path), "--overwrite",
        ],
        check=True,
    )
    subprocess.run(
        [
            "ogr2ogr", "-f", "GPKG", "-overwrite",
            str(geopackage_path), str(poi_path),
        ],
        check=True,
        cwd=folder,
    )
    return geopackage_path


def get_tag(other_tags, key):
    if pd.isna(other_tags):
        return None
    pattern = rf'"{re.escape(key)}"=>"([^"]*)"'
    match = re.search(pattern, str(other_tags))
    if match:
        return match.group(1)
    return None


def load_osm(geopackage_path):
    points = gpd.read_file(geopackage_path, layer="points")
    polygons = gpd.read_file(geopackage_path, layer="multipolygons")
    for frame in (points, polygons):
        for tag in ("shop", "amenity", "highway", "railway", "leisure"):
            extracted = frame["other_tags"].apply(get_tag, args=(tag,))
            if tag in frame.columns:
                frame[tag] = frame[tag].fillna(extracted)
            else:
                frame[tag] = extracted

    polygon_points = polygons.copy()
    # Preserve the original order: representative points BEFORE projection.
    polygon_points["geometry"] = polygons.representative_point()
    combined = pd.concat([points, polygon_points], ignore_index=True)
    objects = gpd.GeoDataFrame(combined, geometry="geometry", crs=points.crs)
    objects = objects.to_crs(CRS)
    objects["is_shop"] = objects["shop"].notna() & (objects["shop"] != "vacant")
    objects["is_food"] = objects["amenity"].isin(["cafe", "restaurant"])
    objects["is_bus_stop"] = objects["highway"] == "bus_stop"
    objects["is_train_station"] = objects["railway"] == "station"
    for flag in CATEGORIES.values():
        objects[flag] = objects[flag].fillna(False)

    parks = polygons[polygons["leisure"] == "park"].to_crs(CRS).copy()
    parks = parks[parks.geometry.notna() & ~parks.geometry.is_empty].copy()
    parks["geometry"] = parks.geometry.make_valid()
    assert parks.geom_type.isin(["Polygon", "MultiPolygon"]).all(), (
        "Park repair produced non-polygon geometry; inspect it before continuing"
    )
    return objects, parks


def add_osm_counts(grid, objects, buffer_distances=(250, 500)):
    grid = grid.copy()
    context_area = grid.geometry.union_all().buffer(max(buffer_distances))
    nearby_objects = objects[objects.intersects(context_area)]
    inside = gpd.sjoin(
        nearby_objects,
        grid[["hex_id", "geometry"]],
        how="inner",
        predicate="within",
    )
    centres = grid[["hex_id", "geometry"]].copy()
    centres["geometry"] = grid.geometry.centroid

    for category, flag in CATEGORIES.items():
        category_inside = inside[inside[flag]]
        counts = category_inside.groupby("hex_id").size()
        grid[f"{category}_inside"] = grid["hex_id"].map(counts).fillna(0).astype(int)
        selected_objects = nearby_objects.loc[nearby_objects[flag], ["geometry"]]

        for radius in buffer_distances:
            zones = centres.copy()
            zones["geometry"] = centres.geometry.buffer(radius)
            matches = gpd.sjoin(
                zones, selected_objects, how="left", predicate="intersects"
            )
            counts = matches.groupby("hex_id")["index_right"].count()
            column = f"{category}_{radius}m"
            grid[column] = grid["hex_id"].map(counts).fillna(0).astype(int)
    return grid


def add_park_features(grid, parks, buffer_distances=(250, 500)):
    grid = grid.copy()
    context_area = grid.geometry.union_all().buffer(max(buffer_distances))
    nearby_parks = parks[parks.intersects(context_area)]
    park_union = nearby_parks.geometry.union_all()
    overlaps = intersection(grid.geometry.array, park_union)
    grid["park_area_inside_m2"] = area(overlaps)

    centres = grid.geometry.centroid
    for radius in buffer_distances:
        # Park buffers use 8 segments/quadrant; population/count buffers use 16.
        zones = buffer(centres.array, radius)
        overlaps = intersection(zones, park_union)
        grid[f"park_area_{radius}m_m2"] = area(overlaps)

    centre_points = grid[["hex_id", "geometry"]].copy()
    centre_points["geometry"] = centres
    # Query ALL available park polygons, not just the 500 m context subset.
    nearest = gpd.sjoin_nearest(
        centre_points, parks[["geometry"]], how="left", distance_col="distance_m"
    )
    distances = nearest.groupby("hex_id")["distance_m"].min()
    grid["distance_nearest_park_m"] = grid["hex_id"].map(distances)
    return grid
