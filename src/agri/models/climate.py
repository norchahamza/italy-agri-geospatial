"""Climate <-> production relationship.

1. Panel regression with province + year fixed effects (cluster-robust SE by province):
       log(yield) = b1*T + b2*T^2 + b3*P(100mm) + province FE + year FE
   NOTE: with year FE the model identifies the effect from *differences between provinces within the
   same year*. Use time_fe="trend" (province FE + linear trend) to keep the common climate signal.
2. Random Forest with a time-based split (train <= cutoff, test after) + permutation importance.
"""
from __future__ import annotations
import numpy as np
import pandas as pd


def fixed_effects(df: pd.DataFrame, crop: str, time_fe: str = "year") -> pd.DataFrame:
    import statsmodels.formula.api as smf
    d = df[(df.crop == crop)].dropna(subset=["yield_t_ha", "t2m_mean_c", "precip_mm"]).copy()
    d = d[d.yield_t_ha > 0]
    if d.province_code.nunique() < 5 or len(d) < 100:
        return pd.DataFrame()
    d["log_yield"] = np.log(d.yield_t_ha)
    d["t2m_sq"] = d.t2m_mean_c ** 2
    d["precip_100mm"] = d.precip_mm / 100.0
    tfe = "C(year)" if time_fe == "year" else "year"
    res = smf.ols(f"log_yield ~ t2m_mean_c + t2m_sq + precip_100mm + C(province_code) + {tfe}", data=d).fit(
        cov_type="cluster", cov_kwds={"groups": d.province_code.astype("category").cat.codes})
    keep = ["t2m_mean_c", "t2m_sq", "precip_100mm"]
    out = pd.DataFrame({"coef": res.params[keep], "std_err": res.bse[keep], "p_value": res.pvalues[keep]}).reset_index(names="term")
    out.insert(0, "crop", crop)
    out["n_obs"], out["r2"], out["time_fe"] = int(res.nobs), res.rsquared, time_fe
    return out


def random_forest(df: pd.DataFrame, train_until: int = 2014, seed: int = 42):
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.inspection import permutation_importance
    from sklearn.metrics import r2_score
    feats = ["t2m_mean_c", "t2m_summer_c", "precip_mm", "year", "lat", "lon"]
    if "cropland_pct" in df.columns:
        feats.append("cropland_pct")
    d = df.dropna(subset=feats + ["yield_t_ha"]).copy()
    d = d[d.yield_t_ha > 0]
    d["log_yield"] = np.log(d.yield_t_ha)
    X = pd.concat([d[feats], pd.get_dummies(d["crop"], prefix="crop", dtype=float)], axis=1)
    tr, te = d.year <= train_until, d.year > train_until
    if tr.sum() < 100 or te.sum() < 30:
        return pd.DataFrame(), {}
    rf = RandomForestRegressor(n_estimators=200, min_samples_leaf=3, n_jobs=-1, random_state=seed)
    rf.fit(X[tr], d.log_yield[tr])
    metrics = dict(r2_train=float(rf.score(X[tr], d.log_yield[tr])),
                   r2_test=float(r2_score(d.log_yield[te], rf.predict(X[te]))),
                   n_train=int(tr.sum()), n_test=int(te.sum()))
    pi = permutation_importance(rf, X[te], d.log_yield[te], n_repeats=10, random_state=seed, n_jobs=-1)
    imp = pd.DataFrame({"feature": X.columns, "importance": pi.importances_mean, "std": pi.importances_std})
    return imp.sort_values("importance", ascending=False), metrics
