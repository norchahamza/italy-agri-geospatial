"""Crop specialisation indicators from a province-year-crop area table.

Expected columns: province, year, crop, area_ha
"""
import numpy as np
import pandas as pd


def location_quotient(df: pd.DataFrame) -> pd.DataFrame:
    """LQ = (province share of crop c in its crop area) / (national share of crop c).
    LQ > 1 means the province is more specialised in c than Italy as a whole."""
    d = df.copy()
    prov_tot = d.groupby(["province", "year"])["area_ha"].transform("sum")
    nat_crop = d.groupby(["year", "crop"])["area_ha"].transform("sum")
    nat_tot = d.groupby("year")["area_ha"].transform("sum")
    d["share"] = d["area_ha"] / prov_tot
    d["lq"] = d["share"] / (nat_crop / nat_tot)
    return d


def hhi(df: pd.DataFrame) -> pd.DataFrame:
    """Herfindahl-Hirschman index per province-year: sum of squared crop shares (1/k..1)."""
    d = df.copy()
    d["share"] = d["area_ha"] / d.groupby(["province", "year"])["area_ha"].transform("sum")
    out = d.groupby(["province", "year"])["share"].apply(lambda s: float(np.sum(s ** 2)))
    return out.rename("hhi").reset_index()


def classify_change(share_t0: float, share_t1: float, emerge_level: float = 0.02,
                    absent_level: float = 0.005, delta: float = 0.02) -> str:
    """Label a province-crop trajectory. All thresholds are placeholders: justify and
    test them in the report (sensitivity analysis)."""
    if share_t0 < absent_level and share_t1 >= emerge_level:
        return "emerged"
    if share_t0 >= emerge_level and share_t1 < absent_level:
        return "abandoned"
    d = share_t1 - share_t0
    if d >= delta:
        return "expanded"
    if d <= -delta:
        return "declined"
    return "stable"


def change_table(df: pd.DataFrame, year0: int, year1: int, **kw) -> pd.DataFrame:
    """Share change and label for every province-crop between two years (average the years first if noisy)."""
    d = df.copy()
    d["share"] = d["area_ha"] / d.groupby(["province", "year"])["area_ha"].transform("sum")
    p = d.pivot_table(index=["province", "crop"], columns="year", values="share", fill_value=0.0)
    out = pd.DataFrame({"share_t0": p[year0], "share_t1": p[year1]})
    out["delta"] = out["share_t1"] - out["share_t0"]
    out["label"] = [classify_change(a, b, **kw) for a, b in zip(out["share_t0"], out["share_t1"])]
    return out.reset_index()
