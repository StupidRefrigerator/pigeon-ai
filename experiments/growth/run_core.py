import sys, json, numpy as np, pandas as pd, h3
ROOT="/Users/summitsetia/Desktop/University/26T3/PIGEON-AI-DATASET"
sys.path.insert(0, ROOT+"/src")
from pigeon_ai.model import TARGETS, make_forest
OUT="/tmp/pigeon-eval/growth/"
FS = sys.argv[1] if len(sys.argv)>1 else "v1"
feats = TARGETS["toilets"].feature_sets["v1"]
study = pd.read_csv(ROOT+"/data/processed/sydney_extended_features.csv")
g = pd.read_csv(ROOT+"/data/processed/sydney_growth_features.csv")
study_ids=set(study.hex_id)
growth = g[~g.hex_id.isin(study_ids)].reset_index(drop=True)
print(len(study), len(growth), growth.toilet_count.sum(), (growth.toilet_count>0).sum())
print("NaNs", growth[feats].isna().sum().sum(), study[feats].isna().sum().sum())
good = set(pd.read_csv(ROOT+"/data/model/good_areas/good_blocks.csv").block)
blk = np.array([h3.cell_to_parent(h,6) for h in study.hex_id])
m = np.isin(blk, list(good)); print("good hexes", m.sum())
base = make_forest(0).fit(study[feats].values, study.toilet_count.values)
ga = make_forest(0).fit(study.loc[m,feats].values, study.toilet_count.values[m])
growth["baseline_pred"]=base.predict(growth[feats].values)
growth["good_areas_pred"]=ga.predict(growth[feats].values)
growth[["lat","lng"]]=[h3.cell_to_latlng(h) for h in growth.hex_id]
pl=json.load(open(ROOT+"/data/reference/sydney_places.json"))["places"]
names=[l.strip() for l in open(ROOT+"/data/reference/growth_suburbs.txt") if l.strip()]
print([n for n in names if n not in pl])
allp=pd.DataFrame([(k,v[0],v[1]) for k,v in pl.items()],columns=["n","la","lo"])
# nearest among ALL places (so non-growth neighbours claim their hexes), then keep label
def near(la,lo):
    d=((allp.la-la)*111)**2+((allp.lo-lo)*92)**2
    return allp.n.iloc[int(d.values.argmin())]
growth["nearest_place_all"]=[near(a,b) for a,b in zip(growth.lat,growth.lng)]
gp=allp[allp.n.isin(names)]
def near_g(la,lo):
    d=((gp.la-la)*111)**2+((gp.lo-lo)*92)**2
    return gp.n.iloc[int(d.values.argmin())]
growth["suburb"]=[near_g(a,b) for a,b in zip(growth.lat,growth.lng)]
growth.to_pickle(OUT+"growth_core.pkl")
growth[["hex_id","suburb","nearest_place_all","lat","lng","toilet_count","baseline_pred","good_areas_pred"]].to_csv(OUT+"growth_predictions.csv",index=False)
print(growth[["toilet_count","baseline_pred","good_areas_pred"]].sum())
print(growth.groupby("suburb").agg(h=("hex_id","size"),t=("toilet_count","sum"),b=("baseline_pred","sum"),g=("good_areas_pred","sum")).round(1))
print((growth.suburb!=growth.nearest_place_all).sum(), growth[growth.suburb!=growth.nearest_place_all].nearest_place_all.value_counts().head(8))
