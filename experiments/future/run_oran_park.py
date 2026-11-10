"""Sanity check: rebuild Oran Park's features from zoning only and compare with its real features/toilets."""
import sys

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

sys.path.insert(0, "/tmp/pigeon-eval/future")
from build import (V1, build_surface, density_table, features, hexes_from_ids, load_zoning,
                   projection_units, split_aero_mu, station_points)
from calibrate import scenario_densities, suburb_polygons
from fetch import overpass
from models import REPO, train
from predict import draw, label_hexes

OUT = "/tmp/pigeon-eval/future"
CONTEXT = (150.66, -34.06, 150.82, -33.94)
SUBURB = "Oran Park"


def main():
    models, _ = train()
    growth = pd.read_csv(REPO / "data/processed/sydney_growth_features.csv")
    study = set(pd.read_csv(REPO / "data/processed/sydney_extended_features.csv", usecols=["hex_id"]).hex_id)
    growth = growth[~growth.hex_id.isin(study)]
    sal = suburb_polygons()
    poly = sal[sal.sal_name_2021 == SUBURB].geometry.iloc[0]
    hexes = hexes_from_ids(growth.hex_id)
    hexes = hexes[hexes.geometry.centroid.within(poly)].reset_index(drop=True)
    real = growth.set_index("hex_id").loc[hexes.hex_id]
    print(len(hexes), "Oran Park hexes;", int(real.toilet_count.sum()), "real toilets in",
          int((real.toilet_count > 0).sum()), "hexes")

    q = ('[out:json][timeout:60];(nwr["railway"="station"](-34.06,150.66,-33.94,150.82);'
         'nwr["construction:railway"="station"](-34.06,150.66,-33.94,150.82););out center tags;')
    stations = station_points(overpass(q, "oran_stations"))
    zoning = split_aero_mu(load_zoning(CONTEXT, "zoning_oran"), stations.iloc[0:0])
    units = projection_units((150.60, -34.10, 150.90, -33.90), 2021)
    parks = zoning[zoning.role == "park"]
    labels = label_hexes(hexes, zoning, stations)
    cal = scenario_densities(pd.read_csv(f"{OUT}/calibration_by_suburb.csv"), exclude=(SUBURB,))

    rows, preds, feats = [], [], []
    real_pred = {m: pd.Series(model.predict(real[V1].to_numpy()), index=real.index) for m, model in models.items()}
    for m in models:
        rows.append(dict(scenario="real_features", model=m, total=real_pred[m].sum(), spearman_vs_real_features=1.0,
                         top10_overlap_with_real_features=10, real_toilet_hexes_in_top10=int(
                             (real.toilet_count.loc[real_pred[m].nlargest(10).index] > 0).sum())))
        preds.append(labels.assign(scenario="real_features", model=m, pred=real_pred[m],
                                   toilet_count=real.toilet_count).reset_index())
    feats.append(real[V1].assign(scenario="real_features").reset_index())
    for level in ("low", "mid", "high"):
        name = f"zoning_proxy|shops_{level}|bus_calibrated"
        surface = build_surface(zoning, units, density_table(cal, level), density_table(cal, "mid"))
        f = features(hexes, surface, stations, parks)
        feats.append(f.assign(scenario=name).reset_index())
        for m, model in models.items():
            pred = pd.Series(model.predict(f[V1].to_numpy()), index=f.index)
            rp = real_pred[m]
            rows.append(dict(scenario=name, model=m, total=pred.sum(),
                             spearman_vs_real_features=spearmanr(pred, rp.loc[pred.index]).statistic,
                             top10_overlap_with_real_features=len(set(pred.nlargest(10).index) & set(rp.nlargest(10).index)),
                             real_toilet_hexes_in_top10=int((real.toilet_count.loc[pred.nlargest(10).index] > 0).sum())))
            preds.append(labels.assign(scenario=name, model=m, pred=pred, toilet_count=real.toilet_count).reset_index())
            if level == "mid":
                draw(hexes, pred, zoning, stations, f"Oran Park {m}: zoning proxy (mid)\ntotal {pred.sum():.1f}",
                     f"{OUT}/map_oran_{m}_proxy_mid.png", vmax=1.5)
                draw(hexes, rp, zoning, stations, f"Oran Park {m}: real features\ntotal {rp.sum():.1f}",
                     f"{OUT}/map_oran_{m}_real.png", vmax=1.5)
    summary = pd.DataFrame(rows)
    summary["real_toilets"] = int(real.toilet_count.sum())
    summary.round(3).to_csv(f"{OUT}/oran_summary.csv", index=False)
    pd.concat(preds).to_csv(f"{OUT}/oran_predictions.csv", index=False)
    feats = pd.concat(feats)
    feats.to_csv(f"{OUT}/oran_features.csv", index=False)
    print(summary.round(3).to_string())
    print(feats.groupby("scenario")[["population_est", "shop_inside", "food_inside", "bus_stop_inside",
                                      "park_area_inside_m2", "train_station_inside"]].sum().round(0).to_string())
    print(real[real.toilet_count > 0][["toilet_count"]].join(labels).join(
        pd.DataFrame({m: s for m, s in real_pred.items()}).round(2)).to_string())


if __name__ == "__main__":
    main()
