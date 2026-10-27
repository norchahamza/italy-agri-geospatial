"""Synthetic data with a KNOWN effect, to test the pipeline before real data is ready."""
import numpy as np
import pandas as pd


def make_panel(n_prov: int = 40, y0: int = 1992, y1: int = 2022, beta: float = 0.5, seed: int = 0):
    rng = np.random.default_rng(seed)
    years = np.arange(y0, y1 + 1)
    coords = rng.uniform(0, 10, size=(n_prov, 2))
    alpha = rng.normal(0, 1, n_prov)
    gamma = rng.normal(0, 0.5, len(years))
    rows = []
    for i in range(n_prov):
        for t, yr in enumerate(years):
            x = rng.normal(0, 1) + 0.03 * t
            y = alpha[i] + gamma[t] + beta * x + rng.normal(0, 0.3)
            rows.append({"province": f"P{i:03d}", "year": int(yr), "x": x, "y": y,
                         "lon": coords[i, 0], "lat": coords[i, 1]})
    return pd.DataFrame(rows)


def make_crop_table(n_prov: int = 10, years=(1992, 2022), seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    crops = ["wheat", "maize", "olive", "grape", "vegetables"]
    rows = []
    for p in range(n_prov):
        base = rng.dirichlet(np.ones(len(crops))) * 10000
        for yr in years:
            drift = 1 + (yr - years[0]) / 100 * rng.normal(0, 1, len(crops))
            for c, a, d in zip(crops, base, drift):
                rows.append({"province": f"P{p:03d}", "year": yr, "crop": c, "area_ha": max(a * d, 0.0)})
    return pd.DataFrame(rows)
