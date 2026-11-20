"""Extract roads, junctions, schools, universities and stations in the study bbox from the Geofabrik PBF.

Usage: python -I extract_pbf.py PBF OUT_DIR
Writes (gzip CSV, WGS84):
  ways.csv.gz      every highway=* way: osm_id, tags we use, WKT linestring
  junctions.csv.gz nodes shared by 3+ road-way ends or 2+ drivable ways (lon, lat)
  pois.csv.gz      kind (school, university, station), lon, lat (areas -> centroid)
"""
import csv
import gzip
import sys
from collections import Counter
from pathlib import Path

import osmium

BBOX = (150.4939, -34.1406, 151.3624, -33.5211)
DRIVABLE = {"motorway", "trunk", "primary", "secondary", "tertiary", "unclassified", "residential",
            "motorway_link", "trunk_link", "primary_link", "secondary_link", "tertiary_link",
            "living_street", "service"}
WAY_TAGS = ["highway", "cycleway", "cycleway:left", "cycleway:right", "cycleway:both", "bicycle",
            "segregated", "maxspeed", "lanes", "oneway", "service", "bicycle_road",
            "construction", "proposed", "proposed:highway", "construction:highway"]


def inside(lon, lat):
    return BBOX[0] <= lon <= BBOX[2] and BBOX[1] <= lat <= BBOX[3]


def poi_kind(tags):
    amenity = tags.get("amenity")
    if amenity == "school":
        return "school"
    if amenity in ("university", "college"):
        return "university"
    if tags.get("railway") == "station" and tags.get("station") not in ("light_rail", "miniature"):
        return "station"
    return None


def main(pbf, out_dir):
    out_dir.mkdir(parents=True, exist_ok=True)
    node_use = Counter()
    ways_out = gzip.open(out_dir / "ways.csv.gz", "wt", newline="")
    ways = csv.writer(ways_out)
    ways.writerow(["osm_id", *WAY_TAGS, "wkt"])
    pois = []
    n_ways = 0
    fp = (osmium.FileProcessor(str(pbf))
          .with_locations("sparse_mem_array")
          .with_areas(osmium.filter.KeyFilter("amenity", "railway"))
          .with_filter(osmium.filter.KeyFilter("highway", "amenity", "railway")))
    for obj in fp:
        tags = obj.tags
        if obj.is_way() and "highway" in tags:
            coords = [(n.lon, n.lat) for n in obj.nodes if n.location.valid()]
            if len(coords) < 2 or not any(inside(*c) for c in coords):
                continue
            ways.writerow([obj.id, *[tags.get(k, "") for k in WAY_TAGS],
                           "LINESTRING (" + ", ".join(f"{x:.7f} {y:.7f}" for x, y in coords) + ")"])
            n_ways += 1
            if tags.get("highway") in DRIVABLE and tags.get("highway") != "service":
                for n in obj.nodes:
                    node_use[(n.ref, round(n.lon, 7), round(n.lat, 7))] += 1
        elif obj.is_node():
            kind = poi_kind(tags)
            if kind and inside(obj.location.lon, obj.location.lat):
                pois.append((kind, obj.location.lon, obj.location.lat))
        elif obj.is_area():
            kind = poi_kind(tags)
            if kind:
                pts = [(n.lon, n.lat) for ring in obj.outer_rings() for n in ring if n.location.valid()]
                if pts:
                    lon = sum(p[0] for p in pts) / len(pts)
                    lat = sum(p[1] for p in pts) / len(pts)
                    if inside(lon, lat):
                        pois.append((kind, lon, lat))
    ways_out.close()
    with gzip.open(out_dir / "junctions.csv.gz", "wt", newline="") as f:
        w = csv.writer(f)
        w.writerow(["lon", "lat"])
        # A node used by 2+ drivable ways is a junction (or a way split mid-street; those are rare
        # in the residential grid and only add noise to a density feature).
        w.writerows((lon, lat) for (_, lon, lat), c in node_use.items() if c >= 2 and inside(lon, lat))
    with gzip.open(out_dir / "pois.csv.gz", "wt", newline="") as f:
        w = csv.writer(f)
        w.writerow(["kind", "lon", "lat"])
        w.writerows(pois)
    print(f"{n_ways} highway ways, {sum(1 for c in node_use.values() if c >= 2)} junction nodes, "
          f"{Counter(p[0] for p in pois)}")


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]))
