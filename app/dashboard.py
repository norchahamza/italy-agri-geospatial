"""Streamlit dashboard.   streamlit run app/dashboard.py   (run the pipeline first)"""
import sys
from pathlib import Path

import geopandas as gpd
import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from agri.config import data_path, load_config, out_path  # noqa: E402
from agri.viz import figures as F  # noqa: E402

st.set_page_config(page_title="Italy agriculture 1995-2024", layout="wide")
mode = st.sidebar.selectbox("Data mode", ["demo", "real"])
cfg = load_config(mode)


@st.cache_data
def load(mode):
    c = load_config(mode)
    rd = lambda *p: pd.read_parquet(data_path(c, *p))
    gdf = gpd.read_parquet(data_path(c, "silver", "provinces.parquet"))
    return rd("gold", "crop_province_year"), rd("gold", "national_crop_year"), rd("gold", "province_diversity"), gdf


try:
    gold, nat, div, gdf = load(mode)
except Exception as e:
    st.error(f"No data for mode '{mode}'. Run: python scripts/run_pipeline.py --mode {mode}\n\n{e}")
    st.stop()

if mode == "demo":
    st.warning("Synthetic demo data - not real findings.")
st.title("Geospatial analytics of Italy's agricultural transformation")
crop = st.sidebar.selectbox("Crop", sorted(gold.crop.unique()))

tab1, tab2, tab3, tab4 = st.tabs(["Map (LQ over time)", "National trends", "Specialisation & shifts", "Climate"])
with tab1:
    st.plotly_chart(F.fig_lq_animation(gold, gdf, crop), use_container_width=True)
with tab2:
    st.plotly_chart(F.fig_national_trends(nat), use_container_width=True)
with tab3:
    st.plotly_chart(F.fig_hhi(div), use_container_width=True)
    p = out_path(cfg, "tables", "crop_centroids.csv")
    if p.exists():
        st.plotly_chart(F.fig_centroids(pd.read_csv(p)), use_container_width=True)
with tab4:
    p = out_path(cfg, "tables", "climate_fixed_effects.csv")
    if p.exists():
        fe = pd.read_csv(p)
        st.plotly_chart(F.fig_climate_coefs(fe), use_container_width=True)
        st.dataframe(fe)
    p = out_path(cfg, "tables", "rf_importance.csv")
    if p.exists():
        st.subheader("Random-forest permutation importance")
        st.dataframe(pd.read_csv(p))
