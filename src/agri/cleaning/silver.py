"""SILVER: cleaned, typed, harmonised tables.

Cleaning rules (all documented, nothing silently invented):
  * column names -> canonical schema, codes -> zero-padded 3-digit strings
  * decimal commas / thousand separators handled, bad numbers -> NULL (try_cast, never crashes)
  * crop names harmonised via config crop_map; sub-crops (durum+soft wheat) are SUMMED
  * quintals -> tonnes; negative or zero areas / negative production -> NULL
  * exact duplicates dropped; years outside the study window dropped
  * missing values are NOT imputed (a gap stays a gap); yield outliers are only FLAGGED
  * province code changes handled through config/province_crosswalk.csv
"""
from __future__ import annotations
import json
import pandas as pd
from pyspark.sql import functions as F
from pyspark.sql import Window

from ..config import ROOT, data_path
from ..spark_utils import read_table, write_table

NUTS2_NAMES = {"ITC1": "Piemonte", "ITC2": "Valle d'Aosta", "ITC3": "Liguria", "ITC4": "Lombardia",
               "ITD1": "Bolzano", "ITD2": "Trento", "ITD3": "Veneto", "ITD4": "Friuli-Venezia Giulia",
               "ITD5": "Emilia-Romagna", "ITE1": "Toscana", "ITE2": "Umbria", "ITE3": "Marche", "ITE4": "Lazio",
               "ITF1": "Abruzzo", "ITF2": "Molise", "ITF3": "Campania", "ITF4": "Puglia", "ITF5": "Basilicata",
               "ITF6": "Calabria", "ITG1": "Sicilia", "ITG2": "Sardegna"}

REGIONS = {1: "Piemonte", 2: "Valle d'Aosta", 3: "Lombardia", 4: "Trentino-Alto Adige", 5: "Veneto",
           6: "Friuli-Venezia Giulia", 7: "Liguria", 8: "Emilia-Romagna", 9: "Toscana", 10: "Umbria",
           11: "Marche", 12: "Lazio", 13: "Abruzzo", 14: "Molise", 15: "Campania", 16: "Puglia",
           17: "Basilicata", 18: "Calabria", 19: "Sicilia", 20: "Sardegna"}


# ---------- helpers ----------
def to_double(df, col):
    """Robust numeric parse: '1.234,5' | '12,5' | '12.5' | '' | 'n.d.' -> double / NULL."""
    s = F.trim(F.col(col).cast("string"))
    both = s.contains(",") & s.contains(".")
    s = F.when(both, F.regexp_replace(F.regexp_replace(s, r"\.", ""), ",", ".")).otherwise(F.regexp_replace(s, ",", "."))
    return df.withColumn("__x", s).withColumn(col, F.expr("try_cast(__x as double)")).drop("__x")


def to_int(df, col):
    return df.withColumn(col, F.expr(f"try_cast(try_cast(`{col}` as double) as int)"))


def zfill_code(col, n=3):
    c = F.regexp_replace(F.trim(F.col(col).cast("string")), r"\.0+$", "")
    return F.lpad(c, n, "0")


def crop_expr(col, crop_map):
    syn = {}
    for canon, lst in crop_map.items():
        for s in list(lst) + [canon]:
            syn[str(s).strip().lower()] = canon
    mapping = F.create_map(*[F.lit(x) for kv in syn.items() for x in kv])
    key = F.lower(F.trim(F.col(col)))
    return F.coalesce(mapping[key], key)


def _crosswalk(spark):
    p = ROOT / "config" / "province_crosswalk.csv"
    pdf = pd.read_csv(p, dtype=str) if p.exists() else pd.DataFrame()
    if pdf.empty:
        return None
    pdf["old_code"] = pdf["old_code"].str.zfill(3)
    pdf["new_code"] = pdf["new_code"].str.zfill(3)
    return spark.createDataFrame(pdf[["old_code", "new_code"]].astype(object).values.tolist(), "old_code string, new_code string")


# ---------- ISTAT crops ----------
def transform_istat_sdmx(df, cfg: dict):
    """ISTAT SDMX long format -> canonical wide table (province_code, crop, year, area_ha, production_q).
    Keeps only NUTS3 provinces (5-char codes), the configured crop codes and the two data types."""
    need = ["REF_AREA", "DATA_TYPE", "TYPE_OF_CROP", "DESTINATION_WINEGRAPES", "TIME_PERIOD", "OBS_VALUE"]
    missing = [c for c in need if c not in df.columns]
    if missing:
        raise ValueError(f"SDMX columns missing: {missing}; found {df.columns}")
    sx = cfg["istat"]["sdmx"]
    code2crop = {code: crop for crop, codes in sx["crop_codes"].items() for code in codes}
    cmap = F.create_map(*[F.lit(x) for kv in code2crop.items() for x in kv])
    df = (df.select(*need).dropDuplicates()
            .filter(F.length("REF_AREA") == 5)                                   # provinces only (NUTS3)
            .filter(F.col("DESTINATION_WINEGRAPES") == sx.get("destination", "ALL"))
            .filter(F.col("DATA_TYPE").isin(sx["area_data_type"], sx["production_data_type"]))
            .withColumn("crop", cmap[F.col("TYPE_OF_CROP")])
            .filter(F.col("crop").isNotNull())
            .withColumn("province_code", F.col("REF_AREA"))
            .withColumn("year", F.expr("try_cast(TIME_PERIOD as int)")))
    df = to_double(df, "OBS_VALUE")
    return (df.groupBy("province_code", "crop", "year")
              .agg(F.sum(F.when(F.col("DATA_TYPE") == sx["area_data_type"], F.col("OBS_VALUE"))).alias("area_ha"),
                   F.sum(F.when(F.col("DATA_TYPE") == sx["production_data_type"], F.col("OBS_VALUE"))).alias("production_q")))


