from agri.config import load_config
from agri.cleaning.silver import transform_istat_sdmx


def test_real_mode_overrides():
    cfg = load_config("real")
    assert cfg["years"]["start"] == 2006 and cfg["istat"]["format"] == "sdmx"
    assert cfg["years"]["range"][0] == 2006
    assert load_config("demo")["istat"]["format"] == "wide"       # demo untouched


def test_sdmx_transform(spark):
    cfg = load_config("real")
    H = "REF_AREA string, DATA_TYPE string, TYPE_OF_CROP string, DESTINATION_WINEGRAPES string, TIME_PERIOD string, OBS_VALUE string"
    rows = [
        # province ITC11: wheat = COMMEAT + WHEATD (summed); production in quintals
        ("ITC11", "ART", "COMMEAT", "ALL", "2020", "100"), ("ITC11", "ART", "WHEATD", "ALL", "2020", "50"),
        ("ITC11", "TP_QUIN_EXT", "COMMEAT", "ALL", "2020", "6000"), ("ITC11", "TP_QUIN_EXT", "WHEATD", "ALL", "2020", "2500"),
        ("ITC11", "ART", "COMMEAT", "ALL", "2020", "100"),                      # exact duplicate -> dropped
        ("ITC1", "ART", "COMMEAT", "ALL", "2020", "999"),                       # NUTS2 -> excluded
        ("IT", "ART", "COMMEAT", "ALL", "2020", "999"),                         # national -> excluded
        ("ITC11", "ART", "OLIVO", "ALL", "2020", "7"),                          # split code, not mapped -> excluded
        ("ITC11", "ART", "WINEES", "PDO", "2020", "5"),                         # other destination -> excluded
        ("ITC11", "ART_ARE", "COMMEAT", "ALL", "2020", "5000"),                 # other data type -> excluded
        ("IT108", "ART", "RICE", "ALL", "2020", "12,5"),                        # ISTAT own province code, decimal comma
    ]
    out = {(r.province_code, r.crop): r for r in transform_istat_sdmx(spark.createDataFrame(rows, H), cfg).collect()}
    w = out[("ITC11", "wheat")]
    assert w.area_ha == 150 and w.production_q == 8500 and w.year == 2020
    assert ("ITC1", "wheat") not in out and ("IT", "wheat") not in out
    assert ("ITC11", "olives") not in out and ("ITC11", "grapes") not in out
    assert out[("IT108", "rice")].area_ha == 12.5
