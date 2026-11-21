"""GOLD: analytical tables and KPIs.

  gold/crop_province_year : area, production, yield, share, Location Quotient (+ climate, lat/lon)
  gold/province_diversity : HHI + dominant crop per province-year
  gold/national_crop_year : national totals per crop
  gold/cagr               : CAGR per province-crop-decade
  gold/shift_share        : national / crop-mix / regional decomposition
"""
from __future__ import annotations
import pandas as pd
from pyspark.sql import functions as F

from ..config import data_path, out_path
from ..spark_utils import read_table, write_table
from .indicators import cagr_table, shift_share


def run(spark, cfg: dict) -> None:
    fmt = cfg["fmt"]
    df = read_table(spark, data_path(cfg, "silver", "integrated"), fmt).filter(F.col("area_ha").isNotNull())

    prov_tot = df.groupBy("province_code", "year").agg(F.sum("area_ha").alias("prov_area_ha"))
    nat_crop = df.groupBy("crop", "year").agg(F.sum("area_ha").alias("nat_crop_area_ha"),
                                              F.sum("production_t").alias("nat_crop_prod_t"))
    nat_tot = df.groupBy("year").agg(F.sum("area_ha").alias("nat_area_ha"))

    g = (df.join(prov_tot, ["province_code", "year"]).join(nat_crop, ["crop", "year"]).join(nat_tot, "year")
           .withColumn("share_in_province", F.col("area_ha") / F.col("prov_area_ha"))
           .withColumn("share_of_national_crop", F.col("area_ha") / F.col("nat_crop_area_ha"))
           .withColumn("nat_share", F.col("nat_crop_area_ha") / F.col("nat_area_ha"))
           # Location Quotient: >1 => province is MORE specialised in the crop than Italy as a whole
           .withColumn("lq", F.col("share_in_province") / F.col("nat_share")))
    write_table(g, data_path(cfg, "gold", "crop_province_year"), fmt)

    div = (g.groupBy("province_code", "province_name", "region", "year")
             .agg(F.sum(F.col("share_in_province") ** 2).alias("hhi"),
                  F.max_by("crop", "area_ha").alias("dominant_crop"),
                  F.count("crop").alias("n_crops"))
             .withColumn("effective_n_crops", 1 / F.col("hhi")))
    write_table(div, data_path(cfg, "gold", "province_diversity"), fmt)

    nat = nat_crop.withColumn("nat_yield_t_ha", F.col("nat_crop_prod_t") / F.col("nat_crop_area_ha"))
    write_table(nat, data_path(cfg, "gold", "national_crop_year"), fmt)

    # small tables -> pandas
    pdf = df.select("province_code", "crop", "year", "area_ha").toPandas()
    periods = [tuple(p) for p in cfg["periods"]]
    cagr = cagr_table(pdf, periods)
    ss = pd.concat([shift_share(pdf, a, b, smooth=3) for a, b in periods] +
                   [shift_share(pdf, cfg["years"]["start"], cfg["years"]["end"], smooth=3)], ignore_index=True)
    for name, t in (("cagr", cagr), ("shift_share", ss)):
        write_table(spark.createDataFrame(t.astype({c: "object" for c in t.select_dtypes("object").columns})), data_path(cfg, "gold", name), fmt)
        t.to_csv(out_path(cfg, "tables", f"{name}.csv"), index=False)

    # KPI summary: biggest winners / losers over the whole period
    full = ss[ss.period == f"{cfg['years']['start']}-{cfg['years']['end']}"]
    kpi = pd.concat([full.nlargest(15, "regional_effect").assign(kind="relocation_gain"),
                     full.nsmallest(15, "regional_effect").assign(kind="relocation_loss")])
    kpi.to_csv(out_path(cfg, "tables", "kpi_relocation.csv"), index=False)
    div.toPandas().to_csv(out_path(cfg, "tables", "province_diversity.csv"), index=False)
    print(f"[gold] tables written. crop_province_year rows={g.count():,}")
