"""Stratified sampling design and area-adjusted accuracy estimation
(after Olofsson et al., 2014, Remote Sensing of Environment 148, pp. 42-57)."""
import numpy as np
import pandas as pd


def sample_size(weights: dict, expected_ua: dict, target_se: float = 0.01, N: float | None = None) -> int:
    """Total sample size n ~ (sum W_i S_i)^2 / (S(O)^2 + (1/N) sum W_i S_i^2), S_i = sqrt(U_i (1-U_i)).
    weights: mapped area proportion per stratum; expected_ua: expected user's accuracy per stratum;
    target_se: desired standard error of overall accuracy."""
    keys = list(weights)
    W = np.array([weights[k] for k in keys], float)
    S = np.sqrt(np.array([expected_ua[k] * (1 - expected_ua[k]) for k in keys]))
    num = (W * S).sum() ** 2
    den = target_se ** 2 + (((W * S ** 2).sum() / N) if N else 0.0)
    return int(np.ceil(num / den))


def allocate(n: int, weights: dict, min_per_stratum: int = 50) -> dict:
    """Split n between strata proportionally, but never fewer than min_per_stratum
    (rare change classes need more than proportional allocation). The total may exceed n."""
    return {k: max(min_per_stratum, int(round(n * w))) for k, w in weights.items()}


def estimate(counts: pd.DataFrame, weights: dict) -> dict:
    """Area-adjusted accuracy and area estimates.
    counts: confusion matrix of sample counts, rows = map class, columns = reference class (same labels).
    weights: mapped area proportion W_i per map class."""
    classes = list(counts.index)
    n_i = counts.sum(axis=1).to_numpy(float)
    W = np.array([weights[c] for c in classes], float)
    p = (counts.to_numpy(float) / n_i[:, None]) * W[:, None]          # p_ij = W_i n_ij / n_i
    p_map, p_ref = p.sum(axis=1), p.sum(axis=0)
    diag = np.diag(p)
    U = np.divide(diag, p_map, out=np.zeros_like(diag), where=p_map > 0)   # user's accuracy
    P = np.divide(diag, p_ref, out=np.zeros_like(diag), where=p_ref > 0)   # producer's accuracy
    OA = diag.sum()
    u_i = np.diag(counts.to_numpy(float)) / n_i                      # within-stratum agreement
    var_oa = ((W ** 2) * u_i * (1 - u_i) / (n_i - 1)).sum()
    share = counts.to_numpy(float) / n_i[:, None]
    var_area = ((W[:, None] ** 2) * share * (1 - share) / (n_i[:, None] - 1)).sum(axis=0)
    return {
        "overall_accuracy": OA, "overall_accuracy_se": float(np.sqrt(var_oa)),
        "users_accuracy": dict(zip(classes, U)), "producers_accuracy": dict(zip(classes, P)),
        "area_proportion": dict(zip(classes, p_ref)),
        "area_proportion_se": dict(zip(classes, np.sqrt(var_area))),
        "area_proportion_ci95": {c: (p_ref[i] - 1.96 * np.sqrt(var_area[i]), p_ref[i] + 1.96 * np.sqrt(var_area[i]))
                                 for i, c in enumerate(classes)},
    }
