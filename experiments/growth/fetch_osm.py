"""Fetch OSM for tiles covering growth hexes + validation study hexes. Cached to disk."""
import json, os, sys, time, math, requests, numpy as np, pandas as pd, h3
ROOT="/Users/summitsetia/Desktop/University/26T3/PIGEON-AI-DATASET"
OUT="/tmp/pigeon-eval/growth/"
os.makedirs(OUT+"osm_cache",exist_ok=True)
PAD=0.02   # ~2.4 km lat; margin for 1 km buffers + nearest-footpath search
TILE=0.1
HW='footway|path|pedestrian|steps|cycleway|residential|living_street|service|unclassified|road|track|primary|secondary|tertiary|primary_link|secondary_link|tertiary_link|trunk|trunk_link'
growth=pd.read_pickle(OUT+"growth_core.pkl")
study=pd.read_csv(ROOT+"/data/processed/sydney_extended_features.csv")
study[["lat","lng"]]=[h3.cell_to_latlng(h) for h in study.hex_id]
# validation: study hexes nearest to growth hexes (within ~3km), random 200
from scipy.spatial import cKDTree
kt=cKDTree(np.c_[growth.lat*111,growth.lng*92])
d,_=kt.query(np.c_[study.lat*111,study.lng*92])
near=study[d<1.5]
print("study hexes within 3km:",len(near))
val=near.sample(200,random_state=0)
val.to_pickle(OUT+"validation_hexes.pkl")
pts=pd.concat([growth[["lat","lng"]],val[["lat","lng"]]])
tiles=set()
for la,lo in zip(pts.lat,pts.lng):
    for dla in (-PAD,0,PAD):
        for dlo in (-PAD,0,PAD):
            tiles.add((math.floor((la+dla)/TILE),math.floor((lo+dlo)/TILE)))
print("tiles",len(tiles))
URLS=["https://overpass-api.de/api/interpreter","https://overpass.kumi.systems/api/interpreter"]
def q(bbox,body,name):
    f=OUT+f"osm_cache/{name}.json"
    if os.path.exists(f): return json.load(open(f))
    for attempt in range(6):
        url=URLS[attempt%2]
        try:
            r=requests.post(url,data={"data":f"[out:json][timeout:180];{body.replace('BB',bbox)}"},headers={"User-Agent":"pigeon-ai-uni-project"},timeout=240)
            if r.status_code==200:
                j=r.json(); json.dump(j,open(f,"w")); return j
            print("status",r.status_code,name,flush=True); time.sleep(15*(attempt+1))
        except Exception as e:
            print("err",e,flush=True); time.sleep(15)
    raise SystemExit("failed "+name)
BODY=('way["highway"~"^(%s)$"](BB);out geom tags;'
      '(nwr["shop"](BB);nwr["amenity"~"^(cafe|restaurant)$"](BB);nwr["highway"="bus_stop"](BB);nwr["railway"="station"](BB););out center tags;'
      '(way["leisure"="park"](BB);relation["leisure"="park"](BB););out geom tags;') % HW
for i,(a,b) in enumerate(sorted(tiles)):
    bbox=f"{a*TILE},{b*TILE},{(a+1)*TILE},{(b+1)*TILE}"
    q(bbox,BODY,f"all_{a}_{b}")
    print(i+1,len(tiles),flush=True); time.sleep(5)
print("done")
