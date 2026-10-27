import pandas as pd
import pytest
from src.crops import change_table, classify_change, hhi, location_quotient
from src.synthetic import make_crop_table


def test_hhi_single_crop_is_one_and_equal_split_is_inverse_k():
    df = pd.DataFrame({"province": ["A"] * 4 + ["B"], "year": [2000] * 5,
                       "crop": ["w", "m", "o", "g", "w"], "area_ha": [10, 10, 10, 10, 50]})
    h = hhi(df).set_index("province")["hhi"]
    assert h["A"] == pytest.approx(0.25) and h["B"] == pytest.approx(1.0)


def test_lq_is_one_when_province_mirrors_nation():
    df = pd.DataFrame({"province": ["A", "A", "B", "B"], "year": 2000,
                       "crop": ["w", "m", "w", "m"], "area_ha": [30, 70, 30, 70]})
    assert location_quotient(df)["lq"].round(6).eq(1.0).all()


def test_lq_above_one_for_specialised_province():
    df = pd.DataFrame({"province": ["A", "A", "B", "B"], "year": 2000,
                       "crop": ["w", "m", "w", "m"], "area_ha": [90, 10, 10, 90]})
    lq = location_quotient(df).set_index(["province", "crop"])["lq"]
    assert lq[("A", "w")] > 1 > lq[("A", "m")]


@pytest.mark.parametrize("s0,s1,label", [(0.0, 0.05, "emerged"), (0.05, 0.0, "abandoned"),
                                         (0.10, 0.15, "expanded"), (0.15, 0.10, "declined"),
                                         (0.10, 0.11, "stable")])
def test_classify_change(s0, s1, label):
    assert classify_change(s0, s1) == label


def test_change_table_shape():
    t = change_table(make_crop_table(), 1992, 2022)
    assert len(t) == 10 * 5 and set(t["label"]) <= {"emerged", "abandoned", "expanded", "declined", "stable"}
