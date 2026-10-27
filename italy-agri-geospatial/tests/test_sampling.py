import pandas as pd
import pytest
from src.sampling import allocate, estimate, sample_size


def test_hand_computed_example():
    counts = pd.DataFrame([[45, 5], [10, 40]], index=["crop", "other"], columns=["crop", "other"])
    r = estimate(counts, {"crop": 0.5, "other": 0.5})
    assert r["overall_accuracy"] == pytest.approx(0.85)
    assert r["area_proportion"]["crop"] == pytest.approx(0.55)
    assert r["users_accuracy"]["crop"] == pytest.approx(0.9)
    assert r["producers_accuracy"]["crop"] == pytest.approx(0.45 / 0.55)
    assert sum(r["area_proportion"].values()) == pytest.approx(1.0)


def test_perfect_map():
    counts = pd.DataFrame([[50, 0], [0, 50]], index=["a", "b"], columns=["a", "b"])
    r = estimate(counts, {"a": 0.3, "b": 0.7})
    assert r["overall_accuracy"] == 1.0 and r["overall_accuracy_se"] == 0.0


def test_sample_size_grows_when_target_se_shrinks():
    W, U = {"a": 0.5, "b": 0.5}, {"a": 0.8, "b": 0.8}
    assert sample_size(W, U, 0.005) > sample_size(W, U, 0.01)
    assert sample_size(W, U, 0.01) == 1600   # (0.5*0.4+0.5*0.4)^2 / 0.01^2 = 0.16/0.0001


def test_allocate_has_minimum_for_rare_classes():
    a = allocate(400, {"stable": 0.97, "gain": 0.03}, min_per_stratum=50)
    assert a["gain"] == 50 and a["stable"] > 300
