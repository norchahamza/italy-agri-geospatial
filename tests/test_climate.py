import numpy as np
import pandas as pd
from agri.models.climate import climate_trends


def test_climate_trends_recovers_warming():
    rng = np.random.default_rng(0)
    years = np.arange(1992, 2025)
    rows = []
    for code, base in (("A", 14.0), ("B", 12.0)):
        for y in years:
            rows.append(dict(province_code=code, year=y, t2m_mean_c=base + 0.04 * (y - 1992) + rng.normal(0, 0.15),
                             t2m_summer_c=base + 9, precip_mm=800 + rng.normal(0, 40)))
    out = climate_trends(pd.DataFrame(rows))
    t = out[(out.variable == "t2m_mean_c")]
    assert len(t) == 2 and (t.trend == "increasing").all()
    assert abs(t.sen_slope_per_decade.mean() - 0.4) < 0.1          # 0.04 C/yr = 0.4 C/decade
    assert (out[out.variable == "precip_mm"].trend == "no_trend").all()
