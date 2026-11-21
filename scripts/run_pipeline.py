#!/usr/bin/env python
"""End-to-end pipeline.   python scripts/run_pipeline.py --mode demo --steps all"""
from __future__ import annotations
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agri.config import load_config  # noqa: E402

STEPS = ["collect", "bronze", "silver", "integrate", "gold", "model", "viz", "report"]


def collect(cfg):
    if cfg["mode"] == "demo":
        from agri.ingestion import demo_data
        demo_data.generate(cfg)
        return
    from agri.ingestion import boundaries, copernicus, faostat, istat
    istat.download(cfg)
    faostat.download(cfg)
    boundaries.download(cfg)
    from agri.cleaning.silver import build_provinces
    provinces = build_provinces(cfg)
    copernicus.download(cfg)
    copernicus.build_climate_table(cfg, provinces)
    print("[collect] ESA CCI land cover: add data/real/raw/landcover/landcover_province_year.csv "
          "(province_code,year,cropland_pct) - see README. Skipped if absent.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["demo", "real"], default="demo")
    ap.add_argument("--steps", default="all", help=f"comma list from {STEPS} or 'all'")
    ap.add_argument("--list-istat-dataflows", action="store_true")
    a = ap.parse_args()
    cfg = load_config(a.mode)

    if a.list_istat_dataflows:
        from agri.ingestion import istat
        istat.list_dataflows(cfg)
        return
    steps = STEPS if a.steps == "all" else a.steps.split(",")
    if "collect" in steps:
        collect(cfg)
    if any(s in steps for s in ("bronze", "silver", "integrate", "gold", "model", "viz")):
        from agri.spark_utils import get_spark
        spark = get_spark()
        if "bronze" in steps:
            from agri.cleaning import bronze; bronze.run(spark, cfg)
        if "silver" in steps:
            from agri.cleaning import silver; silver.run(spark, cfg)
        if "integrate" in steps:
            from agri.cleaning import integrate; integrate.run(spark, cfg)
        if "gold" in steps:
            from agri.features import gold; gold.run(spark, cfg)
        if "model" in steps:
            from agri.models import run as m; m.run(spark, cfg)
        if "viz" in steps:
            from agri.viz import run as v; v.run(spark, cfg)
    if "report" in steps:
        from agri import report; report.run(cfg)
    print("DONE")


if __name__ == "__main__":
    main()
