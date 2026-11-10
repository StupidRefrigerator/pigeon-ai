"""Write new_features_{study,growth,future}.csv, osm_toilets.csv and checks.json."""
import json

import pandas as pd

from features import build, toilet_points
from hexsets import OUT, grid, hex_ids
from osm_layers import layers


def main():
    L = layers()
    toilets = toilet_points(L["toilets"])
    toilets[["lat", "lng", "access", "fee", "name", "operator", "osm_type", "osm_id", "hex_id",
             "is_public", "is_public_tagged", "is_private"]].to_csv(f"{OUT}/osm_toilets.csv", index=False)

    study, growth_ids, future = hex_ids()
    all_ids = sorted(set(study.hex_id) | set(growth_ids) | set(future.hex_id))
    feats = build(grid(all_ids), L, toilets).set_index("hex_id")

    s = feats.loc[study.hex_id].reset_index()
    s.to_csv(f"{OUT}/new_features_study.csv", index=False)
    feats.loc[growth_ids].reset_index().to_csv(f"{OUT}/new_features_growth.csv", index=False)
    f = feats.loc[future.hex_id].reset_index()
    f.insert(1, "area", future.area.values)
    f.to_csv(f"{OUT}/new_features_future.csv", index=False)

    lab = s.merge(study, on="hex_id")
    cols = [c for c in s.columns if c != "hex_id"]
    checks = {
        "layer_sizes": {k: int(len(v)) for k, v in L.items()},
        "toilet_access_values": toilets["access"].fillna("<missing>").value_counts().to_dict(),
        "toilets_total": int(len(toilets)),
        "toilets_public": int(toilets.is_public.sum()),
        "toilets_public_tagged": int(toilets.is_public_tagged.sum()),
        "toilets_private": int(toilets.is_private.sum()),
        "toilets_other_access": int((~toilets.is_public & ~toilets.is_private).sum()),
        "study_official_toilets": int(lab.toilet_count.sum()),
        "study_hexes_with_official": int((lab.toilet_count > 0).sum()),
        "study_osm_public_total": int(lab.osm_toilets_public.sum()),
        "study_hexes_with_osm_public": int((lab.osm_toilets_public > 0).sum()),
        "study_osm_public_tagged_total": int(lab.osm_toilets_public_tagged.sum()),
        "study_osm_private_total": int(lab.osm_toilets_private.sum()),
        "study_hexes_osm_public_but_official_0": int(((lab.osm_toilets_public > 0) & (lab.toilet_count == 0)).sum()),
        "study_hexes_osm_public_tagged_but_official_0": int(((lab.osm_toilets_public_tagged > 0) & (lab.toilet_count == 0)).sum()),
        "study_hexes_official_but_osm_public_0": int(((lab.osm_toilets_public == 0) & (lab.toilet_count > 0)).sum()),
        "study_hexes_both": int(((lab.osm_toilets_public > 0) & (lab.toilet_count > 0)).sum()),
        "pearson_with_toilet_count": lab[cols].corrwith(lab.toilet_count).round(4).to_dict(),
        "spearman_with_toilet_count": lab[cols].corrwith(lab.toilet_count, method="spearman").round(4).to_dict(),
        "rows": {"study": len(s), "growth": len(growth_ids), "future": len(f)},
    }
    json.dump(checks, open(f"{OUT}/checks.json", "w"), indent=1, default=str)
    print(json.dumps(checks, indent=1, default=str))


if __name__ == "__main__":
    main()
