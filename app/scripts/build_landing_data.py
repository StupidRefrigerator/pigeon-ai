"""Turn the model outputs into app/public/landing-hexes.json for the landing-page map.

Run from anywhere:  /tmp/pigeon-env/bin/python app/scripts/build_landing_data.py

Reads data/model/hex_predictions.csv (every study hex) and data/model/recommendations.csv
(the suggested spots, ranked by gap, no weighting). Output, kept small for the browser:
  w, h, r  map size and hex radius in map units (hex radius = 8 units)
  xy       "x,y,x,y,..." hex centres, one pair per hex
  s        one char per hex: 'p' suggested spot, 't' has a public toilet,
           '1'..'9' gap level (bigger = more missing), '0' no meaningful gap
  picks    indices of the suggested spots, best first
"""
import json
import math
from pathlib import Path

import h3
import pandas as pd

APP = Path(__file__).resolve().parents[1]
REPO = APP.parent
OUT = APP / "public" / "landing-hexes.json"

hexes = pd.read_csv(REPO / "data/model/hex_predictions.csv")
recs = pd.read_csv(REPO / "data/model/recommendations.csv").sort_values("rank")
assert len(hexes) == 16228 and hexes.hex_id.is_unique
assert len(recs) == 100 and recs.hex_id.isin(hexes.hex_id).all()

# Equirectangular projection around Sydney, y pointing down.
k = math.cos(math.radians(-33.87))
lat, lng = zip(*(h3.cell_to_latlng(h) for h in hexes.hex_id))
px = [ln * k for ln in lng]
py = [-la for la in lat]
mid = hexes.hex_id.iloc[len(hexes) // 2]
mla, mln = h3.cell_to_latlng(mid)
corner = h3.cell_to_boundary(mid)[0]
radius = math.hypot(corner[1] * k - mln * k, -corner[0] + mla)
unit = radius / 8
x0, y0 = min(px), min(py)
xs = [round((x - x0) / unit) for x in px]
ys = [round((y - y0) / unit) for y in py]

index = {h: i for i, h in enumerate(hexes.hex_id)}
picks = [index[h] for h in recs.hex_id]
pick_set = set(picks)


def state(i, row):
    if i in pick_set:
        return "p"
    if row.toilet_count > 0:
        return "t"
    return str(min(9, int(row.gap * 12))) if row.gap > 0.08 else "0"


s = "".join(state(i, row) for i, row in enumerate(hexes.itertuples()))
assert s.count("p") == 100

out = {"w": max(xs), "h": max(ys), "r": 8, "xy": ",".join(f"{x},{y}" for x, y in zip(xs, ys)), "s": s, "picks": picks}
OUT.write_text(json.dumps(out, separators=(",", ":")))
print(f"{OUT.relative_to(REPO)}: {len(s)} hexes, {s.count('t')} with a toilet, "
      f"{sum(c in '123456789' for c in s)} with a gap, {len(picks)} suggested, {OUT.stat().st_size // 1024} KB")
