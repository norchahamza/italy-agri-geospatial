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


def fig_lq_animation(gold: pd.DataFrame, gdf, crop: str, value: str = "lq", cap: float = 3.0, tiles: bool = False):
    """Choropleth with a year slider: Location Quotient of one crop per province.
    tiles=False (default): Plotly 'geo' map = provinces only, works offline and from file:// (no WebGL worker).
    tiles=True: MapLibre street-map background (needs http://, e.g. Streamlit)."""
    d = gold[gold.crop == crop]
    idx = pd.MultiIndex.from_product([gdf.province_code.unique(), sorted(gold.year.unique())], names=["province_code", "year"])
    d = d.groupby(["province_code", "year"])[value].mean().reindex(idx).fillna(0).reset_index()
    d = d.merge(gdf[["province_code", "province_name"]], on="province_code")
    d[value] = d[value].clip(upper=cap)
    title = f"{crop}: Location Quotient by province (>1 = specialised)"
    common = dict(geojson=_geojson(gdf), locations="province_code", featureidkey="properties.province_code",
                  color=value, animation_frame="year", hover_name="province_name", range_color=(0, cap),
                  color_continuous_scale="YlOrRd", title=title)
    if tiles:
        fig = px.choropleth_map(d, map_style="open-street-map", zoom=4.3, center={"lat": 42.0, "lon": 12.5}, opacity=0.75, **common)
    else:
        fig = px.choropleth(d, **common)
        fig.update_geos(fitbounds="locations", visible=False)
        fig.update_traces(marker_line_width=0.3, marker_line_color="#555")
    fig.update_layout(margin=dict(l=0, r=0, t=40, b=0), height=700)
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
    """Folium map, one switchable layer per crop (Local Moran's I cluster types) + legend. Tiles: OpenStreetMap (no API key)."""
    import folium
    from branca.element import Element
    m = folium.Map(location=[42.0, 12.5], zoom_start=6, tiles="OpenStreetMap")
    for i, crop in enumerate(sorted(cl.crop.unique())):
        sub = cl[(cl.crop == crop) & (cl.year == year)].set_index("province_code")
        g = gdf.merge(sub[["lisa_cluster", "lq"]], left_on="province_code", right_index=True, how="left")
        g["lisa_cluster"] = g["lisa_cluster"].fillna("Not significant")
        g["geometry"] = g.geometry.simplify(0.01)
        fg = folium.FeatureGroup(name=f"{crop} ({year})", show=(i == 0))      # only the first crop visible at start
        folium.GeoJson(
            g[["province_name", "lisa_cluster", "lq", "geometry"]].to_json(),
            style_function=lambda f: {"fillColor": CLUSTER_COLORS.get(f["properties"]["lisa_cluster"], "#e0e0e0"),
                                      "color": "#555", "weight": 0.4, "fillOpacity": 0.8},
            tooltip=folium.GeoJsonTooltip(["province_name", "lisa_cluster", "lq"])).add_to(fg)
        fg.add_to(m)
    folium.LayerControl(collapsed=False).add_to(m)
    legend = ('<div style="position:fixed;bottom:30px;left:30px;z-index:9999;background:white;padding:8px 10px;'
              'border:1px solid #888;font-size:12px"><b>Local Moran cluster</b>' +
              "".join(f'<div><span style="background:{c};display:inline-block;width:12px;height:12px;margin-right:6px"></span>{k}</div>'
                      for k, c in CLUSTER_COLORS.items()) + "</div>")
    m.get_root().html.add_child(Element(legend))
    return m


def fig_climate_series(clim: pd.DataFrame):
    """Mean temperature and precipitation over all provinces, per year, with linear trend lines."""
    import numpy as np
    from plotly.subplots import make_subplots
    import plotly.graph_objects as go
    d = clim.groupby("year")[["t2m_mean_c", "precip_mm"]].mean().reset_index()
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.08,
                        subplot_titles=("Mean annual temperature (C)", "Mean annual precipitation (mm)"))
    for i, (col, color) in enumerate((("t2m_mean_c", "#d7191c"), ("precip_mm", "#2c7bb6")), start=1):
        fig.add_trace(go.Scatter(x=d.year, y=d[col], mode="lines+markers", name=col, line=dict(color=color)), row=i, col=1)
        k, b = np.polyfit(d.year, d[col], 1)
        fig.add_trace(go.Scatter(x=d.year, y=k * d.year + b, mode="lines", name=f"trend {10 * k:+.2f} per decade",
                                 line=dict(color=color, dash="dash")), row=i, col=1)
    fig.update_layout(height=650, title="Italy climate (ERA5-Land, province average)")
    return fig


def fig_warming_map(trends: pd.DataFrame, gdf, variable: str = "t2m_mean_c"):
    """Choropleth of the Sen's-slope warming rate per province (C per decade)."""
    d = trends[trends.variable == variable].merge(gdf[["province_code", "province_name"]], on="province_code")
    lim = max(abs(d.sen_slope_per_decade).max(), 0.01)
    fig = px.choropleth(d, geojson=_geojson(gdf), locations="province_code", featureidkey="properties.province_code",
                        color="sen_slope_per_decade", hover_name="province_name", hover_data={"p": ":.3f"},
                        color_continuous_scale="RdBu_r", range_color=(-lim, lim),
                        title=f"{variable}: trend per decade (Sen's slope)")
    fig.update_geos(fitbounds="locations", visible=False)
    fig.update_traces(marker_line_width=0.3, marker_line_color="#555")
    fig.update_layout(margin=dict(l=0, r=0, t=40, b=0), height=700)
    return fig
