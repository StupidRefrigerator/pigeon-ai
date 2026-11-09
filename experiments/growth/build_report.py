import pandas as pd, numpy as np
O="/tmp/pigeon-eval/growth/"
g=pd.read_pickle(O+"growth_ranked.pkl"); m=pd.read_csv(O+"metrics.csv")
sub=g.groupby("suburb").agg(hexes=("hex_id","size"),actual_toilets=("toilet_count","sum"),baseline_pred=("baseline_pred","sum"),good_areas_pred=("good_areas_pred","sum")).round(1)
sub.loc["TOTAL"]=sub.sum()
t=g[g.toilet_count>0].sort_values(["suburb","baseline_rank"])[["hex_id","suburb","toilet_count","baseline_pred","good_areas_pred","baseline_rank","good_areas_rank"]].round(2)
sub.reset_index().to_csv(O+"per_suburb.csv",index=False); t.to_csv(O+"toilet_hexes.csv",index=False)
cand=[]
for mod in ["baseline","good_areas"]:
    c=g[(g[mod+"_pred"]-g.toilet_count)>=1][["hex_id","suburb","lat","lng","toilet_count",mod+"_pred"]].round(4); c.insert(0,"model",mod); cand.append(c.rename(columns={mod+"_pred":"pred"}))
pd.concat(cand).to_csv(O+"candidates.csv",index=False)
mt=m.set_index("model").T
mt.loc["pred/actual"]=(m.set_index("model").pred_total/39).values
md=lambda d,**k:d.to_markdown(**k)
rep=f"""# Growth-suburb out-of-area test (v1 features, 19 columns)

Both models were trained only on the 16,228 study hexes and applied unchanged to the 1,108 growth hexes
(39 toilets in 35 hexes, 16 of the 20 growth suburbs; Badgerys Creek, Luddenham, Appin and Menangle Park have no hexes in the file).
Baseline = forest on all study hexes. Good areas = forest on the 4,457 study hexes in the 20 good blocks.
Both use `make_forest(0)`, single seed. No cross-validation is needed: no growth hex was ever in training.

## Headline

{md(mt.round(3).astype(str))}

Reading it:
- Baseline predicts 54.6 toilets for 39 real (1.4x). Good areas predicts 97.3 (2.5x): it over-predicts badly out of area, as expected from a model trained on blocks where toilets are over-supplied relative to the baseline.
- Poisson deviance (lower is better): baseline 0.163, good areas 0.210. Baseline is better calibrated.
- Ranking is a wash. PR-AUC 0.31 for both vs a base rate of 0.032 (about 10x chance). Toilets in the top 100 hexes: 28 vs 27 (24 vs 23 of the 35 toilet hexes); chance would be about 3.
- The good-areas model is slightly better at the very top-35 (16 vs 13 toilets) and slightly worse at top 20 (11 vs 12). With 35 positive hexes these differences are one or two toilets, i.e. noise.
- Candidates (pred - actual >= 1): one each, and it is the same hex (89be085a90fffff, Schofields, 0 toilets, predicted 1.22 baseline / 1.18 good areas). Almost no growth hex is predicted above 1 (baseline: 2 hexes, good areas: 4), because these are new, low-density, low-amenity hexes in the 2021 data.

## Per suburb (approximate assignment)

Hexes are assigned to the nearest *growth-suburb* representative point in `sydney_places.json` (no suburb polygons are available offline: `data/raw` is absent). This is a Voronoi split, so boundaries are rough; 286 hexes would instead be nearest a non-growth neighbour (Horningsea Park, Angus, Bradfield, Rossmore, Harrington Park, West Hoxton, Grantham Farm, Denham Court...). The column `nearest_place_all` in growth_predictions.csv gives that alternative label. Treat per-suburb numbers as indicative.

{md(sub)}

Pattern: both models under-predict the already built-up, toilet-rich suburbs (Gregory Hills 7 real vs 3.0/4.8, Riverstone 6 vs 3.9/5.1, Leppington 6 vs 4.8/9.6 for baseline/good) and over-predict the ones still mostly greenfield with 0 toilets (Marsden Park 0 vs 4.7/9.5, Austral 0 vs 2.2/4.7, Vineyard, Bringelly). Marsden Park, Box Hill and Colebee are the main over-prediction pockets; the plausible reading is that they are being built out (see population caveat), so a model fed 2021 inputs expects toilets for their location but 2021 population and amenities are still low.

## The 35 toilet hexes: predictions and rank (of 1,108; 1 = most toilets predicted)

{md(t,index=False)}

Rank is the stable sort by predicted count (ties are rare but exist at the near-zero tail). Hexes ranked below 300 under both models (e.g. Riverstone 89be0858d23ffff, Shanes Park 89be0840417ffff, Gregory Hills 89be08ce807ffff) have almost no population/amenities in the 2021 inputs, so the model cannot see why a toilet is there.

## Candidates (pred - actual >= 1) in growth areas

Baseline: 1 hex. Good areas: 1 hex. Same hex.

{md(pd.concat(cand).reset_index(drop=True),index=False)}

Raising the sensitivity (e.g. pred - actual >= 0.5) would be needed to get a usable candidate list in these suburbs; at the repo's threshold of 1.0 the models flag almost nothing here. Full ranked lists are in growth_predictions.csv.

## Caveats

- Population is the 2021 census, allocated from SA1 polygons. These suburbs have grown a lot since, and amenities mapped in OSM then are a snapshot of the same period; so the inputs understate current demand and the "over-prediction" in the greenfield suburbs may partly be demand that is not yet served rather than a model error. The comparison also cannot tell us whether the 39 toilets (as listed on the National Public Toilet Map, possibly newer than the inputs) were placed in response to growth after 2021.
- Toilet counts: the toilet data and the inputs are not time-aligned. Toilets built after 2021 sit in hexes whose features still look empty.
- Good blocks were selected using the baseline's `latest`-feature out-of-fold predictions (as committed in good_blocks.csv); this test applies them to a v1-feature forest. The block choice is therefore not tuned on the growth hexes, but it is also not the exact v1 selection.
- Single seed and 35 positive hexes: ranking differences of 1 to 3 toilets are not meaningful.
- Suburb assignment is approximate (above).
- Hit counts use toilets (summing toilet_count over the top N hexes), and "hexes with a toilet" separately; the repo's `top_hits` counts hexes with a toilet.

## Stretch: `latest` feature set - NOT DONE

Skipped. The 9 missing columns cannot be recomputed from the repo (`data/raw` and `data/interim` are not present: no NSW OSM extract, no osmium, no SA1 boundaries). I tried live Overpass (a bbox cut into 0.05 then 0.1 degree tiles, cached in osm_cache/). The public server returned 429/502/504 repeatedly: 4 of 19 tiles in about 25 minutes, so full coverage of the growth area was not reachable in the time box, and I stopped. Further problems that would remain even with the data: `population_1000m` needs SA1 population polygons (not OSM) and could only be approximated from the hex-level population; OSM polygon centres from Overpass differ slightly from the repo's representative points; the OSM snapshot differs from the one the committed features used. Scripts fetch_osm.py and compute_features.py are in this folder, unfinished (compute_features.py has never been run, and validation against 200 study hexes was therefore not done). Do not treat the `latest` results as available.

## Files
growth_predictions.csv (hex_id, suburb, nearest_place_all, lat, lng, toilet_count, baseline_pred, good_areas_pred), growth_predictions_full.csv (all features), metrics.csv, per_suburb.csv, toilet_hexes.csv, candidates.csv. Scripts: run_core.py, metrics.py, tables.py, build_report.py.
"""
open(O+"report.md","w").write(rep)
