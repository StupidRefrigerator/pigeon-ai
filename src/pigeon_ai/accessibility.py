"""Public walking linework and OSM-node connectivity for V6."""

from collections import defaultdict
import subprocess
import xml.etree.ElementTree as ET

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely import LineString, box

from .paths import CRS, INTERIM, RAW

ACCESSIBILITY_FEATURES = [
    "walkable_length_500m", "walkable_junctions_500m",
    "distance_nearest_footpath_m",
]
PATH_TYPES = {"footway", "path", "pedestrian", "steps", "cycleway"}
STREET_TYPES = {
    "residential", "living_street", "service", "unclassified", "road", "track",
    "primary", "secondary", "tertiary",
    "primary_link", "secondary_link", "tertiary_link", "trunk", "trunk_link",
}
PUBLIC_ACCESS = {"", "yes", "public", "designated", "permissive"}


def eligible_way(tags):
    """Conservative outdoor/public policy; do not infer missing sidewalks."""
    highway = tags.get("highway", "")
    if highway not in PATH_TYPES | STREET_TYPES:
        return False
    if tags.get("area") == "yes" or tags.get("indoor") == "yes":
        return False
    if tags.get("access", "") not in PUBLIC_ACCESS:
        return False
    foot = tags.get("foot", "")
    if foot not in PUBLIC_ACCESS:
        return False
    # Cycleways and major trunk roads need explicit permission for walking.
    if highway in {"cycleway", "trunk", "trunk_link"} and not foot:
        return False
    if highway in STREET_TYPES:
        # Retain the mapped sidepath instead of counting its parallel road too.
        sidewalk_keys = ("sidewalk", "sidewalk:both", "sidewalk:left", "sidewalk:right")
        if any(tags.get(key) == "separate" for key in sidewalk_keys):
            return False
    return True


def extract_walking_network(grid, padding=5000):
    """Extract once with complete ways and references; certify coverage later."""
    folder = INTERIM / "accessibility"
    folder.mkdir(parents=True, exist_ok=True)
    extent = box(*grid.total_bounds).buffer(padding)
    bounds = gpd.GeoSeries([extent], crs=CRS).to_crs(4326).total_bounds
    bbox = ",".join(map(str, bounds))
    area_path = folder / "walking_area.osm.pbf"
    network_path = folder / "walking_network.osm.pbf"
    subprocess.run([
        "osmium", "extract", "-b", bbox, "-s", "complete_ways",
        str(RAW / "osm/nsw.osm.pbf"), "-o", str(area_path), "--overwrite",
    ], check=True)
    subprocess.run([
        "osmium", "tags-filter", str(area_path), "w/highway",
        "-o", str(network_path), "--overwrite",
    ], check=True)
    # Densify geographic rectangle edges before projection for the coverage test.
    coverage = gpd.GeoSeries(
        [box(*bounds).segmentize(0.01)], crs=4326,
    ).to_crs(CRS).iloc[0]
    return network_path, coverage


def load_walking_network(path):
    """Stream native OSM XML to preserve node IDs; no extra Python dependency."""
    nodes = {}
    rows = []
    process = subprocess.Popen(
        ["osmium", "cat", str(path), "-f", "osm"], stdout=subprocess.PIPE,
    )
    try:
        context = ET.iterparse(process.stdout, events=("start", "end"))
        _, root = next(context)
        for event, element in context:
            if event != "end":
                continue
            if element.tag == "node":
                nodes[int(element.attrib["id"])] = (
                    float(element.attrib["lon"]), float(element.attrib["lat"]),
                )
                root.clear()
            elif element.tag == "way":
                tags = {tag.attrib["k"]: tag.attrib["v"] for tag in element.findall("tag")}
                if eligible_way(tags):
                    refs = [int(nd.attrib["ref"]) for nd in element.findall("nd")]
                    if len(refs) >= 2:
                        missing = [node for node in refs if node not in nodes]
                        if missing:
                            raise ValueError(f"Missing node coordinates in way {element.attrib['id']}")
                        rows.append({
                            "osm_id": int(element.attrib["id"]), "nodes": refs,
                            "dedicated": tags["highway"] in PATH_TYPES,
                            "roundabout": tags.get("junction") in {"roundabout", "circular"},
                            "geometry": LineString([nodes[node] for node in refs]),
                        })
                root.clear()
            elif element.tag == "relation":
                root.clear()
        if process.wait() != 0:
            raise RuntimeError("osmium failed while reading walking network")
    finally:
        process.stdout.close()
        if process.poll() is None:
            process.terminate()
            process.wait()
    if not rows:
        raise ValueError("No eligible walking ways found")
    return gpd.GeoDataFrame(rows, crs=4326).to_crs(CRS)


