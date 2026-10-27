"""End-to-end smoke test on SYNTHETIC data: python -m scripts.run_demo"""
import numpy as np
from src.models import fit_fixed_effects, knn_weights, morans_i
from src.synthetic import make_panel
from src.viz import plot_residual_map

panel = make_panel(beta=0.5)
res = fit_fixed_effects(panel, "y", ["x"])
print(f"Estimated beta = {res.params['x']:.3f} (true 0.5), clustered SE = {res.bse['x']:.3f}")
panel["resid"] = res.resid
prov = panel.groupby("province").agg(lon=("lon", "first"), lat=("lat", "first"), resid=("resid", "mean")).reset_index()
print("Moran's I of mean residuals:", morans_i(prov["resid"].to_numpy(), knn_weights(prov[["lon", "lat"]].to_numpy())))
print("Map:", plot_residual_map(prov))
