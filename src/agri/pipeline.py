"""Pipeline steps as importable functions (used by scripts/run_pipeline.py, Docker and the Databricks notebook)."""
from __future__ import annotations

STEPS = ["collect", "bronze", "silver", "integrate", "gold", "model", "viz", "report"]   # what 'all' runs
SPARK_STEPS = {"bronze", "silver", "integrate", "gold", "model", "viz"}


def collect(cfg: dict, skip_climate: bool = False) -> None:
    if cfg["mode"] == "demo":
        from .ingestion import demo_data
        demo_data.generate(cfg)
        return
    from .cleaning.silver import build_provinces
    from .ingestion import boundaries, copernicus, faostat, istat
    istat.download(cfg)
    faostat.download(cfg)
    boundaries.download(cfg)
    provinces = build_provinces(cfg)
    if skip_climate:
        print("[collect] ERA5 climate skipped (--skip-climate)")
    else:
        copernicus.download(cfg)
        copernicus.build_climate_table(cfg, provinces)
    print("[collect] ESA CCI land cover: add data/real/raw/landcover/landcover_province_year.csv "
          "(province_code,year,cropland_pct) - see README. Skipped if absent.")


def climate(cfg: dict) -> None:
    """Optional step (not part of 'all'): ERA5 download + zonal stats, for the years in copernicus.years."""
    if cfg["mode"] == "demo":
        print("[climate] demo mode has synthetic climate already")
        return
    import geopandas as gpd
    from .cleaning.silver import build_provinces
    from .config import data_path
    from .ingestion import copernicus
    pp = data_path(cfg, "silver", "provinces.parquet")
    provinces = gpd.read_parquet(pp) if pp.exists() else build_provinces(cfg)
    copernicus.download(cfg)
    copernicus.build_climate_table(cfg, provinces)


def run(cfg: dict, steps, skip_climate: bool = False, spark=None) -> None:
    """Runs the requested steps in the fixed order collect -> climate -> bronze -> ... -> report."""
    steps = list(steps)
    if "collect" in steps:
        collect(cfg, skip_climate)
    if "climate" in steps:
        climate(cfg)
    if SPARK_STEPS & set(steps):
        if spark is None:
            from .spark_utils import get_spark
            spark = get_spark()
        if "bronze" in steps:
            from .cleaning import bronze; bronze.run(spark, cfg)
        if "silver" in steps:
            from .cleaning import silver; silver.run(spark, cfg)
        if "integrate" in steps:
            from .cleaning import integrate; integrate.run(spark, cfg)
        if "gold" in steps:
            from .features import gold; gold.run(spark, cfg)
        if "model" in steps:
            from .models import run as m; m.run(spark, cfg)
        if "viz" in steps:
            from .viz import run as v; v.run(spark, cfg)
    if "report" in steps:
        from . import report
        report.run(cfg)
    print("DONE")
