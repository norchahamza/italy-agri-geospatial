import numpy as np
import pandas as pd
from agri.features.indicators import cagr_table, shift_share
from agri.models.trends import mann_kendall


def _df():
    rows = []
    for p, base in (("001", 100.0), ("002", 200.0)):
        for c, g in (("a", 0.05), ("b", -0.02)):
            for y in range(2000, 2021):
                rows.append((p, c, y, base * (1 + g) ** (y - 2000)))
    return pd.DataFrame(rows, columns=["province_code", "crop", "year", "area_ha"])


def test_shift_share_identity():
    s = shift_share(_df(), 2000, 2020)
    err = (s.national_effect + s.crop_mix_effect + s.regional_effect - s.total_change).abs().max()
    assert err < 1e-9


def test_cagr_recovers_growth():
    t = cagr_table(_df(), [(2000, 2020)], smooth=1)
    a = t[t.crop == "a"].cagr.iloc[0]
    assert abs(a - 0.05) < 1e-9


def test_mann_kendall_detects_trend_and_noise():
    inc = mann_kendall(np.arange(30) + np.random.default_rng(0).normal(0, 1, 30))
    assert inc["trend"] == "increasing" and inc["sen_slope"] > 0.8
    flat = mann_kendall(np.random.default_rng(1).normal(0, 1, 30))
    assert flat["trend"] == "no_trend"
    assert mann_kendall([1, 2, 3])["trend"] == "insufficient_data"
