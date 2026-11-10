import pandas as pd, numpy as np
g=pd.read_pickle("/tmp/pigeon-eval/growth/growth_ranked.pkl")
g.drop(columns=[c for c in g.columns if c.endswith("_rank")]).to_csv("/tmp/pigeon-eval/growth/growth_predictions_full.csv",index=False)
# sanity: rank ties and a random-baseline for top-100
print((g.baseline_pred>0.005).sum())
# how many of 35 toilet hexes within top 100 vs chance
print(100*35/1108)
# population in growth hexes
print(g.population_est.sum(), g.population_est.describe())
# suburb-level ratio
