"""BRONZE: raw files stored as-is (all columns string) + lineage metadata."""
from __future__ import annotations
import re
from pyspark.sql import functions as F
from ..config import data_path
from ..spark_utils import write_table

# (bronze table, raw sub-folder, file glob, source label, encoding)
SOURCES = [
    ("istat_crops",     "istat",     "*.csv",                    "ISTAT",      "UTF-8"),
    ("fao_crops",       "faostat",   "faostat_crops*.csv",       "FAOSTAT",    "ISO-8859-1"),
    ("fao_pesticides",  "faostat",   "faostat_pesticides*.csv",  "FAOSTAT",    "ISO-8859-1"),
    ("fao_fertilizers", "faostat",   "faostat_fertilizers*.csv", "FAOSTAT",    "ISO-8859-1"),
    ("climate",         "climate",   "climate_province_year.csv", "Copernicus ERA5-Land", "UTF-8"),
    ("landcover",       "landcover", "*.csv",                    "ESA CCI Land Cover", "UTF-8"),
]


def _safe(c: str) -> str:      # parquet doesn't allow spaces/() in column names
    return re.sub(r"[^0-9A-Za-z_]+", "_", c).strip("_")


def run(spark, cfg: dict) -> None:
    for name, sub, glob, source, enc in SOURCES:
        folder = data_path(cfg, "raw", sub)
        if not list(folder.glob(glob)):
            print(f"[bronze] skip {name}: no file matching {folder / glob}")
            continue
        df = (spark.read.option("header", True).option("inferSchema", False)
              .option("encoding", enc).csv(str(folder / glob)))
        df = df.toDF(*[_safe(c) for c in df.columns])
        df = (df.withColumn("_ingestion_ts", F.current_timestamp())
                .withColumn("_source", F.lit(source))
                .withColumn("_file", F.col("_metadata.file_path")))
        write_table(df, data_path(cfg, "bronze", name), cfg["fmt"])
        print(f"[bronze] {name}: {df.count():,} rows")