def walking_junctions(ways, merge_distance=10):
    """Unique node neighbours; merge junctions connected within 10 m/rings."""
    neighbours = defaultdict(set)
    coordinates = {}
    ring_edges = []
    for row in ways.itertuples():
        coordinates.update(zip(row.nodes, row.geometry.coords))
        for start, end in zip(row.nodes, row.nodes[1:]):
            if start == end or coordinates[start] == coordinates[end]:
                continue
            neighbours[start].add(end)
            neighbours[end].add(start)
            if row.roundabout:
                ring_edges.append((start, end))
    ids = [node for node, adjacent in neighbours.items() if len(adjacent) >= 3]
    points = gpd.GeoSeries(
        gpd.points_from_xy(
            [coordinates[node][0] for node in ids],
            [coordinates[node][1] for node in ids],
        ), index=ids, crs=CRS,
    )
    if points.empty:
        return points
    parent = {node: node for node in set(ids) | {n for edge in ring_edges for n in edge}}

    def find(node):
        while parent[node] != node:
            parent[node] = parent[parent[node]]
            node = parent[node]
        return node

    def join(start, end):
        parent[find(start)] = find(end)

    def close_connection(start, end):
        # Nearby bridge/underpass junctions must stay separate unless the
        # walking graph actually connects them within the merge distance.
        best = {start: 0.0}
        pending = [(start, 0.0)]
        while pending:
            node, distance = pending.pop()
            if node == end:
                return True
            x, y = coordinates[node]
            for neighbour in neighbours[node]:
                nx, ny = coordinates[neighbour]
                total = distance + np.hypot(nx - x, ny - y)
                if total <= merge_distance and total < best.get(neighbour, float("inf")):
                    best[neighbour] = total
                    pending.append((neighbour, total))
        return False

    for start, end in ring_edges:
        join(start, end)
    left, right = points.sindex.query(points, predicate="dwithin", distance=merge_distance)
    for start, end in zip(left, right):
        if start < end and close_connection(ids[start], ids[end]):
            join(ids[start], ids[end])
    groups = pd.Series([find(node) for node in ids], index=ids)
    # A roundabout/complex intersection contributes one physical junction.
    return points.groupby(groups).agg(lambda group: group.union_all().centroid)


def calculate_accessibility(grid, ways, coverage):
    centres = grid.geometry.centroid
    zones = gpd.GeoDataFrame(
        {"hex_id": grid["hex_id"].to_numpy()}, geometry=centres.buffer(500), crs=CRS,
    ).reset_index(drop=True)
    paths = ways.loc[ways["dedicated"], ["geometry"]]
    if paths.empty:
        raise ValueError("No dedicated pedestrian paths available for nearest distances")
    nearest = gpd.sjoin_nearest(
        gpd.GeoDataFrame(geometry=centres.reset_index(drop=True), crs=CRS),
        paths, how="left", distance_col="distance",
    )["distance"].groupby(level=0).min()
    # Anything omitted by the rectangular extraction is at least this far away.
    margin = centres.reset_index(drop=True).distance(coverage.boundary)
    if not centres.within(coverage).all() or (nearest + 1 >= margin).any() or (margin <= 501).any():
        raise ValueError("Walking extract is too small; increase padding (nearest search/buffers uncertified)")

    junctions = walking_junctions(ways)
    junction_frame = gpd.GeoDataFrame(geometry=junctions.reset_index(drop=True), crs=CRS)
    matches = gpd.sjoin(zones, junction_frame, predicate="intersects", how="left")
    counts = matches.groupby(level=0)["index_right"].count()
    # Spatial-index candidates only; union removes coincident/reversed geometry
    # before measuring clipped linework. Parallel distinct sidewalks remain.
    lengths = []
    index = ways.sindex
    for zone in zones.geometry:
        candidates = index.query(zone, predicate="intersects")
        clipped = ways.geometry.iloc[candidates].intersection(zone)
        lengths.append(clipped.union_all().length)
    result = pd.DataFrame({
        "walkable_length_500m": lengths,
        "walkable_junctions_500m": counts.to_numpy(dtype=int),
        "distance_nearest_footpath_m": nearest.to_numpy(),
    }, index=pd.Index(grid["hex_id"], name="hex_id"))
    if not np.isfinite(result.to_numpy()).all() or (result < 0).any().any():
        raise ValueError("Missing, negative or infinite accessibility values")
    print(
        f"Walking ways: {len(ways):,}; dedicated paths: {len(paths):,}; "
        f"consolidated junctions: {len(junctions):,}; "
        f"minimum extraction margin: {margin.min():.0f} m; "
        f"maximum nearest-path distance: {nearest.max():.0f} m", flush=True,
    )
    return result
