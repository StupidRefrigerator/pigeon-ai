"""V8: Census-scaled scenarios using the 2024 NSW projection release."""
import geopandas as gpd
import numpy as np
import pandas as pd

from .paths import RAW
from .population import select_population_context

PROJECTION_FEATURES = [
    "population_projected_2031", "population_projected_2041",
    "population_growth_2021_2031", "population_growth_pct_2021_2031",
]
PROJECTION_PATH = RAW / "population_projections/2024-nsw-population-projections-sa2s.xlsx"


def load_projection_tables():
    with pd.ExcelFile(PROJECTION_PATH, engine="openpyxl") as workbook:
        totals = pd.read_excel(workbook, "Total population", header=6)
        collapsed = pd.read_excel(workbook, "Collapsed SA2s", header=6)
    return totals[["SA2", 2021, 2031, 2041]], collapsed[["SA2_NAME_2021", "Collapsed SA2"]]


def map_projection_units(native, totals, collapsed):
    """Strict exact-name crosswalk for all spatial NSW 2021 SA2s."""
    native = native[["SA2_CODE21", "SA2_NAME21"]].drop_duplicates().copy()
    totals, collapsed = totals.copy(), collapsed.copy()
    for frame, columns in (
        (native, ["SA2_NAME21"]), (totals, ["SA2"]),
        (collapsed, ["SA2_NAME_2021", "Collapsed SA2"]),
    ):
        for column in columns:
            if not frame[column].map(lambda name: isinstance(name, str) and bool(name.strip())).all():
                raise ValueError(f"Missing/invalid geographic name in {column}")
            frame[column] = frame[column].str.strip()
    if native.SA2_CODE21.isna().any() or native.SA2_CODE21.duplicated().any() or native.SA2_NAME21.duplicated().any():
        raise ValueError("Ambiguous native SA2 code/name correspondence")
    if totals.SA2.duplicated().any():
        raise ValueError("Duplicate projection-unit workbook rows")
    if collapsed.SA2_NAME_2021.duplicated().any():
        raise ValueError("Duplicate or ambiguous collapsed-SA2 membership")
    if not set(collapsed.SA2_NAME_2021) <= set(native.SA2_NAME21):
        raise ValueError("Collapsed-SA2 member names do not match native 2021 geography")
    if not set(collapsed["Collapsed SA2"]) <= set(totals.SA2):
        raise ValueError("Collapsed projection unit has no workbook row")
    ambiguous = collapsed.SA2_NAME_2021.isin(totals.SA2) & collapsed.SA2_NAME_2021.ne(collapsed["Collapsed SA2"])
    if ambiguous.any():
        raise ValueError("Ambiguous name: native SA2 has both standalone and collapsed projections")
    membership = collapsed.set_index("SA2_NAME_2021")["Collapsed SA2"]
    native["projection_unit"] = native.SA2_NAME21.map(membership).fillna(native.SA2_NAME21)
    missing = sorted(set(native.projection_unit) - set(totals.SA2))
    if missing:
        raise ValueError(f"Native SA2s lack a projection row: {missing}")
    if set(totals.SA2) - set(native.projection_unit):
        raise ValueError("Workbook projection rows do not map to native NSW geography")
    for year in (2021, 2031, 2041):
        totals[year] = pd.to_numeric(totals[year], errors="raise")
        if not np.isfinite(totals[year]).all() or totals[year].lt(0).any():
            raise ValueError(f"Missing, negative or infinite population for {year}")
    if totals[2021].eq(0).any():
        raise ValueError("Zero projection-unit 2021 baseline: growth ratios are undefined")
    # Repeated units are intentional; the workbook side must have exactly one row.
    return native.merge(totals, left_on="projection_unit", right_on="SA2", validate="many_to_one")


def calculate_projections(grid, boundaries, mapping):
    context = select_population_context(boundaries, grid.geometry.union_all())
    context = context.merge(
        mapping[["SA2_CODE21", "projection_unit", 2021, 2031, 2041]],
        on="SA2_CODE21", how="left", validate="many_to_one",
    )
    if context[["projection_unit", 2021, 2031, 2041]].isna().any().any():
        raise ValueError("Study-area SA1s lack a valid projection mapping")
    overlap = gpd.overlay(
        grid[["hex_id", "geometry"]], context, how="intersection", keep_geom_type=True,
    )
    overlap = overlap[overlap.geometry.area.gt(0)].copy()
    contribution = overlap.population * overlap.geometry.area / overlap.sa1_area_m2
    allocated = contribution.groupby(overlap.hex_id).sum().reindex(grid.hex_id)
    if allocated.isna().any():
        raise ValueError("Hexagon has no SA1/projection coverage")
    baseline = pd.Series(grid.population_est.to_numpy(), index=pd.Index(grid.hex_id, name="hex_id"))
    np.testing.assert_allclose(allocated, baseline, rtol=1e-10, atol=1e-6)
    result = pd.DataFrame(index=baseline.index)
    for year in (2031, 2041):
        scaled = contribution * overlap[year] / overlap[2021]
        result[f"population_projected_{year}"] = scaled.groupby(overlap.hex_id).sum().reindex(baseline.index)
        result.loc[baseline.eq(0), f"population_projected_{year}"] = 0.0
    result["population_growth_2021_2031"] = result.population_projected_2031 - baseline
    result["population_growth_pct_2021_2031"] = result.population_growth_2021_2031 / baseline.where(baseline.gt(0)) * 100
    assert np.isfinite(result.iloc[:, :3].to_numpy()).all()
    assert result.iloc[:, :2].ge(0).all().all()
    assert result.iloc[:, 3].isna().equals(baseline.eq(0))
    assert np.isfinite(result.loc[baseline.gt(0)].to_numpy()).all()
    report = {
        "mapped_native_SA2s": len(mapping),
        "workbook_projection_units": mapping.projection_unit.nunique(),
        "study_native_SA2s": context.SA2_CODE21.nunique(),
        "study_projection_units": context.projection_unit.nunique(),
        "covered_hexagons": overlap.hex_id.nunique(),
        "crossing_native_SA2s": int(overlap.groupby("hex_id").SA2_CODE21.nunique().gt(1).sum()),
        "crossing_projection_units": int(overlap.groupby("hex_id").projection_unit.nunique().gt(1).sum()),
        "zero_baseline_hexagons": int(baseline.eq(0).sum()),
    }
    return result[PROJECTION_FEATURES], report
