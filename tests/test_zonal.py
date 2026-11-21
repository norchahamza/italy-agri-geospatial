import numpy as np
import pandas as pd
import geopandas as gpd
import xarray as xr
from shapely.geometry import box
from agri.ingestion.copernicus import zonal_stats


def test_zonal_stats_synthetic():
    lat = np.arange(46.0, 44.0, -0.5)
    lon = np.arange(8.0, 10.0, 0.5)
    times = pd.date_range("2000-01-01", "2001-12-01", freq="MS")
    t = np.full((len(times), len(lat), len(lon)), 273.15 + 10.0)
    tp = np.full_like(t, 0.002)          # 2 mm/day
    ds = xr.Dataset({"t2m": (("valid_time", "latitude", "longitude"), t),
                     "tp": (("valid_time", "latitude", "longitude"), tp)},
                    coords={"valid_time": times, "latitude": lat, "longitude": lon})
    prov = gpd.GeoDataFrame({"province_code": ["001", "002"]},
                            geometry=[box(7.9, 44.9, 9.1, 46.1), box(9.2, 44.2, 9.4, 44.4)], crs=4326)  # 2nd is tiny
    out = zonal_stats(ds, prov)
    assert set(out.province_code) == {"001", "002"}
    assert np.allclose(out.t2m_mean_c, 10.0)
    assert np.allclose(out.precip_mm, 2 * 365, atol=2)       # ~730 mm / year
