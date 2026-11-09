"""Baseline and good-areas forests (make_forest(0), v1 features), trained once and cached."""
import sys
from pathlib import Path

import h3
import joblib
import pandas as pd

REPO = Path("/Users/summitsetia/Desktop/University/26T3/PIGEON-AI-DATASET")
sys.path.insert(0, str(REPO / "src"))
from pigeon_ai.model import DATA_FILE, TARGETS, make_forest  # noqa: E402

V1 = TARGETS["toilets"].feature_sets["v1"]
LABEL = TARGETS["toilets"].label
CACHE = Path("/tmp/pigeon-eval/future/models.joblib")


def train():
    if CACHE.exists():
        return joblib.load(CACHE)
    df = pd.read_csv(DATA_FILE)
    assert len(df) == 16228 and len(V1) == 19
    good = set(pd.read_csv(REPO / "data/model/good_areas/good_blocks.csv").block)
    assert len(good) == 20
    in_good = df.hex_id.map(lambda h: h3.cell_to_parent(h, 6) in good)
    models = {
        "baseline": make_forest(0).fit(df[V1].to_numpy(), df[LABEL].to_numpy()),
        "good_areas": make_forest(0).fit(df.loc[in_good, V1].to_numpy(), df.loc[in_good, LABEL].to_numpy()),
    }
    meta = {"n_train": {"baseline": len(df), "good_areas": int(in_good.sum())},
            "toilets_train": {"baseline": int(df[LABEL].sum()), "good_areas": int(df.loc[in_good, LABEL].sum())}}
    joblib.dump((models, meta), CACHE)
    return models, meta


if __name__ == "__main__":
    models, meta = train()
    print(meta)
