# Databricks notebook source
# MAGIC %md
# MAGIC # Italy agriculture pipeline on Databricks
# MAGIC 1. Clone the repo in Repos. 2. Create a Volume for data. 3. Run this notebook (cluster DBR 14+).

# COMMAND ----------
# MAGIC %pip install geopandas shapely libpysal esda statsmodels scikit-learn plotly folium cdsapi xarray netCDF4 pyyaml requests

# COMMAND ----------
import os, sys
REPO = os.getcwd().rsplit("/databricks", 1)[0]          # repo root when run from Repos
sys.path.insert(0, REPO + "/src")
os.environ["AGRI_DATA_DIR"] = "/Volumes/main/agri/data"        # <- change to your catalog/schema/volume
os.environ["AGRI_OUTPUT_DIR"] = "/Volumes/main/agri/outputs"
os.environ["AGRI_TABLE_FORMAT"] = "delta"                     # Delta tables for bronze/silver/gold

# COMMAND ----------
from agri.config import load_config
from agri.cleaning import bronze, silver, integrate
from agri.features import gold
from agri.models import run as models
from agri.viz import run as viz
from agri import report
from agri.ingestion import demo_data

MODE = "demo"            # switch to "real" after filling config/sources.yml and running collection
cfg = load_config(MODE)
if MODE == "demo":
    demo_data.generate(cfg)

# COMMAND ----------
for step in (bronze, silver, integrate, gold, models, viz):
    step.run(spark, cfg)
report.run(cfg)
