"""Plotly / Folium figures. Every function returns a figure so Streamlit can reuse them."""
from __future__ import annotations
import json
import numpy as np
import pandas as pd
import plotly.express as px

CLUSTER_COLORS = {"High-High": "#d7191c", "Low-Low": "#2c7bb6", "High-Low": "#fdae61",
                  "Low-High": "#abd9e9", "Not significant": "#e0e0e0"}


def _geojson(gdf, tol: float = 0.01) -> dict:
    g = gdf[["province_code", "province_name", "geometry"]].copy()
    g["geometry"] = g.geometry.simplify(tol, preserve_topology=True)
    return json.loads(g.to_json())


def fig_lq_animation(gold: pd.DataFrame, gdf, crop: str, value: str = "lq", cap: float = 3.0):
    """Choropleth with a year slider: Location Quotient of one crop per province."""
    d = gold[gold.crop == crop]
    idx = pd.MultiIndex.from_product([gdf.province_code.unique(), sorted(gold.year.unique())], names=["province_code", "year"])
    d = d.groupby(["province_code", "year"])[value].mean().reindex(idx).fillna(0).reset_index()
    d = d.merge(gdf[["province_code", "province_name"]], on="province_code")
    d[value] = d[value].clip(upper=cap)
    fig = px.choropleth_map(d, geojson=_geojson(gdf), locations="province_code", featureidkey="properties.province_code",
                            color=value, animation_frame="year", hover_name="province_name", range_color=(0, cap),
                            color_continuous_scale="YlOrRd", map_style="carto-positron", zoom=4.3,
                            center={"lat": 42.0, "lon": 12.5}, opacity=0.75,
                            title=f"{crop}: Location Quotient by province (>1 = specialised)")
    fig.update_layout(margin=dict(l=0, r=0, t=40, b=0))
    return fig


def fig_national_trends(nat: pd.DataFrame):
    d = nat.sort_values("year").copy()
    base = d.groupby("crop")["nat_crop_area_ha"].transform("first")
    d["area_index"] = 100 * d["nat_crop_area_ha"] / base
    return px.line(d, x="year", y="area_index", color="crop", title="National cultivated area (index, first year = 100)")


def fig_centroids(cen: pd.DataFrame):
    return px.line(cen, x="year", y="centroid_lat", color="crop",
                   title="Latitude of each crop's centre of gravity (rising = shifting north)")


def fig_hhi(div: pd.DataFrame):
    d = div.groupby(["region", "year"])["hhi"].mean().reset_index()
    return px.line(d, x="year", y="hhi", color="region",
                   title="Crop concentration (HHI) by region - higher = more specialised")


def fig_env(env: pd.DataFrame):
    d = env.copy()
    d["index"] = 100 * d["value"] / d.groupby("indicator")["value"].transform("first")
    return px.line(d.sort_values("year"), x="year", y="index", color="indicator",
                   title="FAOSTAT environmental indicators for Italy (national, first year = 100)")


def fig_climate_coefs(fe: pd.DataFrame):
    d = fe[fe.term == "precip_100mm"].copy()
    d["ci"] = 1.96 * d.std_err
    return px.bar(d, x="crop", y="coef", error_y="ci", title="Effect of +100 mm precipitation on log(yield) (province+year FE)")


def map_clusters(cl: pd.DataFrame, gdf, year: int):
    """Folium map, one switchable layer per crop (Local Moran's I cluster types)."""
    import folium
    m = folium.Map(location=[42.0, 12.5], zoom_start=6, tiles="cartodbpositron")
    for crop in sorted(cl.crop.unique()):
        sub = cl[(cl.crop == crop) & (cl.year == year)].set_index("province_code")
        g = gdf.merge(sub[["lisa_cluster", "lq"]], left_on="province_code", right_index=True, how="left")
        g["lisa_cluster"] = g["lisa_cluster"].fillna("Not significant")
        g["geometry"] = g.geometry.simplify(0.01)
        folium.GeoJson(
            g[["province_name", "lisa_cluster", "lq", "geometry"]].to_json(), name=f"{crop} ({year})", show=False,
            style_function=lambda f: {"fillColor": CLUSTER_COLORS.get(f["properties"]["lisa_cluster"], "#e0e0e0"),
                                      "color": "#555", "weight": 0.4, "fillOpacity": 0.8},
            tooltip=folium.GeoJsonTooltip(["province_name", "lisa_cluster", "lq"])).add_to(m)
    folium.LayerControl(collapsed=False).add_to(m)
    return m
