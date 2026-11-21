"""Spatial clustering of crop specialisation: Local Moran's I (LISA) and Getis-Ord Gi*,
plus the movement of each crop's centre of gravity."""
from __future__ import annotations
import numpy as np
import pandas as pd

LISA_LABELS = {1: "High-High", 2: "Low-High", 3: "Low-Low", 4: "High-Low"}


def build_weights(gdf, k: int = 5):
    """k-nearest-neighbour weights on centroids (EPSG:3035). KNN avoids 'islands' (Sardinia, Sicily)."""
    from libpysal.weights import KNN
    g = gdf.to_crs(3035)
    c = np.c_[g.geometry.centroid.x, g.geometry.centroid.y]
    w = KNN.from_array(c, k=k)
    w.transform = "R"
    return w


def local_clusters(gold: pd.DataFrame, gdf, crop: str, year: int, value: str = "lq",
                   k: int = 5, permutations: int = 999, seed: int = 42, alpha: float = 0.05) -> pd.DataFrame:
    from esda.moran import Moran_Local
    from esda.getisord import G_Local
    gdf = gdf.reset_index(drop=True)
    s = gold[(gold.crop == crop) & (gold.year == year)].groupby("province_code")[value].mean()
    y = gdf["province_code"].map(s).fillna(0.0).to_numpy(float)     # crop absent => LQ 0
    if np.nanstd(y) == 0:
        return pd.DataFrame()
    w = build_weights(gdf, k)
    li = Moran_Local(y, w, permutations=permutations, seed=seed)
    gi = G_Local(y, w, transform="R", star=True, permutations=permutations, seed=seed)
    sig = li.p_sim < alpha
    out = pd.DataFrame({
        "province_code": gdf["province_code"], "crop": crop, "year": year, value: y,
        "local_moran_I": li.Is, "lisa_p": li.p_sim,
        "lisa_cluster": np.where(sig, pd.Series(li.q).map(LISA_LABELS), "Not significant"),
        "gi_z": gi.Zs, "gi_p": gi.p_sim,
        "hotspot": np.where(gi.p_sim < alpha, np.where(gi.Zs > 0, "Hot spot", "Cold spot"), "Not significant"),
    })
    return out


def all_clusters(gold, gdf, crops, years, **kw) -> pd.DataFrame:
    parts = [local_clusters(gold, gdf, c, y, **kw) for c in crops for y in years]
    return pd.concat([p for p in parts if len(p)], ignore_index=True)


def crop_centroids(gold: pd.DataFrame) -> pd.DataFrame:
    """Area-weighted centre of gravity (lat/lon) of each crop per year -> tracks geographic shifts."""
    d = gold.dropna(subset=["area_ha", "lat", "lon"]).copy()
    d["wlat"], d["wlon"] = d.lat * d.area_ha, d.lon * d.area_ha
    g = d.groupby(["crop", "year"]).agg(w=("area_ha", "sum"), wlat=("wlat", "sum"), wlon=("wlon", "sum")).reset_index()
    g["centroid_lat"], g["centroid_lon"] = g.wlat / g.w, g.wlon / g.w
    return g[["crop", "year", "centroid_lat", "centroid_lon"]]
