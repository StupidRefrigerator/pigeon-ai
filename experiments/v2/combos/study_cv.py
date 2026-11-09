"""Held-out (5-fold GroupKFold on res-6 parents) predictions for every model variant and seed, `latest` family."""
import time

import pandas as pd

from common import MODELS, OUT, SEEDS, cross_validate, features, label, load_study

df = load_study()
preds = pd.DataFrame({"hex_id": df.hex_id})
for name, (with_f, lab) in MODELS.items():
    feats = features("latest", with_f)
    y = label(df, lab)
    df["_y"] = y
    for seed in SEEDS:
        t = time.time()
        p, fold, _ = cross_validate(df, feats, "_y", seed)
        preds[f"{name}_s{seed}"] = p
        print(name, seed, len(feats), "features", f"{time.time() - t:.0f}s", round(p.sum(), 1), flush=True)
preds["fold"] = fold
preds.to_csv(OUT / "study_oof_predictions.csv", index=False)
