"""Shared prediction, SHAP drivers, hex labelling and map drawing for a built area."""
import geopandas as gpd
import h3
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import shap

from build import CRS, V1

CATEGORY = [("train_station", "station"), ("park", "park"), ("distance_nearest_park", "park"),
            ("shop", "centre"), ("food", "centre"), ("bus_stop", "bus"), ("population", "population")]


def category(feature):
    return next(c for prefix, c in CATEGORY if feature.startswith(prefix))


def drivers(model, X, n=3):
    sv = shap.TreeExplainer(model).shap_values(X)
    out = []
    for row in sv:
        idx = np.argsort(-np.abs(row), kind="stable")[:n]
        out.append("; ".join(f"{V1[j]} {row[j]:+.2f}" for j in idx))
    cats = []
    for row in sv:
        pos = pd.Series(row, index=[category(f) for f in V1]).groupby(level=0).sum()
        cats.append(pos.idxmax())
    return out, cats


def label_hexes(hexes, zoning, stations):
    """Dominant zone, its role, nearest station and distance for each hex."""
    hits = gpd.overlay(hexes[["hex_id", "geometry"]], zoning[["SYM_CODE", "LAY_CLASS", "role", "geometry"]],
                       how="intersection", keep_geom_type=True)
    hits["a"] = hits.area
    dom = hits.sort_values("a", ascending=False).drop_duplicates("hex_id").set_index("hex_id")
    lab = pd.DataFrame(index=pd.Index(hexes.hex_id, name="hex_id"))
    lab["zone"] = dom.SYM_CODE.reindex(lab.index).fillna("unzoned") + " " + dom.LAY_CLASS.reindex(lab.index).fillna("")
    lab["role"] = dom.role.reindex(lab.index).fillna("unzoned")
    cen = hexes.geometry.centroid.values
    d = np.array([[c.distance(s) for s in stations.geometry] for c in cen])
    lab["nearest_station"] = stations.name.values[d.argmin(1)]
    lab["station_dist_m"] = d.min(1).round(0)
    ll = [h3.cell_to_latlng(h) for h in hexes.hex_id]
    lab["lat"], lab["lng"] = [round(a, 5) for a, _ in ll], [round(b, 5) for _, b in ll]
    return lab


def draw(hexes, values, zoning, stations, title, path, vmax=None, outline_roles=("centre", "park", "mu_fringe")):
    fig, ax = plt.subplots(figsize=(8, 9))
    g = hexes.assign(v=values.reindex(hexes.hex_id).values)
    g.plot(column="v", ax=ax, cmap="YlOrRd", vmin=0, vmax=vmax or max(g.v.max(), 1), edgecolor="none",
           legend=True, legend_kwds={"label": "Predicted toilets per hex", "shrink": 0.6})
    xmin, ymin, xmax, ymax = hexes.total_bounds
    colours = {"centre": "#1f4e9e", "park": "#2e8b3a", "mu_fringe": "#7a5fb0", "enterprise": "#888888"}
    for role in outline_roles:
        z = zoning[zoning.role == role].clip((xmin, ymin, xmax, ymax))
        if len(z):
            z.boundary.plot(ax=ax, color=colours[role], linewidth=0.8, label=f"{role} zone")
    s = stations.clip((xmin, ymin, xmax, ymax))
    s.plot(ax=ax, marker="s", color="black", markersize=40, label="station", zorder=5)
    for _, r in s.iterrows():
        ax.annotate(r["name"], (r.geometry.x, r.geometry.y), xytext=(6, 4), textcoords="offset points", fontsize=8)
    ax.set_xlim(xmin, xmax)
    ax.set_ylim(ymin, ymax)
    ax.set_axis_off()
    ax.set_title(title, fontsize=10)
    ax.legend(loc="lower left", fontsize=7)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)
