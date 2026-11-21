"""Mann-Kendall trend test + Sen's slope (non-parametric, robust to outliers)."""
from __future__ import annotations
import numpy as np
import pandas as pd
from scipy.stats import norm


def mann_kendall(y, x=None, alpha: float = 0.05, min_n: int = 8) -> dict:
    y = np.asarray(y, float)
    x = np.arange(len(y), dtype=float) if x is None else np.asarray(x, float)
    ok = ~np.isnan(y)
    y, x = y[ok], x[ok]
    n = len(y)
    nan = dict(n=n, tau=np.nan, z=np.nan, p=np.nan, sen_slope=np.nan, trend="insufficient_data")
    if n < min_n:
        return nan
    iu = np.triu_indices(n, 1)
    dy = (y[None, :] - y[:, None])[iu]
    dx = (x[None, :] - x[:, None])[iu]
    s = np.sign(dy).sum()
    _, cnt = np.unique(y, return_counts=True)
    var = (n * (n - 1) * (2 * n + 5) - (cnt * (cnt - 1) * (2 * cnt + 5)).sum()) / 18.0
    z = 0.0 if (var <= 0 or s == 0) else (s - np.sign(s)) / np.sqrt(var)
    p = 2 * (1 - norm.cdf(abs(z)))
    slope = float(np.median(dy / dx))
    trend = "no_trend" if p >= alpha else ("increasing" if z > 0 else "decreasing")
    return dict(n=n, tau=s / (n * (n - 1) / 2), z=z, p=p, sen_slope=slope, trend=trend)


def run_trends(df: pd.DataFrame, value: str = "area_ha", min_years: int = 12) -> pd.DataFrame:
    rows = []
    for (prov, crop), g in df.sort_values("year").groupby(["province_code", "crop"]):
        if g[value].notna().sum() < min_years:
            continue
        r = mann_kendall(g[value].values, g["year"].values)
        mean = g[value].mean()
        r.update(province_code=prov, crop=crop, mean_value=mean,
                 sen_slope_pct_per_year=100 * r["sen_slope"] / mean if mean else np.nan)
        rows.append(r)
    return pd.DataFrame(rows)
