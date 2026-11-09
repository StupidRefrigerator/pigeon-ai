"""Planned areas (Bradfield / Aerotropolis core; Leppington Town Centre): projected features per scenario, predictions.

Usage: run_aero.py [aero|leppington]
"""
import json
import sys

import geopandas as gpd
import numpy as np
import pandas as pd

sys.path.insert(0, "/tmp/pigeon-eval/future")
from build import (V1, build_surface, density_table, features, hex_grid, load_zoning,
                   projection_units, split_aero_mu, station_points)
from calibrate import scenario_densities
from models import REPO, train
from predict import draw, drivers, label_hexes

OUT = "/tmp/pigeon-eval/future"
AREAS = {
    # area bbox, zoning context bbox (covers every projection unit touching the area), population scenarios
    "aero": dict(area=(150.69, -33.945, 150.78, -33.83), context=(150.58, -34.06, 150.89, -33.76),
                 pops=("dphi2041", "masterplan2056")),
    "leppington": dict(area=(150.78, -33.975, 150.835, -33.935), context=(150.58, -34.10, 150.95, -33.76),
                       pops=("dphi2041",)),
}
METRO = ["Bradfield Station", "Airport Terminal", "Airport Business Park", "Luddenham Station", "Orchard Hills"]
BRADFIELD_RESIDENTS_2056 = 15288                   # Amended Social Infrastructure Strategy, p52-54
SITE_RADIUS_M = 600                                # ~114 ha Bradfield site as a circle round the station


def scenarios(pops):
    for pop in pops:
        for bus in ("none", "calibrated"):
            for level in ("low", "mid", "high"):
                yield f"{pop}|shops_{level}|bus_{bus}", pop, level, bus, "all"
    # Sensitivity: ENZ is mostly riparian corridor, not embellished park. Count only RE1/PRR as parks.
    yield f"{pops[0]}|shops_mid|bus_calibrated|parks_RE_only", pops[0], "mid", "calibrated", "re_only"


def main(key):
    cfg = AREAS[key]
    models, meta = train()
    stations = station_points(json.load(open(f"{OUT}/downloads/stations_raw.json")))
    metro = stations[stations.planned & stations.name.isin(METRO)]
    zoning = split_aero_mu(load_zoning(cfg["context"], "zoning_units" if key == "aero" else f"zoning_{key}"), metro)
    units = projection_units((150.60, -34.10, 150.90, -33.75), 2041)
    hexes = hex_grid(cfg["area"])
    parks = zoning[zoning.role == "park"]
    labels = label_hexes(hexes, zoning, stations)
    cal = scenario_densities(pd.read_csv(f"{OUT}/calibration_by_suburb.csv"),
                             exclude=("Leppington",) if key == "leppington" else ())
    bradfield = metro[metro.name == "Bradfield Station"].geometry.iloc[0]
    site = bradfield.buffer(SITE_RADIUS_M)

    feats, preds, tops = [], [], []
    for name, pop, level, bus, park_set in scenarios(cfg["pops"]):
        sf = density_table(cal, level)
        bt = density_table(cal, "mid" if bus == "calibrated" else "low")
        override = (site, BRADFIELD_RESIDENTS_2056) if pop == "masterplan2056" else None
        surface = build_surface(zoning, units, sf, bt, override)
        if key == "aero" and name == "dphi2041|shops_mid|bus_calibrated":
            inside = surface.intersection(site)
            print("DPHI 2041 residents on the Bradfield site circle:",
                  round(float((surface.pop_m2 * inside.area).sum())))
        f = features(hexes, surface, stations, parks if park_set == "all" else parks[parks.SYM_CODE != "ENZ"])
        feats.append(f.assign(scenario=name).reset_index())
        for mname, model in models.items():
            pred = pd.Series(model.predict(f[V1].to_numpy()), index=f.index)
            p = labels.join(pred.rename("pred")).assign(scenario=name, model=mname)
            p["p_any"] = 1 - np.exp(-p.pred)
            preds.append(p.reset_index())
            top = p.sort_values("pred", ascending=False).head(15).copy()
            top["drivers"], top["main_driver"] = drivers(model, f.loc[top.index, V1].to_numpy())
            tops.append(top.reset_index())
            if level == "mid" and bus == "calibrated" and park_set == "all":
                draw(hexes, pred, zoning, stations, f"{mname}: {name}\ntotal {pred.sum():.1f} predicted toilets",
                     f"{OUT}/map_{key}_{mname}_{pop}.png", vmax=1.5)

    today = pd.read_csv(REPO / "data/processed/sydney_all_features.csv").set_index("hex_id").reindex(hexes.hex_id)
    assert today[V1].notna().all().all(), "every area hex has committed present-day features"
    for mname, model in models.items():
        p = labels.join(pd.Series(model.predict(today[V1].to_numpy()), index=today.index).rename("pred"))
        p = p.assign(scenario="today_real_features", model=mname, p_any=lambda d: 1 - np.exp(-d.pred))
        preds.append(p.reset_index())
    print("real toilets today:", int(today.toilet_count.sum()))
    pd.concat(feats).to_csv(f"{OUT}/{key}_features.csv", index=False)
    preds = pd.concat(preds)
    preds.to_csv(f"{OUT}/{key}_predictions.csv", index=False)
    pd.concat(tops).to_csv(f"{OUT}/{key}_top15.csv", index=False)
    summary = preds.groupby(["scenario", "model"]).agg(
        total=("pred", "sum"), hexes_ge1=("pred", lambda s: int((s >= 1).sum())), max_hex=("pred", "max"),
        expected_hexes_with_toilet=("p_any", "sum")).round(2)
    base = summary.xs("today_real_features", level="scenario")["total"]
    summary["uplift_vs_today"] = (summary.total - summary.index.get_level_values("model").map(base)).round(2)
    summary.to_csv(f"{OUT}/{key}_summary.csv")
    print(summary.to_string())
    print(len(hexes), "hexes;", meta)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "aero")
