import numpy as np
from src.models import fit_fixed_effects, knn_weights, morans_i
from src.synthetic import make_panel


def test_fixed_effects_recovers_true_beta():
    res = fit_fixed_effects(make_panel(n_prov=30, beta=0.5, seed=3), "y", ["x"])
    assert abs(res.params["x"] - 0.5) < 0.05 and res.pvalues["x"] < 0.01


def test_knn_weights_are_row_standardised():
    W = knn_weights(np.random.default_rng(0).uniform(size=(20, 2)), k=4)
    assert np.allclose(W.sum(axis=1), 1.0) and np.all(np.diag(W) == 0)


def test_morans_i_detects_spatial_clustering():
    rng = np.random.default_rng(0)
    xy = rng.uniform(0, 10, (80, 2))
    W = knn_weights(xy, 5)
    clustered = xy[:, 0] + rng.normal(0, 0.3, 80)       # smooth gradient
    noise = rng.normal(size=80)
    assert morans_i(clustered, W)["I"] > 0.5 and morans_i(clustered, W)["p_value"] < 0.01
    assert abs(morans_i(noise, W)["I"]) < 0.25
