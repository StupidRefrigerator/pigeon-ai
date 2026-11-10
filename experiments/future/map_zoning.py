"""Planned zoning roles map for the Aerotropolis area (map_aero_zoning.png)."""
import json
import sys

sys.path.insert(0, "/tmp/pigeon-eval/future")
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

from build import hex_grid, load_zoning, split_aero_mu, station_points

COLOURS = {"centre": "#d62728", "mu_fringe": "#ff9896", "enterprise": "#9e9e9e", "park": "#2ca02c",
           "residential": "#ffbb78", "low_residential": "#ffe0b2", "infrastructure": "#1f77b4", "rural": "#f5f0d0",
           "conservation": "#98df8a", "private_recreation": "#bcbd22"}
st = station_points(json.load(open("/tmp/pigeon-eval/future/downloads/stations_raw.json")))
z = split_aero_mu(load_zoning((150.58, -34.06, 150.89, -33.76), "zoning_units"), st[st.planned])
b = hex_grid((150.69, -33.945, 150.78, -33.83)).total_bounds
zc = z.clip(b)
fig, ax = plt.subplots(figsize=(8, 9))
for role, colour in COLOURS.items():
    if (zc.role == role).any():
        zc[zc.role == role].plot(ax=ax, color=colour, edgecolor="white", linewidth=0.2)
s = st.clip(b)
s.plot(ax=ax, marker="s", color="k", markersize=40)
for _, r in s.iterrows():
    ax.annotate(r["name"], (r.geometry.x, r.geometry.y), xytext=(6, 4), textcoords="offset points", fontsize=8)
ax.legend(handles=[Patch(color=c, label=r) for r, c in COLOURS.items() if (zc.role == r).any()], loc="lower left", fontsize=7)
ax.set_axis_off()
ax.set_title("Planned zoning roles, Aerotropolis core (NSW Land Zoning layer)", fontsize=10)
fig.tight_layout()
fig.savefig("/tmp/pigeon-eval/future/map_aero_zoning.png", dpi=120)
