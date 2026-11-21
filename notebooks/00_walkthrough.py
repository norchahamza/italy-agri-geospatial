# %% [markdown]
# # Walkthrough (jupytext "percent" format - open in VS Code / Jupyter)
# Explore pipeline outputs after `python scripts/run_pipeline.py --mode demo`.

# %%
import sys; sys.path.insert(0, "../src")
import pandas as pd, geopandas as gpd
from agri.config import load_config, data_path, out_path
cfg = load_config("demo")
gold = pd.read_parquet(data_path(cfg, "gold", "crop_province_year"))
gdf = gpd.read_parquet(data_path(cfg, "silver", "provinces.parquet"))
gold.head()

# %% Top specialised provinces for a crop in the last year
gold[(gold.crop == "tomatoes") & (gold.year == gold.year.max())].nlargest(10, "lq")[["province_name", "lq", "area_ha"]]

# %% Trend table
pd.read_csv(out_path(cfg, "tables", "trends_area.csv")).sort_values("sen_slope_pct_per_year").tail(10)
