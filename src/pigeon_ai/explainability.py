"Getting all the evidence for an LLM call (should be in llm_explanations.py)"

import numpy as np
import pandas as pd


# Useful contextual features to include even when they are not among
# the strongest SHAP contributors. Missing columns are simply skipped.
CONTEXT_FEATURES = (
    "population_est",
    "population_250m",
    "population_500m",
    "shop_500m",
    "seifa_irsd_score",
)


def _clean_value(value):
    """Convert NumPy/Pandas values into ordinary Python values."""
    if pd.isna(value):
        return None

    if isinstance(value, np.generic):
        return value.item()

    return value


def build_candidate_evidence(
    recommendations,
    feature_data,
    shap_values,
    feature_names,
    top_k=5,
):
    """Build a compact evidence record for each recommended hexagon.

    Args:
        recommendations: DataFrame returned by recommended_list().
        feature_data: Original feature DataFrame (the df in model.run()).
        shap_values: SHAP array returned by cross_validate().
        feature_names: Feature names used to train the Random Forest.
        top_k: Number of strongest SHAP contributions to include.

    Returns:
        A list of dictionaries, one per recommendation.
    """
    if top_k < 1:
        raise ValueError("top_k must be at least 1")

    if "hex_id" not in recommendations or "hex_id" not in feature_data:
        raise ValueError("Both DataFrames must contain hex_id")

    if feature_data["hex_id"].duplicated().any():
        raise ValueError("feature_data contains duplicate hex_id values")

    shap_values = np.asarray(shap_values)
    feature_names = list(feature_names)

    expected_shape = (len(feature_data), len(feature_names))
    if shap_values.shape != expected_shape:
        raise ValueError(
            f"Expected SHAP shape {expected_shape}, got {shap_values.shape}"
        )

    missing_features = set(feature_names) - set(feature_data.columns)
    if missing_features:
        raise ValueError(
            f"Missing feature columns: {sorted(missing_features)}"
        )

    # Associate each SHAP row with its hexagon explicitly.
    shap_by_hex = pd.DataFrame(
        shap_values,
        columns=feature_names,
        index=feature_data["hex_id"],
    )

    features_by_hex = feature_data.set_index("hex_id")

    missing_hexes = (
        set(recommendations["hex_id"]) - set(features_by_hex.index)
    )
    if missing_hexes:
        raise ValueError(
            f"Recommendations contain unknown hex IDs: {len(missing_hexes)}"
        )

    # Include contextual features when available.
    context_columns = [
        col for col in CONTEXT_FEATURES
        if col in feature_data.columns
    ]

    evidence = []

    for _, recommendation in recommendations.iterrows():
        hex_id = recommendation["hex_id"]

        # Find this hexagon's original feature values and SHAP values.
        feature_row = features_by_hex.loc[hex_id]
        shap_row = shap_by_hex.loc[hex_id]

        # Sort features by absolute SHAP contribution.
        strongest = np.argsort(
            -np.abs(shap_row.to_numpy()),
            kind="stable",
        )[:top_k]

        drivers = []
        for index in strongest:
            name = feature_names[index]
            contribution = float(shap_row.iloc[index])

            drivers.append({
                "feature": name,
                "value": _clean_value(feature_row[name]),
                "shap_value": contribution,
                "effect": (
                    "increases prediction"
                    if contribution > 0
                    else "decreases prediction"
                    if contribution < 0
                    else "no effect"
                ),
            })

        record = {
            "hex_id": hex_id,
            "recommendation": {
                column: _clean_value(value)
                for column, value in recommendation.items()
            },
            "context": {
                column: _clean_value(feature_row[column])
                for column in context_columns
            },
            "model_drivers": drivers,
        }

        evidence.append(record)

    return evidence