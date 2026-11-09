"""Growth suburbs: train on all study hexes (v1 family), predict the 1,108 growth hexes. Also writes
growth predictions for the 3 council sites in growth hexes (used by council.py)."""
import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, mean_poisson_deviance

from common import MODELS, OUT, SEEDS, features, label, load_growth, load_study, make_forest

study, growth = load_study(), load_growth()
y_off = growth.toilet_count.to_numpy()
y_cor = label(growth, "public")
rows, preds = [], pd.DataFrame({"hex_id": growth.hex_id, "toilet_count": y_off, "label_osm": y_cor})


def score(y, p):
    p = np.clip(p, 1e-6, None)
    top = np.argsort(-p, kind="stable")[:100]
    return dict(pred_total=p.sum(), actual_total=int(y.sum()), toilet_hexes=int((y > 0).sum()),
                pr_auc=average_precision_score(y > 0, p), found_top100=int((y[top] > 0).sum()),
                deviance=mean_poisson_deviance(y, p), candidates=int(((p - y) >= 1).sum()))


for name, (with_f, lab) in MODELS.items():
    feats = features("v1", with_f)
    for seed in SEEDS:
        m = make_forest(seed).fit(study[feats].to_numpy(), label(study, lab))
        p = m.predict(growth[feats].to_numpy())
        preds[f"{name}_s{seed}"] = p
        for lname, y in (("official", y_off), ("osm_corrected", y_cor)):
            rows.append(dict(model=name, seed=seed, eval_label=lname, **score(y, p)))
        print(name, seed, round(p.sum(), 1), flush=True)
r = pd.DataFrame(rows)
r.to_csv(OUT / "growth_metrics_by_seed.csv", index=False)
preds.to_csv(OUT / "growth_predictions.csv", index=False)
agg = r.groupby(["eval_label", "model"]).agg(["mean", "min", "max"]).drop(columns="seed")
agg.to_csv(OUT / "growth_metrics.csv")
print(agg.round(3).to_string())
