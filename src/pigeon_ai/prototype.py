"""Local inference for the model comparison page, from saved held-out predictions."""
import difflib
import json

import h3
import numpy as np
import pandas as pd

from .model import is_candidate
from .paths import REFERENCE, ROOT

WEB_DIR = ROOT / "web"
MODELS = {
    "V1": "V1 — Baseline",
    "V5": "V5 — 1 km features",
    "V6": "V6 — Accessibility",
    "latest": "Latest — V5 + V6 (production)",
}


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
    """Serves web/predictions.csv. Run scripts/build_comparison_page.py to rebuild it."""

    def __init__(self, web_dir=WEB_DIR):
        self.places = json.loads((REFERENCE / "sydney_places.json").read_text())["places"]
        self.evaluation = json.loads((web_dir / "metrics.json").read_text())
        predictions = pd.read_csv(web_dir / "predictions.csv").set_index("hex_id")
        self.versions = list(self.evaluation["models"])
        self.ids = predictions.index
        self.actual = predictions["toilet_count"].to_numpy()
        self.predicted = {v: predictions[v].to_numpy() for v in self.versions}
        self.centers = np.array([h3.cell_to_latlng(h) for h in self.ids])

    def summary(self):
        return {"versions": [{"id": v, "label": MODELS.get(v, v)} for v in self.versions],
                "evaluation": self.evaluation, "places": list(self.places),
                "hexagons": len(self.ids),
                "importance": {v: m["importance"] for v, m in self.evaluation["models"].items()}}

    def analyze(self, location, radius_km):
        name, center = resolve_place(location, self.places)
        selected = within_radius(self.centers, center, radius_km)
        ids = self.ids[selected]
        if not len(ids):
            raise ValueError("No study-area hexagons inside this circle. Try a larger radius or another Sydney location.")
        actual = self.actual[selected]
        results, totals = {}, {}
        for version in self.versions:
            pred = self.predicted[version][selected]
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
                                            "models": {v: results[v][hex_id] for v in self.versions}}})
        return {"location": name, "center": center, "radius_km": radius_km,
                "hexagons": len(ids), "actual_total": int(actual.sum()), "totals": totals,
                "geojson": {"type": "FeatureCollection", "features": features}}
