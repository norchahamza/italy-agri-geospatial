"""Runs every model and stores results under gold/ and outputs/<mode>/tables."""
from __future__ import annotations
import json
import geopandas as gpd
import pandas as pd

from ..config import data_path, out_path
from ..spark_utils import read_pandas
from . import clusters, climate, trends


def run(spark, cfg: dict) -> None:
    fmt, m = cfg["fmt"], cfg["model"]
    gold = read_pandas(spark, data_path(cfg, "gold", "crop_province_year"), fmt)
    gdf = gpd.read_parquet(data_path(cfg, "silver", "provinces.parquet"))
    tab = lambda n: out_path(cfg, "tables", n)

    tr = trends.run_trends(gold, "area_ha", m["min_years_trend"])
    tr.to_csv(tab("trends_area.csv"), index=False)
    print(f"[model] Mann-Kendall: {len(tr)} series; increasing={int((tr.trend=='increasing').sum())} "
          f"decreasing={int((tr.trend=='decreasing').sum())}")

    y0, y1 = cfg["years"]["start"], cfg["years"]["end"]
    crops = sorted(gold.crop.unique())
    cl = clusters.all_clusters(gold, gdf, crops, [y0, y1], k=m["lisa_neighbors"], permutations=m["lisa_permutations"])
    cl.to_csv(tab("spatial_clusters.csv"), index=False)
    cen = clusters.crop_centroids(gold)
    cen.to_csv(tab("crop_centroids.csv"), index=False)
    print(f"[model] spatial clusters: {len(cl)} rows; centroid table: {len(cen)} rows")

    fe = pd.concat([climate.fixed_effects(gold, c) for c in crops], ignore_index=True)
    fe.to_csv(tab("climate_fixed_effects.csv"), index=False)
    imp, metrics = climate.random_forest(gold, m["rf_train_until"])
    imp.to_csv(tab("rf_importance.csv"), index=False)
    tab("rf_metrics.json").write_text(json.dumps(metrics, indent=2))
    print(f"[model] fixed-effects rows={len(fe)}; RF metrics={metrics}")
