"""Maps and charts. Needs geopandas/folium (see requirements.txt)."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def plot_residual_map(df, value="resid", path="outputs/residual_map.png"):
    """Quick scatter map of residuals by province centroid (lon/lat columns)."""
    fig, ax = plt.subplots(figsize=(6, 5))
    sc = ax.scatter(df["lon"], df["lat"], c=df[value], cmap="coolwarm", s=60)
    fig.colorbar(sc, label=value)
    ax.set_title("Model residuals by province")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path


def interactive_choropleth(gdf, column, path="outputs/map.html"):
    """Interactive HTML map from a GeoDataFrame in EPSG:4326."""
    import folium
    m = folium.Map(location=[42.5, 12.5], zoom_start=6, tiles="cartodbpositron")
    folium.Choropleth(geo_data=gdf.to_json(), data=gdf, columns=[gdf.index.name or "index", column],
                      key_on="feature.id", fill_color="YlGn", legend_name=column).add_to(m)
    m.save(path)
    return path
