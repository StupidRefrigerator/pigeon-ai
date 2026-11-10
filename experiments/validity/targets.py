"""Builds the set of hexes to classify: union candidates plus calibration samples. Deterministic (seed 0)."""
import numpy as np, pandas as pd, h3

REPO = "/Users/summitsetia/Desktop/University/26T3/PIGEON-AI-DATASET"
OUT = "/tmp/pigeon-eval/validity"
SEED = 0
N_CAL = 300
LOW_PRED = 0.1


def load_targets():
    base = pd.read_csv(f"{REPO}/data/model/hex_predictions.csv")
    ga = pd.read_csv(f"{REPO}/data/model/good_areas/hex_predictions.csv")
    df = base[["hex_id", "toilet_count", "predicted_toilets", "is_candidate", "kind", "top_drivers"]].rename(
        columns={"predicted_toilets": "baseline_pred", "is_candidate": "baseline_candidate", "kind": "baseline_kind",
                 "top_drivers": "baseline_drivers"}).merge(
        ga[["hex_id", "good_areas_pred", "is_candidate", "kind", "in_good_block", "top_drivers"]].rename(
            columns={"is_candidate": "ga_candidate", "kind": "ga_kind", "top_drivers": "ga_drivers"}), on="hex_id")
    rng = np.random.default_rng(SEED)
    toilet = df[df.toilet_count > 0]
    neg_low = df[(df.toilet_count == 0) & (df.baseline_pred < LOW_PRED) & (df.good_areas_pred < LOW_PRED)]
    neg_mid = df[(df.toilet_count == 0) & (df.baseline_pred.between(0.5, 1.0)) & (~df.baseline_candidate) & (~df.ga_candidate)]
    groups = {
        "candidate": df[df.baseline_candidate | df.ga_candidate].hex_id,
        "cal_toilet": toilet.hex_id.iloc[rng.choice(len(toilet), N_CAL, replace=False)],
        "cal_no_toilet_low_pred": neg_low.hex_id.iloc[rng.choice(len(neg_low), N_CAL, replace=False)],
        "cal_no_toilet_mid_pred": neg_mid.hex_id.iloc[rng.choice(len(neg_mid), min(N_CAL, len(neg_mid)), replace=False)],
    }
    rows = [{"hex_id": h, "group": g} for g, hs in groups.items() for h in hs]
    t = pd.DataFrame(rows).merge(df, on="hex_id")
    ll = t.hex_id.map(h3.cell_to_latlng)
    t["lat"] = [a for a, _ in ll]
    t["lng"] = [b for _, b in ll]
    return t, df
