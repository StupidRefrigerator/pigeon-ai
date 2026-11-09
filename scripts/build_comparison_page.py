#!/usr/bin/env python3
"""Compute held-out predictions for the comparison page and write web/predictions.csv and web/metrics.json."""
from pathlib import Path
import json
import sys

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pigeon_ai.comparison import held_out_predictions, load_model_data
from pigeon_ai.model import metrics_row
from pigeon_ai.paths import WEB as WEB_DIR

MODELS = ["V1", "V5", "V6", "latest"]  # page labels are in web/analyze.js

SEED = 0
SOURCE = ("Held-out 5-fold res-6 spatial cross-validation, seed 0. Each hex is predicted by a "
          "forest that never saw its res-6 block.")

if __name__ == "__main__":
    predictions, metrics = None, {}
    for name in MODELS:
        X, y = load_model_data(name)
        print(f"{name}: {len(X):,} hexes, {len(X.columns)} features", flush=True)
        frame = held_out_predictions(X, y, SEED, with_shap=True)
        if predictions is None:
            predictions = frame[["toilet_count", "fold"]].copy()
        elif not predictions.index.equals(frame.index):
            sys.exit(f"{name} must cover the same hexes as the first model.")
        predictions[name] = frame["predicted_toilets"].round(4)
        shown = predictions[name].to_numpy()  # score what the page shows
        row = metrics_row(name, frame["toilet_count"].to_numpy(), shown, shown)
        shap_mean = frame.attrs["mean_abs_shap"]
        total = sum(shap_mean.values())
        top = sorted(shap_mean.items(), key=lambda item: -item[1])[:5]
        metrics[name] = {
            "deviance": row["deviance"], "pr_auc": row["pr_auc"],
            "top100_hits": int(row["top100_hits"]), "candidates": int(row["candidates"]),
            "importance": [{"feature": f, "importance": float(v / total)} for f, v in top]}
    predictions.to_csv(WEB_DIR / "predictions.csv", index_label="hex_id")
    (WEB_DIR / "metrics.json").write_text(
        json.dumps({"source": SOURCE, "models": metrics}, indent=2) + "\n")
    print(pd.DataFrame(metrics).T.drop(columns="importance").to_string())
