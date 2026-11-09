"""Joins classifications with model outputs; writes candidates_classified.csv, calibration_check.csv and report tables."""
import os, sys
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from targets import load_targets, OUT
from classify import PRECEDENCE

VALIDISH = ["toilet_already_mapped_public", "toilet_customers_or_private", "shopping_centre", "public_destination", "commercial_street"]


def rates(df, col="category"):
    c = df[col].value_counts().reindex(PRECEDENCE, fill_value=0)
    return c, (c / max(len(df), 1))


def table(groups, col="category"):
    out = {}
    for name, df in groups.items():
        c, _ = rates(df, col)
        out[name] = [f"{n} ({n / max(len(df), 1):.0%})" for n in c]
    t = pd.DataFrame(out, index=PRECEDENCE)
    t.loc["n"] = [str(len(d)) for d in groups.values()]
    return t


def md(df, index=True):
    return df.to_markdown(index=index)


def main():
    t, _ = load_targets()
    cls = pd.read_csv(f"{OUT}/hex_osm_classified.csv")
    cand = t[t.group == "candidate"].drop(columns="group").merge(cls.drop(columns=["lat", "lng"]), on="hex_id")
    cand["baseline_gap"] = cand.baseline_pred - cand.toilet_count
    cand["ga_gap"] = cand.good_areas_pred - cand.toilet_count
    cand["baseline_rank"] = cand.baseline_gap.where(cand.baseline_candidate).rank(ascending=False, method="first")
    cand["ga_rank"] = cand.ga_gap.where(cand.ga_candidate).rank(ascending=False, method="first")
    cand["membership"] = np.select([cand.baseline_candidate & cand.ga_candidate, cand.baseline_candidate], ["both", "baseline_only"], "good_areas_only")
    for c in ("mall", "department_store", "destination_names", "nearest_suburb"):
        cand[c] = cand[c].fillna("").astype(str)
    cand["place_name"] = np.where(cand.mall.str.len() > 0, cand.mall,
                         np.where(cand.destination_names.str.len() > 0, cand.destination_names.str.split(", ").str[0], cand.department_store))
    # Interprets the OSM toilet signal per candidate kind: in a shortfall hex the OSM toilet is probably the mapped one.
    cand["osm_extra_public_toilets"] = (cand.osm_public_toilets_in_hex - cand.toilet_count).clip(lower=0)
    cand["toilet_not_on_map"] = cand.osm_extra_public_toilets > 0
    cand["suburb"] = cand.nearest_suburb.fillna("")
    cand = cand.sort_values(["ga_rank", "baseline_rank"])
    cand.to_csv(f"{OUT}/candidates_classified.csv", index=False)

    cal = t[t.group.str.startswith("cal_")].merge(cls[["hex_id", "category", "category_site_only"]], on="hex_id")
    rows = []
    for g, df in cal.groupby("group"):
        for col in ("category", "category_site_only"):
            c, s = rates(df, col)
            for cat in PRECEDENCE:
                rows.append({"group": g, "classifier": "full" if col == "category" else "site_only_ignoring_osm_toilets",
                             "category": cat, "n": int(c[cat]), "share": round(float(s[cat]), 3), "group_n": len(df)})
    calc = pd.DataFrame(rows)
    calc.to_csv(f"{OUT}/calibration_check.csv", index=False)

    groups_cal = {g: df for g, df in cal.groupby("group")}
    groups_cand = {
        "baseline (all)": cand[cand.baseline_candidate],
        "good-areas (all)": cand[cand.ga_candidate],
        "both models": cand[cand.membership == "both"],
        "good-areas only": cand[cand.membership == "good_areas_only"],
        "baseline only": cand[cand.membership == "baseline_only"],
        "baseline shortfall": cand[cand.baseline_candidate & (cand.baseline_kind == "shortfall")],
        "good-areas shortfall": cand[cand.ga_candidate & (cand.ga_kind == "shortfall")],
        "good-areas top 50": cand[cand.ga_rank <= 50],
        "baseline top 50": cand[cand.baseline_rank <= 50],
    }

    def top(rankcol, predcol, gapcol):
        d = cand[cand[rankcol] <= 20].sort_values(rankcol)
        return d.assign(lat=d.lat.round(5), lng=d.lng.round(5), pred=d[predcol].round(2), gap=d[gapcol].round(2))[
            [rankcol, "lat", "lng", "suburb", "place_name", "toilet_count", "pred", "gap", "category", "destination_tier", "evidence"]].rename(columns={rankcol: "rank"})

    def signals(groups):
        out = {}
        for name, d in groups.items():
            sd = d.strong_destinations.fillna("").astype(str).str.len() > 0
            shop = d.category_site_only == "shopping_centre"
            extra = (d.osm_public_toilets_in_hex - d.toilet_count).clip(lower=0) > 0
            out[name] = {
                "n": len(d),
                "OSM public toilet in hex": f"{(d.osm_public_toilets_in_hex > 0).mean():.0%}",
                "OSM public toilets > map count (toilet_not_on_map)": f"{extra.mean():.0%}",
                "...of which access tag missing only": f"{(extra & d.osm_public_toilet_access_missing_only).mean():.0%}",
                "OSM customers/private toilet in hex": f"{(d.osm_customer_private_toilets_in_hex > 0).mean():.0%}",
                "site: shopping centre": f"{shop.mean():.0%}",
                "site: strong destination (station, beach, 1ha+ park, library, ped. street...)": f"{sd.mean():.0%}",
                "site: shopping OR strong destination": f"{(shop | sd).mean():.0%}",
                "site: weak destination only (playground, pitch, small park)": f"{((d.category_site_only == 'public_destination') & ~sd).mean():.0%}",
                "site: residential/industrial/unknown": f"{d.category_site_only.isin(['residential_or_industrial_only', 'unknown']).mean():.0%}",
                "median shops+food in hex": f"{d.shops_food_in_hex.median():.0f}",
            }
        return pd.DataFrame(out)

    calx = t[t.group.str.startswith("cal_")].merge(cls, on="hex_id")
    sig_cal = signals({g: d for g, d in calx.groupby("group")})
    sig_cand = signals(groups_cand)
    sig_cal.to_csv(f"{OUT}/calibration_signals.csv")
    sig_cand.to_csv(f"{OUT}/candidate_signals.csv")
    with open(f"{OUT}/tables.md", "w") as f:
        f.write("## Signals: calibration groups\n\n" + md(sig_cal) + "\n\n")
        f.write("## Signals: candidate groups\n\n" + md(sig_cand) + "\n\n")
        f.write("## Calibration (full classifier)\n\n" + md(table(groups_cal)) + "\n\n")
        f.write("## Calibration (site-only, OSM toilets ignored)\n\n" + md(table(groups_cal, "category_site_only")) + "\n\n")
        f.write("## Candidates (full classifier)\n\n" + md(table(groups_cand)) + "\n\n")
        f.write("## Candidates (site-only)\n\n" + md(table(groups_cand, "category_site_only")) + "\n\n")
        f.write("## Baseline top 20\n\n" + md(top("baseline_rank", "baseline_pred", "baseline_gap"), index=False) + "\n\n")
        f.write("## Good-areas top 20\n\n" + md(top("ga_rank", "good_areas_pred", "ga_gap"), index=False) + "\n\n")
        sf = cand[cand.baseline_candidate & (cand.baseline_kind == "shortfall")]
        f.write("## Baseline shortfall\n\n" + md(sf[["lat", "lng", "suburb", "place_name", "toilet_count", "baseline_pred", "category", "evidence"]].round(3), index=False) + "\n")
    print(open(f"{OUT}/tables.md").read())


if __name__ == "__main__":
    main()
