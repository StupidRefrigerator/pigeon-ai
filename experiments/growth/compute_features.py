"""Compute the 9 missing `latest` columns from cached Overpass data, using repo definitions."""
import sys, glob, json, numpy as np, pandas as pd, geopandas as gpd, h3
from shapely.geometry import LineString, Point, Polygon, MultiPolygon
from shapely.ops import polygonize, unary_union
from shapely import buffer, area, intersection
ROOT="/Users/summitsetia/Desktop/University/26T3/PIGEON-AI-DATASET"
sys.path.insert(0,ROOT+"/src")
from pigeon_ai.accessibility import eligible_way, PATH_TYPES, walking_junctions
from pigeon_ai.paths import CRS
OUT="/tmp/pigeon-eval/growth/"
def load(prefix):
    els={}
    for f in glob.glob(OUT+"osm_cache/all_*.json"):
        for e in json.load(open(f))["elements"]:
            t=e.get("tags",{})
            kind=("park" if t.get("leisure")=="park" else "hw" if (e["type"]=="way" and "highway" in t and "geometry" in e and "center" not in e and t.get("highway")!="bus_stop") else "poi" if ("center" in e or e["type"]=="node") else None)
            if kind==prefix: els[(e["type"],e["id"])]=e
    return list(els.values())
# --- ways
rows=[]
for e in load("hw"):
    tags=e.get("tags",{})
    if not eligible_way(tags) or len(e.get("nodes",[]))<2: continue
    geom=[(p["lon"],p["lat"]) for p in e["geometry"]]
    rows.append(dict(osm_id=e["id"],nodes=e["nodes"],dedicated=tags["highway"] in PATH_TYPES,
        roundabout=tags.get("junction") in {"roundabout","circular"},geometry=LineString(geom)))
ways=gpd.GeoDataFrame(rows,crs=4326).to_crs(CRS); print("ways",len(ways),"dedicated",ways.dedicated.sum())
# --- POIs
pr=[]
for e in load("poi"):
    t=e.get("tags",{})
    if e["type"]=="node": lo,la=e["lon"],e["lat"]
    else:
        c=e.get("center"); 
        if not c: continue
        lo,la=c["lon"],c["lat"]
    pr.append(dict(shop=t.get("shop") is not None and t.get("shop")!="vacant",food=t.get("amenity") in("cafe","restaurant"),
        bus_stop=t.get("highway")=="bus_stop",train_station=t.get("railway")=="station",geometry=Point(lo,la)))
pois=gpd.GeoDataFrame(pr,crs=4326).to_crs(CRS); print("pois",len(pois),pois[["shop","food","bus_stop","train_station"]].sum().to_dict())
# --- parks
polys=[]
for e in load("park"):
    if e["type"]=="way":
        g=e["geometry"]
        if len(g)>=4 and g[0]==g[-1]: polys.append(Polygon([(p["lon"],p["lat"]) for p in g]))
    else:
        outer=[LineString([(p["lon"],p["lat"]) for p in m["geometry"]]) for m in e.get("members",[]) if m.get("role")=="outer" and m.get("geometry")]
        inner=[LineString([(p["lon"],p["lat"]) for p in m["geometry"]]) for m in e.get("members",[]) if m.get("role")=="inner" and m.get("geometry")]
        o=unary_union(list(polygonize(unary_union(outer)))) if outer else None
        if o is None or o.is_empty: continue
        i=unary_union(list(polygonize(unary_union(inner)))) if inner else None
        polys.append(o.difference(i) if i is not None and not i.is_empty else o)
parks=gpd.GeoSeries(polys,crs=4326).to_crs(CRS).make_valid()
park_union=unary_union(list(parks)); print("parks",len(parks))
junc=walking_junctions(ways); print("junctions",len(junc))
jf=gpd.GeoDataFrame(geometry=junc.reset_index(drop=True),crs=CRS)
def compute(hexes):
    grid=gpd.GeoDataFrame({"hex_id":hexes},geometry=[Polygon([(lo,la) for la,lo in h3.cell_to_boundary(h)]) for h in hexes],crs=4326).to_crs(CRS)
    cen=grid.geometry.centroid
    out=pd.DataFrame({"hex_id":hexes}).set_index("hex_id")
    zones1k=gpd.GeoDataFrame({"hex_id":hexes},geometry=cen.buffer(1000),crs=CRS)
    for cat in ["shop","food","bus_stop","train_station"]:
        sel=pois[pois[cat]][["geometry"]]
        m=gpd.sjoin(zones1k,sel,how="left",predicate="intersects")
        out[f"{cat}_1000m"]=m.groupby("hex_id")["index_right"].count().reindex(hexes).values
    out["park_area_1000m_m2"]=area(intersection(buffer(cen.array,1000),park_union))
    zones=gpd.GeoDataFrame({"hex_id":hexes},geometry=cen.buffer(500),crs=CRS).reset_index(drop=True)
    paths=ways.loc[ways.dedicated,["geometry"]]
    near=gpd.sjoin_nearest(gpd.GeoDataFrame(geometry=cen.reset_index(drop=True),crs=CRS),paths,how="left",distance_col="d")["d"].groupby(level=0).min()
    out["distance_nearest_footpath_m"]=near.values
    mm=gpd.sjoin(zones,jf,predicate="intersects",how="left")
    out["walkable_junctions_500m"]=mm.groupby(level=0)["index_right"].count().values
    idx=ways.sindex; L=[]
    for z in zones.geometry:
        c=idx.query(z,predicate="intersects"); L.append(ways.geometry.iloc[c].intersection(z).union_all().length)
    out["walkable_length_500m"]=L
    return out
# population_1000m: area-weighted hex population (approximation; SA1 shapes unavailable)
allf=pd.read_csv(ROOT+"/data/processed/sydney_growth_features.csv")
hp=allf.set_index("hex_id").population_est
def hexpoly(h): return Polygon([(lo,la) for la,lo in h3.cell_to_boundary(h)])
hg=gpd.GeoDataFrame({"hex_id":allf.hex_id,"pop":allf.population_est},geometry=[hexpoly(h) for h in allf.hex_id],crs=4326).to_crs(CRS)
hg["a"]=hg.geometry.area
def pop1k(hexes):
    g=gpd.GeoDataFrame({"hex_id":hexes},geometry=[hexpoly(h) for h in hexes],crs=4326).to_crs(CRS)
    zones=gpd.GeoDataFrame({"hex_id":hexes},geometry=g.geometry.centroid.buffer(1000),crs=CRS)
    ov=gpd.overlay(zones,hg[["pop","a","geometry"]],how="intersection",keep_geom_type=True)
    ov["c"]=ov["pop"]*ov.geometry.area/ov["a"]
    return ov.groupby("hex_id").c.sum().reindex(hexes).fillna(0).values
growth=pd.read_pickle(OUT+"growth_ranked.pkl"); val=pd.read_pickle(OUT+"validation_hexes.pkl")
for name,hx in [("growth",list(growth.hex_id)),("val",list(val.hex_id))]:
    o=compute(hx); o["population_1000m"]=pop1k(hx); o.to_csv(OUT+f"computed_{name}.csv"); print(name,"done")
