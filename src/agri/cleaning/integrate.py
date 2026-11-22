"""INTEGRATION: crops x provinces x climate x land use  ->  one analysis-ready table."""
from __future__ import annotations
import geopandas as gpd
from pyspark.sql import functions as F

from ..config import data_path
from ..spark_utils import read_table, write_table


def run(spark, cfg: dict) -> None:
    fmt = cfg["fmt"]
    crops = read_table(spark, data_path(cfg, "silver", "istat_crops"), fmt)
    gdf = gpd.read_parquet(data_path(cfg, "silver", "provinces.parquet"))
    attrs = gdf[["province_code", "province_name", "region", "area_km2", "lat", "lon"]].copy()
    prov = spark.createDataFrame(attrs.astype(object).values.tolist(),
                                 "province_code string, province_name string, region string, area_km2 double, lat double, lon double")

    unmatched = sorted(r[0] for r in crops.join(prov, "province_code", "left_anti").select("province_code").distinct().collect())
    if unmatched:
        print(f"[integrate] WARNING {len(unmatched)} ISTAT province codes have no boundary "
              f"(fix with config/province_crosswalk.csv or boundaries.merge): {unmatched}")
    used = {r[0] for r in crops.select("province_code").distinct().collect()}
    unused = gdf[~gdf["province_code"].isin(used)]
    if len(unused):
        print(f"[integrate] {len(unused)} boundary polygons have no ISTAT data: "
              + ", ".join(f"{c} ({n})" for c, n in zip(unused["province_code"], unused["province_name"])))
    df = crops.join(prov, "province_code", "inner")

    clim_p = data_path(cfg, "silver", "climate")
    if clim_p.exists():
        df = df.join(read_table(spark, clim_p, fmt), ["province_code", "year"], "left")
    lc_p = data_path(cfg, "silver", "landcover")
    if lc_p.exists():
        df = df.join(read_table(spark, lc_p, fmt), ["province_code", "year"], "left")

    write_table(df, data_path(cfg, "silver", "integrated"), fmt)
    print(f"[integrate] integrated: {df.count():,} rows, columns={df.columns}")
