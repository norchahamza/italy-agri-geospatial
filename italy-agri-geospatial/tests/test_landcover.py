import numpy as np
import pytest
from src.landcover import change_by_zone, change_summary, cropland_mask, transition_matrix


def test_rules_are_nested():
    a = np.array([10, 20, 30, 40, 50])
    assert cropland_mask(a, "strict").sum() == 2
    assert cropland_mask(a, "with_mosaic").sum() == 3
    assert cropland_mask(a, "broad").sum() == 4


def test_unknown_rule():
    with pytest.raises(ValueError):
        cropland_mask(np.array([10]), "nope")


def test_change_summary():
    t0 = np.array([10, 10, 50, 50])
    t1 = np.array([10, 50, 10, 50])
    s = change_summary(t0, t1, pixel_area_ha=2.0)
    assert s["persistence_ha"] == 2 and s["gain_ha"] == 2 and s["loss_ha"] == 2 and s["net_ha"] == 0


def test_net_equals_difference_of_totals():
    rng = np.random.default_rng(1)
    t0, t1 = rng.choice([10, 20, 50, 60], 500), rng.choice([10, 20, 50, 60], 500)
    s = change_summary(t0, t1)
    assert s["net_ha"] == s["cropland_t1_ha"] - s["cropland_t0_ha"]


def test_transition_matrix_sums_to_total_area():
    t0, t1 = np.array([10, 10, 50, 60]), np.array([10, 50, 50, 10])
    m = transition_matrix(t0, t1, pixel_area_ha=3.0)
    assert m.to_numpy().sum() == 12.0 and m.loc[10, 50] == 3.0


def test_change_by_zone_ignores_zone_zero():
    t0, t1 = np.array([10, 10, 50, 50]), np.array([50, 10, 10, 50])
    zones = np.array([1, 1, 2, 0])
    df = change_by_zone(t0, t1, zones).set_index("zone")
    assert df.loc[1, "loss_ha"] == 1 and df.loc[2, "gain_ha"] == 1 and 0 not in df.index
