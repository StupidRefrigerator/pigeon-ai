"""Oran Park proxy check (experiments/future/run_oran_park.py) for v1 vs v1+F (and the +L versions).

Real features: the growth-set values. Proxy v1: experiments/future/oran_features.csv (zoning proxy, mid shops,
calibrated bus). Proxy F: Oran Park's RE1 land treated as undeveloped and filled at the pooled established-suburb
RE1 rates, the method of pigeon-v2/data/scripts/planned.py (sports/playground start at 0; distances start at
2,500 m and fall to the nearest RE1 parcel big enough for >= 0.5 expected features; beach values kept as real).
"""
import glob
import json
import sys

import geopandas as gpd
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from common import F, MODELS, OUT, REPO, V2, features, label, load_growth, load_study, make_forest

sys.path.insert(0, str(V2 / "data/scripts"))
from hexsets import CRS, grid  # noqa: E402
from planned import parcels, planned  # noqa: E402

PROXY_V1 = "zoning_proxy|shops_mid|bus_calibrated"
BASE_DIST_M = 2500.0

study, growth = load_study(), load_growth().set_index("hex_id")
of = pd.read_csv(REPO / "experiments/future/oran_features.csv")
ids = of[of.scenario == "real_features"].hex_id.tolist()
real = growth.loc[ids]
proxy_v1 = of[of.scenario == PROXY_V1].set_index("hex_id").loc[ids]

z = gpd.read_file(glob.glob("/tmp/pigeon-eval/future/downloads/arcgis_zoning_oran_*.geojson")[0]).to_crs(CRS)
z["geometry"] = z.geometry.make_valid()
und = parcels(z, ["RE1"])
rate = json.load(open(V2 / "data/planned_checks.json"))["rates"]
base = real[F].copy()
for c in F:
    if c.startswith(("sports", "playground")) and not c.startswith("distance"):
        base[c] = 0.0
base["distance_nearest_sports_m"] = BASE_DIST_M
base["distance_nearest_playground_m"] = BASE_DIST_M
g = grid(ids)
proxy_f = planned(base, g, und, rate, "proxy").drop(columns="scenario").loc[ids]
print("RE1 parcels", len(und), "ha", round(und.area.sum() / 1e4, 1))
print(pd.DataFrame({"real": real[["sports_500m", "playground_500m", "distance_nearest_sports_m"]].mean(),
                    "proxy": proxy_f[["sports_500m", "playground_500m", "distance_nearest_sports_m"]].mean()}).round(2))

y = real.toilet_count
rows = []
for name in ("M0", "M1", "M2", "M3"):
    with_f, lab = MODELS[name]
    feats = features("v1", with_f)
    m = make_forest(0).fit(study[feats].to_numpy(), label(study, lab))
    ref = pd.Series(m.predict(real[feats].to_numpy()), index=ids)
    sets = {"real features": real}
    sets["proxy v1 + proxy F"] = proxy_v1.join(proxy_f[F]) if with_f else proxy_v1
    if with_f:
        sets["real v1 + proxy F"] = real.drop(columns=F).join(proxy_f[F])
        sets["proxy v1 + real F"] = proxy_v1.join(real[F])
    for sname, X in sets.items():
        p = pd.Series(m.predict(X[feats].to_numpy()), index=ids)
        top = p.nlargest(10).index
        rows.append(dict(model=name, features=sname, total=p.sum(),
                         spearman_vs_real=spearmanr(p, ref).statistic,
                         top10_overlap_with_real=len(set(top) & set(ref.nlargest(10).index)),
                         toilet_hexes_in_top10=int((y.loc[top] > 0).sum()), toilet_hexes=int((y > 0).sum()),
                         real_toilets=int(y.sum())))
r = pd.DataFrame(rows)
r.to_csv(OUT / "oran_proxy_check.csv", index=False)
print(r.round(3).to_string())
