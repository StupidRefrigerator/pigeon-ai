import json
import sys
from pathlib import Path

import h3
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pigeon_ai.prototype import ComparisonApp

TOWN_HALL = (-33.8732, 151.2069)
NEAR = h3.latlng_to_cell(*TOWN_HALL, 9)
FAR = h3.latlng_to_cell(-33.8140, 151.0010, 9)  # Parramatta, about 17 km away


@pytest.fixture
def web_dir(tmp_path):
    pd.DataFrame({"hex_id": [NEAR, FAR], "toilet_count": [1, 0], "fold": [0, 1],
                  "V1": [2.5, 3.0], "latest": [0.4, 1.0]}).to_csv(tmp_path / "predictions.csv", index=False)
    (tmp_path / "metrics.json").write_text(json.dumps({"source": "test", "models": {
        "V1": {"importance": []}, "latest": {"importance": []}}}))
    return tmp_path


def test_analyze_returns_the_files_predictions_gaps_and_candidates(web_dir):
    result = ComparisonApp(web_dir).analyze("Town Hall", 2)

    assert result["hexagons"] == 1 and result["actual_total"] == 1
    models = result["geojson"]["features"][0]["properties"]["models"]
    assert models["V1"] == {"predicted_count": 2.5, "gap": 1.5, "candidate": True}
    assert models["latest"] == {"predicted_count": 0.4, "gap": 0.0, "candidate": False}
    assert result["totals"]["V1"] == {"predicted": 2.5, "gap": 1.5, "candidates": 1}
    assert result["totals"]["latest"]["candidates"] == 0


def test_a_larger_radius_includes_the_far_hex(web_dir):
    result = ComparisonApp(web_dir).analyze("Town Hall", 30)

    assert result["hexagons"] == 2
    assert result["totals"]["V1"]["candidates"] == 2
    assert result["totals"]["latest"]["candidates"] == 1  # 1.0 predicted for an empty hex


def test_versions_come_from_the_metrics_file(web_dir):
    summary = ComparisonApp(web_dir).summary()

    assert [v["id"] for v in summary["versions"]] == ["V1", "latest"]