def build_istat(spark, cfg: dict) -> None:
    df = read_table(spark, data_path(cfg, "bronze", "istat_crops"), cfg["fmt"])
    n_raw = df.count()
    if cfg["istat"].get("format", "wide") == "sdmx":
        df = transform_istat_sdmx(df, cfg).withColumnRenamed("production_q", "production")
        factor = 0.1                                                           # quintals -> tonnes
        n_dedup = n_raw
    else:
        cmap = cfg["istat"]["columns"]
        missing = [c for c in cmap if c not in df.columns]
        if missing:
            raise ValueError(f"Columns {missing} not in the ISTAT file. Columns found: {df.columns}. "
                             "Fix istat.columns in config/sources.yml")
        df = df.select([F.col(k).alias(v) for k, v in cmap.items()])
        df = df.dropDuplicates()
        n_dedup = df.count()
        df = (df.withColumn("province_code", zfill_code("province_code"))
                .withColumn("crop", crop_expr("crop", cfg["crop_map"])))
        df = to_int(df, "year")
        df = to_double(df, "area_ha")
        df = to_double(df, "production")
        factor = 0.1 if cfg["istat"]["production_unit"] == "q" else 1.0
    df = df.withColumn("production_t", F.col("production") * F.lit(factor)).drop("production")
    df = (df.withColumn("area_ha", F.when(F.col("area_ha") > 0, F.col("area_ha")))
            .withColumn("production_t", F.when(F.col("production_t") >= 0, F.col("production_t"))))
    y0, y1 = cfg["years"]["start"], cfg["years"]["end"]
    df = df.filter(F.col("year").between(y0, y1) & F.col("province_code").isNotNull()
                   & F.col("crop").isNotNull() & (F.col("crop") != ""))

    cw = _crosswalk(spark)
    if cw is not None:
        df = (df.join(cw, df.province_code == cw.old_code, "left")
                .withColumn("province_code", F.coalesce("new_code", "province_code")).drop("old_code", "new_code"))

    df = (df.groupBy("province_code", "crop", "year")
            .agg(F.sum("area_ha").alias("area_ha"), F.sum("production_t").alias("production_t")))
    df = df.withColumn("yield_t_ha", F.when(F.col("area_ha") > 0, F.col("production_t") / F.col("area_ha")))
    med = Window.partitionBy("crop")
    df = df.withColumn("is_yield_outlier", F.col("yield_t_ha") > 5 * F.percentile_approx("yield_t_ha", 0.5).over(med))
    write_table(df, data_path(cfg, "silver", "istat_crops"), cfg["fmt"])

    dq = dict(rows_raw=n_raw, rows_after_dedup=n_dedup, rows_silver=df.count(),
              null_area=df.filter(F.col("area_ha").isNull()).count(),
              null_production=df.filter(F.col("production_t").isNull()).count(),
              yield_outliers=df.filter("is_yield_outlier").count(),
              provinces=df.select("province_code").distinct().count(),
              years=[r[0] for r in df.select("year").distinct().orderBy("year").collect()],
              crops=sorted(r[0] for r in df.select("crop").distinct().collect()))
    p = data_path(cfg, "silver", "_dq_istat.json")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(dq, indent=2))
    print(f"[silver] istat_crops: {dq}")


# ---------- FAOSTAT ----------
def build_fao(spark, cfg: dict) -> None:
    area = cfg["faostat"]["area_name"]
    crops_p = data_path(cfg, "bronze", "fao_crops")
    if crops_p.exists():
        df = read_table(spark, crops_p, cfg["fmt"]).filter(F.col("Area") == area)
        df = df.filter(F.col("Element").isin("Area harvested", "Production"))
        df = to_double(to_int(df, "Year"), "Value").withColumn("crop", crop_expr("Item", cfg["crop_map"]))
        df = df.filter(F.col("crop").isin(list(cfg["crop_map"])))
        df = (df.groupBy("crop", F.col("Year").alias("year"))
                .agg(F.sum(F.when(F.col("Element") == "Area harvested", F.col("Value"))).alias("area_ha"),
                     F.sum(F.when(F.col("Element") == "Production", F.col("Value"))).alias("production_t")))
        write_table(df, data_path(cfg, "silver", "fao_crops_national"), cfg["fmt"])
        print(f"[silver] fao_crops_national: {df.count():,} rows")
    parts = []
    for name in ("fao_pesticides", "fao_fertilizers"):
        pth = data_path(cfg, "bronze", name)
        if pth.exists():
            d = read_table(spark, pth, cfg["fmt"]).filter(F.col("Area") == area)
            parts.append(d.select("Item", "Element", "Year", "Unit", "Value"))
    if parts:
        env = parts[0]
        for d in parts[1:]:
            env = env.unionByName(d)
        env = to_double(to_int(env, "Year"), "Value")
        env = env.select(F.concat_ws(" | ", "Item", "Element").alias("indicator"),
                         F.col("Year").alias("year"), "Unit", F.col("Value").alias("value")).dropna(subset=["year", "value"])
        write_table(env, data_path(cfg, "silver", "fao_env_national"), cfg["fmt"])
        print(f"[silver] fao_env_national: {env.count():,} rows")


