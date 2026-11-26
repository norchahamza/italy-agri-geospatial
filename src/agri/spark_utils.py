"""SparkSession + table IO helpers (local Spark or Databricks)."""
from __future__ import annotations
import os
import pandas as pd


def get_spark(app: str = "italy-agri"):
    from pyspark.sql import SparkSession
    b = SparkSession.builder.appName(app)
    if not os.environ.get("DATABRICKS_RUNTIME_VERSION"):      # local run
        b = (b.master("local[*]")
              .config("spark.sql.shuffle.partitions", "8")
              .config("spark.sql.session.timeZone", "UTC")
              .config("spark.ui.enabled", "false")
              .config("spark.driver.memory", os.environ.get("SPARK_DRIVER_MEMORY", "2g")))
    spark = b.getOrCreate()
    try:
        spark.sparkContext.setLogLevel("ERROR")
    except Exception:                      # serverless / shared clusters do not expose sparkContext
        pass
    return spark


def write_table(df, path, fmt: str = "parquet") -> None:
    w = df.write.format(fmt).mode("overwrite")
    if fmt == "delta":
        w = w.option("overwriteSchema", "true")
    w.save(str(path))


def read_table(spark, path, fmt: str = "parquet"):
    return spark.read.format(fmt).load(str(path))


def read_pandas(spark, path, fmt: str = "parquet") -> pd.DataFrame:
    return read_table(spark, path, fmt).toPandas()
