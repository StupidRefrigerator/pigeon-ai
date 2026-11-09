import sys, numpy as np, pandas as pd
from sklearn.metrics import average_precision_score, mean_poisson_deviance
OUT="/tmp/pigeon-eval/growth/"
g=pd.read_pickle(OUT+"growth_core.pkl") if len(sys.argv)<2 else pd.read_pickle(sys.argv[1])
models=[c for c in g.columns if c.endswith("_pred")]
y=g.toilet_count.values
rows=[]
for m in models:
    p=np.clip(g[m].values,1e-6,None)
    order=np.argsort(-p,kind="stable"); g[m.replace("_pred","_rank")]=pd.Series(np.empty(len(g),int)); 
    rank=np.empty(len(g),int); rank[order]=np.arange(1,len(g)+1); g[m.replace("_pred","_rank")]=rank
    hit=lambda k:int(y[order[:k]].sum())
    rows.append(dict(model=m[:-5],pred_total=p.sum(),actual=y.sum(),deviance=mean_poisson_deviance(y,p),
      pr_auc=average_precision_score(y>0,p),base_rate=(y>0).mean(),toilets_top20=hit(20),toilets_top35=hit(35),toilets_top100=hit(100),
      hexes_with_toilet_in_top100=int((y[order[:100]]>0).sum()),hexes_with_toilet=int((y>0).sum()),
      candidates=int(((p-y)>=1).sum())))
r=pd.DataFrame(rows); print(r.round(3).T.to_string()); r.to_csv(OUT+"metrics.csv",index=False)
g.to_pickle(OUT+"growth_ranked.pkl")
