"""Pure pandas indicators (small data): CAGR and shift-share."""
from __future__ import annotations
import numpy as np
import pandas as pd


def cagr_table(df: pd.DataFrame, periods, value: str = "area_ha", smooth: int = 3,
               keys=("province_code", "crop")) -> pd.DataFrame:
    """CAGR between 3-year mean windows at the start and end of each period (less noisy than 2 single years)."""
    out = []
    for a, b in periods:
        v0 = df[df.year.between(a, a + smooth - 1)].groupby(list(keys))[value].mean().rename("v0")
        v1 = df[df.year.between(b - smooth + 1, b)].groupby(list(keys))[value].mean().rename("v1")
        m = pd.concat([v0, v1], axis=1).dropna().reset_index()
        n_years = ((b - smooth + 1) + b) / 2 - (a + (a + smooth - 1)) / 2
        ok = (m.v0 > 0) & (m.v1 > 0)
        m["cagr"] = np.where(ok, (m.v1 / m.v0.where(ok)) ** (1 / n_years) - 1, np.nan)
        m["abs_change"] = m.v1 - m.v0
        m["period"] = f"{a}-{b}"
        out.append(m)
    return pd.concat(out, ignore_index=True)


def shift_share(df: pd.DataFrame, y0: int, y1: int, value: str = "area_ha", smooth: int = 1) -> pd.DataFrame:
    """Classic shift-share of the change in crop area of each (province, crop) between y0 and y1.

    change = national_effect + crop_mix_effect + regional_competitive_effect  (exact identity)
      national  = E0 * g_nat                  (everything grows like total cultivated area)
      crop_mix  = E0 * (g_crop - g_nat)       (the crop is nationally growing/declining faster than average)
      regional  = E1 - E0 * (1 + g_crop)      (province did better/worse than the crop nationally -> relocation)
    """
    k = ["province_code", "crop"]
    e0 = df[df.year.between(y0, y0 + smooth - 1)].groupby(k)[value].mean().rename("e0")
    e1 = df[df.year.between(y1 - smooth + 1, y1)].groupby(k)[value].mean().rename("e1")
    m = pd.concat([e0, e1], axis=1).fillna(0).reset_index()
    nat0, nat1 = m.e0.sum(), m.e1.sum()
    g_nat = nat1 / nat0 - 1 if nat0 > 0 else 0.0
    c = m.groupby("crop")[["e0", "e1"]].sum()
    c["g_crop"] = np.where(c.e0 > 0, c.e1 / c.e0.where(c.e0 > 0) - 1, 0.0)
    m = m.merge(c[["g_crop"]], left_on="crop", right_index=True)
    m["national_effect"] = m.e0 * g_nat
    m["crop_mix_effect"] = m.e0 * (m.g_crop - g_nat)
    m["regional_effect"] = m.e1 - m.e0 * (1 + m.g_crop)
    m["total_change"] = m.e1 - m.e0
    m["period"] = f"{y0}-{y1}"
    return m
