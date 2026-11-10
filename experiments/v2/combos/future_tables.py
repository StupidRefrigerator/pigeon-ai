"""Side-by-side top-10 tables for future areas (seed 0, F scenario planned_re1)."""
import pandas as pd

from common import OUT

t = pd.read_csv(OUT / "future_top10.csv")
SHORT = {"train_station": "station", "food": "food", "shop": "shops", "park": "park", "sports": "sports",
         "distance_nearest_sports": "sports", "distance_nearest_playground": "playground",
         "distance_nearest_park": "park", "population": "population", "playground": "playground", "bus": "bus"}


def drv(s):
    out = []
    for part in s.split("; ")[:2]:
        f = part.rsplit(" ", 1)[0]
        k = next(v for p, v in SHORT.items() if f.startswith(p))
        if k not in out:
            out.append(k)
    return " + ".join(out)


blocks = []
for area in ("aerotropolis", "leppington"):
    for fs in ("planned_re1", "planned_re1_enz"):
        d = t[(t.area == area) & (t.f_scenario == fs)]
        cols = {}
        for m, g in d.groupby("model", sort=False):
            g = g.sort_values("rank")
            cols[m] = [f"{r.zone.split(' ')[0]}, {r.nearest_station.replace(' Station', '')} {r.station_dist_m:.0f} m, "
                       f"{r.pred:.2f} ({drv(r.drivers)})" + (" **Bradfield stn**" if r.hex_id == "89be0856407ffff" else "")
                       for r in g.itertuples()]
        df = pd.DataFrame(cols)
        df.insert(0, "rank", range(1, len(df) + 1))
        md = ["| " + " | ".join(df.columns) + " |", "|" + "---|" * len(df.columns)]
        md += ["| " + " | ".join(map(str, x)) + " |" for x in df.itertuples(index=False)]
        blocks.append(f"### {area} — F scenario {fs}\n" + "\n".join(md))
open(OUT / "future_tables.md", "w").write("\n\n".join(blocks) + "\n")
print("\n\n".join(blocks))
