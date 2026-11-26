"""Writes all interactive outputs (HTML) to outputs/<mode>/."""
from __future__ import annotations
import geopandas as gpd
import pandas as pd

from ..config import data_path, out_path
from ..spark_utils import read_pandas
from . import figures as F


def run(spark, cfg: dict) -> None:
    fmt = cfg["fmt"]
    gold = read_pandas(spark, data_path(cfg, "gold", "crop_province_year"), fmt)
    nat = read_pandas(spark, data_path(cfg, "gold", "national_crop_year"), fmt)
    div = read_pandas(spark, data_path(cfg, "gold", "province_diversity"), fmt)
    gdf = gpd.read_parquet(data_path(cfg, "silver", "provinces.parquet"))
    tables = out_path(cfg, "tables", "x").parent
    links = []

    def save(fig, name, title):
        p = out_path(cfg, "maps" if name.startswith(("lq_", "lisa")) else "charts", f"{name}.html")
        if hasattr(fig, "write_html"):
            fig.write_html(str(p), include_plotlyjs="directory")   # plotly.min.js saved next to the file -> works offline
        else:
            fig.save(str(p))
        links.append((title, p.relative_to(p.parents[1]).as_posix()))

    for crop in sorted(gold.crop.unique()):
        save(F.fig_lq_animation(gold, gdf, crop), f"lq_{crop}", f"Animated map: {crop}")
    save(F.fig_national_trends(nat), "national_trends", "National area trends")
    save(F.fig_hhi(div), "hhi_by_region", "Crop concentration (HHI)")
    if (tables / "crop_centroids.csv").exists():
        save(F.fig_centroids(pd.read_csv(tables / "crop_centroids.csv")), "centroid_shift", "Centre-of-gravity shift")
    if (tables / "spatial_clusters.csv").exists():
        cl = pd.read_csv(tables / "spatial_clusters.csv", dtype={"province_code": str})
        save(F.map_clusters(cl, gdf, int(cl.year.max())), "lisa_clusters", f"Spatial clusters {int(cl.year.max())}")
    if (tables / "climate_fixed_effects.csv").exists():
        fe = pd.read_csv(tables / "climate_fixed_effects.csv")
        if len(fe):
            save(F.fig_climate_coefs(fe), "climate_effects", "Climate effect on yield")
    clim_p = data_path(cfg, "silver", "climate")
    if clim_p.exists():
        save(F.fig_climate_series(read_pandas(spark, clim_p, fmt)), "climate_series", "Climate 1992+: temperature and precipitation")
        if (tables / "climate_trends.csv").exists():
            ct = pd.read_csv(tables / "climate_trends.csv", dtype={"province_code": str})
            if len(ct):
                save(F.fig_warming_map(ct, gdf, "t2m_mean_c"), "warming_map", "Warming rate per province (C/decade)")
    env_p = data_path(cfg, "silver", "fao_env_national")
    if env_p.exists():
        save(F.fig_env(read_pandas(spark, env_p, fmt)), "fao_env", "FAOSTAT environmental indicators")

    html = "<h1>Italy agriculture - outputs</h1><ul>" + "".join(f'<li><a href="{u}">{t}</a></li>' for t, u in links) + "</ul>"
    out_path(cfg, "index.html").write_text(html, encoding="utf-8")
    print(f"[viz] {len(links)} figures -> {out_path(cfg, 'index.html')}")
