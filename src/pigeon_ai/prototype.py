"""Full-data fits and local inference for the three-model prototype."""
from datetime import datetime, timezone
import difflib
import json
import pickle

import h3
import numpy as np
import sklearn
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline

from .experiments import EXPERIMENTS, load_experiment
from .model import MODEL_DIR, SEEDS, THRESHOLD, is_candidate, make_forest
from .paths import REFERENCE, ROOT

VERSIONS = ("V1", "V5", "V6")
FINAL_DIR = MODEL_DIR / "final"
WEB_DIR = ROOT / "web"


def train_final_models(out_dir=FINAL_DIR):
    """One full-data fit per experiment, with the existing forest settings."""
    out_dir.mkdir(parents=True, exist_ok=True)
    for version in VERSIONS:
        X, y = load_experiment(version)
        print(f"Fitting {version}: {len(X):,} rows, {len(X.columns)} predictors...", flush=True)
        pipeline = make_pipeline(SimpleImputer(strategy="median", keep_empty_features=True),
                                 make_forest(SEEDS[0]))
        pipeline.fit(X.to_numpy(), y.to_numpy())
        forest = pipeline.steps[-1][1]
        metadata = {
            "version": version, "target": "toilet_count", "features": list(X.columns),
            "dataset": EXPERIMENTS[version].get("dataset", "sydney_hex_features.csv"),
            "rows": len(X), "seed": SEEDS[0], "candidate_threshold": THRESHOLD,
            "trained_at": datetime.now(timezone.utc).isoformat(),
            "sklearn_version": sklearn.__version__, "preprocessing": "median imputation",
            "feature_importance": sorted(
                [{"feature": f, "importance": float(value)}
                 for f, value in zip(X.columns, forest.feature_importances_)],
                key=lambda row: -row["importance"]),
        }
        with (out_dir / f"{version}.pkl").open("wb") as file:
            pickle.dump(pipeline, file)
        (out_dir / f"{version}.json").write_text(json.dumps(metadata, indent=2) + "\n")
        print(f"Saved {version}.pkl and {version}.json", flush=True)


def resolve_place(query, places):
    """Match the local gazetteer; coordinates allow other points without geocoding."""
    query = query.strip()
    lookup = {name.casefold(): name for name in places}
    if query.casefold() in lookup:
        name = lookup[query.casefold()]
        return name, places[name]
    try:
        lat, lng = map(float, query.split(","))
        if np.isfinite([lat, lng]).all() and -34.6 <= lat <= -33.0 and 149.8 <= lng <= 151.7:
            return f"{lat:.5f}, {lng:.5f}", [lat, lng]
    except (ValueError, TypeError):
        pass
    similar = difflib.get_close_matches(query.casefold(), lookup, n=3, cutoff=0.5)
    hint = ", ".join(lookup[name] for name in similar)
    raise ValueError("Choose a Sydney suburb or listed landmark, or enter latitude, longitude."
                     + (f" Try: {hint}." if hint else ""))


def within_radius(centers, center, radius_km):
    """Great-circle distance from hex centers; keep whole H3 cells."""
    if not np.isfinite(radius_km) or not 0.1 <= radius_km <= 30:
        raise ValueError("Radius must be between 0.1 and 30 km.")
    points = np.radians(centers)
    lat, lng = np.radians(center)
    a = np.sin((points[:, 0] - lat) / 2) ** 2 + np.cos(lat) * np.cos(points[:, 0]) * np.sin((points[:, 1] - lng) / 2) ** 2
    distance = 6371.0088 * 2 * np.arcsin(np.sqrt(np.clip(a, 0, 1)))
    return distance <= radius_km


class ComparisonApp:
    def __init__(self, model_dir=FINAL_DIR):
        self.places = json.loads((REFERENCE / "sydney_places.json").read_text())["places"]
        self.evaluation = json.loads((WEB_DIR / "metrics.json").read_text())
        self.models, self.metadata, self.features = {}, {}, {}
        for version in VERSIONS:
            path = model_dir / f"{version}.json"
            if not path.exists() or not (model_dir / f"{version}.pkl").exists():
                raise FileNotFoundError("Saved models missing. Run python scripts/train_final_models.py first.")
            meta = json.loads(path.read_text())
            if meta["sklearn_version"] != sklearn.__version__:
                raise ValueError("scikit-learn version changed; retrain with python scripts/train_final_models.py")
            X, y = load_experiment(version)
            if meta["features"] != list(X.columns):
                raise ValueError(f"{version} predictors changed; retrain the final models.")
            # Only load pickle artifacts produced locally by train_final_models.py.
            with (model_dir / f"{version}.pkl").open("rb") as file:
                self.models[version] = pickle.load(file)
            self.metadata[version], self.features[version] = meta, X
            if version == "V1":
                self.ids, self.actual = X.index, y
            elif set(X.index) != set(self.ids) or not np.array_equal(y.loc[self.ids], self.actual):
                raise ValueError(f"{version} must match V1 hexagons and toilet labels.")
        self.centers = np.array([h3.cell_to_latlng(h) for h in self.ids])

    def summary(self):
        return {"versions": list(VERSIONS), "evaluation": self.evaluation,
                "places": list(self.places), "hexagons": len(self.ids),
                "importance": {v: self.metadata[v]["feature_importance"][:5] for v in VERSIONS}}

    def analyze(self, location, radius_km):
        name, center = resolve_place(location, self.places)
        selected = within_radius(self.centers, center, radius_km)
        ids = self.ids[selected]
        if not len(ids):
            raise ValueError("No study-area hexagons inside this circle. Try a larger radius or another Sydney location.")
        actual = self.actual.loc[ids].to_numpy()
        results, totals = {}, {}
        for version in VERSIONS:
            X = self.features[version].loc[ids, self.metadata[version]["features"]]
            pred = self.models[version].predict(X.to_numpy())
            gap = np.maximum(0, pred - actual)
            candidates = is_candidate(pred, actual)
            results[version] = {h: {"predicted_count": float(p), "gap": float(g), "candidate": bool(c)}
                                for h, p, g, c in zip(ids, pred, gap, candidates)}
            totals[version] = {"predicted": float(pred.sum()), "gap": float(gap.sum()),
                               "candidates": int(candidates.sum())}
        features = []
        for hex_id, count in zip(ids, actual):
            ring = [[lng, lat] for lat, lng in h3.cell_to_boundary(hex_id)]
            ring.append(ring[0])
            features.append({"type": "Feature", "geometry": {"type": "Polygon", "coordinates": [ring]},
                             "properties": {"hex_id": hex_id, "actual_count": int(count),
                                            "models": {v: results[v][hex_id] for v in VERSIONS}}})
        return {"location": name, "center": center, "radius_km": radius_km,
                "hexagons": len(ids), "actual_total": int(actual.sum()), "totals": totals,
                "geojson": {"type": "FeatureCollection", "features": features}}
