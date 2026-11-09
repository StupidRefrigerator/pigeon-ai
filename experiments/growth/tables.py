import numpy as np, pandas as pd
OUT="/tmp/pigeon-eval/growth/"
g=pd.read_pickle(OUT+"growth_ranked.pkl")
sub=g.groupby("suburb").agg(hexes=("hex_id","size"),actual=("toilet_count","sum"),baseline=("baseline_pred","sum"),good_areas=("good_areas_pred","sum")).round(1)
sub.loc["TOTAL"]=sub.sum(); print(sub.to_markdown())
t=g[g.toilet_count>0].sort_values(["suburb","baseline_rank"])
print(t[["hex_id","suburb","toilet_count","baseline_pred","good_areas_pred","baseline_rank","good_areas_rank"]].round(2).to_markdown(index=False))
for m in ["baseline","good_areas"]:
    c=g[(g[m+"_pred"]-g.toilet_count)>=1]
    print(m); print(c[["hex_id","suburb","lat","lng","toilet_count",m+"_pred"]].round(3).to_markdown(index=False))
print(g[["baseline_pred","good_areas_pred"]].describe().round(2))
print("hexes pred>=1:",(g.baseline_pred>=1).sum(),(g.good_areas_pred>=1).sum())
print((g[(g.toilet_count>0)][["baseline_rank","good_areas_rank"]]<=100).sum())
