# Databricks notebook source
# MAGIC %md
# MAGIC # Italy agriculture pipeline on Databricks
# MAGIC API (ISTAT, FAOSTAT, Eurostat, Copernicus ERA5) -> Bronze/Silver/Gold (Delta) -> models -> maps/report.
# MAGIC
# MAGIC **Setup (once)**
# MAGIC 1. Workspace -> Create -> **Git folder** -> `https://github.com/norchahamza/italy-agri-geospatial`, then open this notebook from the Git folder.
# MAGIC 2. Compute: a cluster with DBR 15.4 LTS or newer (single node is enough) or serverless. The compute needs **outbound internet** (ISTAT, FAOSTAT, GISCO, Copernicus).
# MAGIC 3. You need permission to create a schema and a volume in the catalog you choose (or point the widgets to an existing volume).
# MAGIC 4. Climate: put your Copernicus token in the `cds_token` widget, or in a secret `agri/cds_token` (recommended; do not commit tokens).
# MAGIC
# MAGIC Not tested on a real workspace by the authors: if a cell fails, send the error.

# COMMAND ----------
# MAGIC %pip install geopandas shapely libpysal esda statsmodels scikit-learn plotly folium cdsapi xarray netCDF4 pyyaml requests pyarrow

# COMMAND ----------
dbutils.library.restartPython()

# COMMAND ----------
dbutils.widgets.text("catalog", "main", "Catalog")
dbutils.widgets.text("schema", "agri", "Schema")
dbutils.widgets.text("volume", "data", "Volume")
dbutils.widgets.dropdown("mode", "real", ["demo", "real"], "Mode")
dbutils.widgets.dropdown("table_format", "delta", ["delta", "parquet"], "Table format")
dbutils.widgets.dropdown("run_climate", "no", ["no", "yes"], "Download ERA5 climate (1992-2024)")
dbutils.widgets.text("cds_token", "", "Copernicus token (or use secret agri/cds_token)")

# COMMAND ----------
import os
import sys
from pathlib import Path

CATALOG, SCHEMA, VOLUME = (dbutils.widgets.get(k) for k in ("catalog", "schema", "volume"))
MODE = dbutils.widgets.get("mode")
FMT = dbutils.widgets.get("table_format")
RUN_CLIMATE = dbutils.widgets.get("run_climate") == "yes"

REPO = str(Path(os.getcwd()).parent)               # this notebook lives in <repo>/databricks
sys.path.insert(0, REPO + "/src")

try:
    spark.sql(f"CREATE SCHEMA IF NOT EXISTS {CATALOG}.{SCHEMA}")
    spark.sql(f"CREATE VOLUME IF NOT EXISTS {CATALOG}.{SCHEMA}.{VOLUME}")
except Exception as e:
    print("Could not create schema/volume (maybe they already exist or you lack permission):", e)

ROOT = f"/Volumes/{CATALOG}/{SCHEMA}/{VOLUME}"
os.environ["AGRI_DATA_DIR"] = f"{ROOT}/data"
os.environ["AGRI_OUTPUT_DIR"] = f"{ROOT}/outputs"
os.environ["AGRI_TABLE_FORMAT"] = FMT
print("data ->", os.environ["AGRI_DATA_DIR"], "| outputs ->", os.environ["AGRI_OUTPUT_DIR"], "| format:", FMT)

# COMMAND ----------
# Copernicus credentials (only needed when run_climate = yes)
token = dbutils.widgets.get("cds_token")
if not token:
    try:
        token = dbutils.secrets.get("agri", "cds_token")
    except Exception:
        token = ""
if token:
    (Path.home() / ".cdsapirc").write_text(f"url: https://cds.climate.copernicus.eu/api\nkey: {token}\n")
    print("CDS credentials written")
elif RUN_CLIMATE:
    raise ValueError("run_climate = yes but no Copernicus token provided")

# COMMAND ----------
from agri import pipeline
from agri.config import load_config

cfg = load_config(MODE)

# 1) Collect from the APIs (demo mode generates synthetic data). ISTAT is rate limited: ~5-10 minutes.
pipeline.run(cfg, ["collect"], skip_climate=True)

# COMMAND ----------
# 2) Climate from Copernicus ERA5-Land (queued requests: minutes to hours). Skipped unless run_climate = yes.
if RUN_CLIMATE and MODE == "real":
    pipeline.run(cfg, ["climate"])

# COMMAND ----------
# 3) Bronze -> Silver -> Integration -> Gold -> models -> figures -> report
pipeline.run(cfg, ["bronze", "silver", "integrate", "gold", "model", "viz", "report"], spark=spark)

# COMMAND ----------
# 4) Register the gold tables in Unity Catalog (SQL access, Databricks Dashboards)
from agri.config import data_path

for t in ("crop_province_year", "province_diversity", "national_crop_year", "cagr", "shift_share"):
    (spark.read.format(FMT).load(str(data_path(cfg, "gold", t)))
          .write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(f"{CATALOG}.{SCHEMA}.gold_{MODE}_{t}"))
    print("table:", f"{CATALOG}.{SCHEMA}.gold_{MODE}_{t}")

# COMMAND ----------
# 5) Preview a map in the notebook (Plotly from CDN). Full outputs are in the Volume: Catalog -> Volumes -> outputs/<mode>/
import geopandas as gpd
from agri.viz import figures as F

gold = spark.read.format(FMT).load(str(data_path(cfg, "gold", "crop_province_year"))).toPandas()
gdf = gpd.read_parquet(data_path(cfg, "silver", "provinces.parquet"))
displayHTML(F.fig_lq_animation(gold, gdf, "olives").to_html(include_plotlyjs="cdn"))
