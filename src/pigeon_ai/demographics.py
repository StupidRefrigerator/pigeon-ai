"""V7: area-allocated Census counts and population-weighted SA1 IRSD."""

import geopandas as gpd
import numpy as np
import pandas as pd

from .paths import RAW
from .population import select_population_context

AGE_GROUPS = {
    "age_0_17": [f"Age_yr_{age}_P" for age in range(18)],
    "age_18_25": [f"Age_yr_{age}_P" for age in range(18, 26)],
    "age_26_64": [f"Age_yr_{age}_P" for age in range(26, 65)],
    "age_65plus": [f"Age_yr_{age}_P" for age in range(65, 80)] + [
        "Age_yr_80_84_P", "Age_yr_85_89_P", "Age_yr_90_94_P",
        "Age_yr_95_99_P", "Age_yr_100_yr_over_P",
    ],
}
AGE_FEATURES = [f"{group}_pct" for group in AGE_GROUPS]
DEMOGRAPHIC_FEATURES = AGE_FEATURES + ["households_total", "seifa_irsd_score"]


def load_sa1_demographics():
    folder = RAW / "census_2021/2021 Census GCP Statistical Area 1 for NSW"
    age_tables = [
        pd.read_csv(
            folder / f"2021Census_G04{part}_NSW_SA1.csv",
            dtype={"SA1_CODE_2021": str},
        ).set_index("SA1_CODE_2021", verify_integrity=True)
        for part in ("A", "B")
    ]
    if not age_tables[0].index.equals(age_tables[1].index):
        raise ValueError("G04A and G04B SA1 IDs/order differ")
    ages = pd.concat(age_tables, axis=1, verify_integrity=True)
    counts = pd.DataFrame({
        group: ages[columns].sum(axis=1, min_count=len(columns))
        for group, columns in AGE_GROUPS.items()
    })
    households = pd.read_csv(
        folder / "2021Census_G35_NSW_SA1.csv",
        dtype={"SA1_CODE_2021": str},
    ).set_index("SA1_CODE_2021", verify_integrity=True)
    counts["households_total"] = households["Total_Total"]

    with pd.ExcelFile(RAW / "SEIFA_2021_SA1.xlsx", engine="openpyxl") as workbook:
        scores = pd.read_excel(workbook, sheet_name="Table 2", skiprows=5, usecols="A,C", dtype=str)
        excluded = pd.read_excel(workbook, sheet_name="Table 6", skiprows=5, usecols="A,C", dtype=str)
    code_column = "2021 Statistical Area Level 1 (SA1)"
    # Ignore explanatory/footer rows, retaining the native 11-digit 2021 codes.
    scores = scores[scores[code_column].str.fullmatch(r"\d{11}", na=False)]
    scores = scores.set_index(code_column, verify_integrity=True)
    numeric_scores = pd.to_numeric(scores["Score"], errors="raise")
    if not np.isfinite(numeric_scores).all() or not numeric_scores.gt(0).all():
        raise ValueError("Invalid score in SEIFA Table 2 IRSD Score column")
    excluded_ids = set(excluded.loc[excluded["IRSD"].eq("Y"), code_column])
    counts["seifa_irsd_score"] = numeric_scores
    counts["irsd_excluded"] = counts.index.isin(excluded_ids)
    return counts


def calculate_demographics(grid, boundaries, source):
    """Preserve undefined values as NaN; never infer or impute demographics."""
    context = select_population_context(boundaries, grid.geometry.union_all())
    if not context["sa1_code"].isin(source.index).all():
        raise ValueError("Census source is missing contextual 2021 SA1 identifiers")
    context = context.merge(source, left_on="sa1_code", right_index=True, validate="one_to_one")
    count_columns = list(AGE_GROUPS) + ["households_total"]
    values = context[count_columns].to_numpy()
    if not np.isfinite(values).all() or (values < 0).any():
        raise ValueError("Missing/invalid Census age or household counts")
    missing_score = context["seifa_irsd_score"].isna()
    if (missing_score & ~context["irsd_excluded"]).any():
        raise ValueError("Missing IRSD source is not explained by ABS Table 6 exclusions")

    overlap = gpd.overlay(
        grid[["hex_id", "geometry"]], context, how="intersection", keep_geom_type=True,
    )
    fraction = overlap.geometry.area / overlap["sa1_area_m2"]
    allocated = (
        overlap[count_columns].mul(fraction, axis=0)
        .groupby(overlap["hex_id"]).sum(min_count=1)
        .reindex(grid["hex_id"])
    )
    # No overlapping SA1 is a source-coverage problem, not an observed zero.
    if allocated.isna().any().any():
        raise ValueError("A hexagon has no complete Census allocation")
    weights = overlap["population"] * fraction
    population = weights.groupby(overlap["hex_id"]).sum().reindex(grid["hex_id"])
    age_total = allocated[list(AGE_GROUPS)].sum(axis=1)
    defined_age = population.gt(0) & age_total.gt(0)
    result = allocated[list(AGE_GROUPS)].div(age_total.where(defined_age), axis=0) * 100
    result.columns = AGE_FEATURES
    result["households_total"] = allocated["households_total"]

    unscored_population = (
        weights.where(overlap["seifa_irsd_score"].isna(), 0)
        .groupby(overlap["hex_id"]).sum().reindex(grid["hex_id"])
    )
    numerator = (
        (weights * overlap["seifa_irsd_score"])
        .groupby(overlap["hex_id"]).sum(min_count=1).reindex(grid["hex_id"])
    )
    # A missing score for even part of the resident weight makes IRSD undefined.
    # Missing scores attached only to zero resident weight do not affect it.
    defined_irsd = population.gt(0) & unscored_population.eq(0)
    result["seifa_irsd_score"] = numerator / population.where(defined_irsd)

    if "population_est" in grid:
        np.testing.assert_allclose(population, grid["population_est"], rtol=1e-10, atol=1e-6)
    np.testing.assert_allclose(result.loc[defined_age, AGE_FEATURES].sum(axis=1), 100, atol=1e-10)
    observed_ages = result[AGE_FEATURES].dropna()
    assert observed_ages.ge(0).all().all() and observed_ages.le(100).all().all()
    assert not np.isinf(result.to_numpy()).any()
    observed_scores = result["seifa_irsd_score"].dropna()
    assert observed_scores.between(context.seifa_irsd_score.min(), context.seifa_irsd_score.max()).all()
    report = {
        "zero_population": int(population.eq(0).sum()),
        "undefined_ages": int((~defined_age).sum()),
        "positive_population_without_age_counts": int((population.gt(0) & age_total.eq(0)).sum()),
        "resident_weight_from_unscored_SA1": int(unscored_population.gt(0).sum()),
        "undefined_irsd": int((~defined_irsd).sum()),
        "any_undefined_demographic": int(result.isna().any(axis=1).sum()),
    }
    return result[DEMOGRAPHIC_FEATURES], report
