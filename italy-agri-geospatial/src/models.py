"""Driver analysis: panel regression with fixed effects and spatial autocorrelation checks."""
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf


def fit_fixed_effects(panel: pd.DataFrame, y: str, X: list[str], entity: str = "province", time: str = "year"):
    """OLS with entity and time fixed effects (dummies) and standard errors clustered by entity.
    Coefficients are ASSOCIATIONS, not causal effects. Nationwide policies are absorbed by the time effects."""
    formula = f"{y} ~ {' + '.join(X)} + C({entity}) + C({time})"
    cluster = pd.factorize(panel[entity])[0]
    return smf.ols(formula, data=panel).fit(cov_type="cluster", cov_kwds={"groups": cluster})


def knn_weights(coords: np.ndarray, k: int = 5) -> np.ndarray:
    """Row-standardised k-nearest-neighbour spatial weights matrix (n x n)."""
    coords = np.asarray(coords, float)
    d = np.linalg.norm(coords[:, None, :] - coords[None, :, :], axis=2)
    np.fill_diagonal(d, np.inf)
    W = np.zeros_like(d)
    for i, row in enumerate(d):
        W[i, np.argsort(row)[:k]] = 1.0
    return W / W.sum(axis=1, keepdims=True)


def morans_i(values: np.ndarray, W: np.ndarray, permutations: int = 999, seed: int = 0) -> dict:
    """Global Moran's I with a permutation p-value (two-sided). Use W built on the same units."""
    x = np.asarray(values, float)
    z = x - x.mean()
    denom = (z ** 2).sum()
    stat = lambda v: (len(v) / W.sum()) * (v @ W @ v) / denom
    I = stat(z)
    rng = np.random.default_rng(seed)
    sims = np.array([stat(rng.permutation(z)) for _ in range(permutations)])
    p = (1 + (np.abs(sims - sims.mean()) >= abs(I - sims.mean())).sum()) / (permutations + 1)
    return {"I": float(I), "expected": float(-1 / (len(x) - 1)), "p_value": float(p)}