# ---------- climate / land cover ----------
def build_climate(spark, cfg: dict) -> None:
    p = data_path(cfg, "bronze", "climate")
    if not p.exists():
        return
    df = read_table(spark, p, cfg["fmt"]).select("province_code", "year", "t2m_mean_c", "t2m_summer_c", "precip_mm")
    df = df.withColumn("province_code", zfill_code("province_code"))
    df = to_int(df, "year")
    for c in ("t2m_mean_c", "t2m_summer_c", "precip_mm"):
        df = to_double(df, c)
    df = (df.withColumn("t2m_mean_c", F.when(F.col("t2m_mean_c").between(-30, 50), F.col("t2m_mean_c")))
            .withColumn("precip_mm", F.when(F.col("precip_mm").between(0, 6000), F.col("precip_mm")))
            .dropDuplicates(["province_code", "year"]))
    write_table(df, data_path(cfg, "silver", "climate"), cfg["fmt"])
    print(f"[silver] climate: {df.count():,} rows")


def build_landcover(spark, cfg: dict) -> None:
    p = data_path(cfg, "bronze", "landcover")
    if not p.exists():
        return
    df = read_table(spark, p, cfg["fmt"]).select("province_code", "year", "cropland_pct")
    df = to_double(to_int(df.withColumn("province_code", zfill_code("province_code")), "year"), "cropland_pct")
    df = df.withColumn("cropland_pct", F.when(F.col("cropland_pct").between(0, 100), F.col("cropland_pct"))) \
           .dropDuplicates(["province_code", "year"])
    write_table(df, data_path(cfg, "silver", "landcover"), cfg["fmt"])
    print(f"[silver] landcover: {df.count():,} rows")


# ---------- boundaries (GeoPandas) ----------
def build_provinces(cfg: dict):
    import geopandas as gpd
    folder = data_path(cfg, "raw", "boundaries")
    cands = (list(folder.glob("**/*ProvCM*.shp")) or list(folder.glob("**/*Prov*.shp"))
             or list(folder.glob("**/*.geojson")) or list(folder.glob("**/*.shp")))
    if not cands:
        raise FileNotFoundError(f"No boundary file in {folder}")
    gdf = gpd.read_file(cands[0]).to_crs(4326)
    b = cfg["boundaries"]
    if "NUTS_ID" in gdf.columns:                                  # Eurostat GISCO NUTS3 file
        if "CNTR_CODE" in gdf.columns:
            gdf = gdf[gdf["CNTR_CODE"] == "IT"]
        if "LEVL_CODE" in gdf.columns:
            gdf = gdf[gdf["LEVL_CODE"] == 3]
        namecol = "NAME_LATN" if "NAME_LATN" in gdf.columns else "NUTS_NAME"
        out = gpd.GeoDataFrame({
            "province_code": gdf["NUTS_ID"].astype(str).values,
            "province_name": gdf[namecol].astype(str).values,
            "region": gdf["NUTS_ID"].astype(str).str[:4].map(NUTS2_NAMES).fillna(gdf["NUTS_ID"].astype(str).str[:4]).values,
        }, geometry=gdf.geometry.make_valid().values, crs=4326)
    else:                                                         # ISTAT shapefile / demo geojson
        out = gpd.GeoDataFrame({
            "province_code": gdf[b["code_col"]].astype(str).str.replace(r"\.0$", "", regex=True).str.zfill(3),
            "province_name": gdf[b["name_col"]].astype(str),
            "region": (gdf["REGIONE"].astype(str) if "REGIONE" in gdf.columns
                       else gdf[b["region_code_col"]].astype(int).map(REGIONS)),
        }, geometry=gdf.geometry.make_valid(), crs=4326)
    proj = out.to_crs(3035)
    out["area_km2"] = proj.area / 1e6
    cen = proj.centroid.to_crs(4326)
    out["lat"], out["lon"] = cen.y, cen.x
    dest = data_path(cfg, "silver", "provinces.parquet")
    dest.parent.mkdir(parents=True, exist_ok=True)
    out.to_parquet(dest)
    print(f"[silver] provinces: {len(out)} polygons from {cands[0].name}")
    return out


def run(spark, cfg: dict) -> None:
    build_istat(spark, cfg)
    build_fao(spark, cfg)
    build_climate(spark, cfg)
    build_landcover(spark, cfg)
    build_provinces(cfg)
