"""ERA5-Land climate from the Copernicus CDS + zonal statistics per province.

Setup: create a free account at cds.climate.copernicus.eu, accept the dataset licence, and
put your key in ~/.cdsapirc.  Requests are queued, so the first run can take a while.

ERA5-Land *monthly means*: t2m in Kelvin; tp = mean DAILY accumulation (metres) -> multiply by
days-in-month * 1000 to get mm per month. Coordinate names differ between CDS versions
(time vs valid_time) - handled below.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from ..config import data_path


def download(cfg: dict) -> None:
    import cdsapi
    c = cdsapi.Client()
    out = data_path(cfg, "raw", "climate", "era5")
    out.mkdir(parents=True, exist_ok=True)
    yr = cfg["copernicus"].get("years") or cfg["years"]
    years = list(range(yr["start"], yr["end"] + 1))
    step = cfg["copernicus"]["years_per_request"]
    for i in range(0, len(years), step):
        chunk = years[i:i + step]
        target = out / f"era5land_{chunk[0]}_{chunk[-1]}.nc"
        if target.exists():
            continue
        print(f"[era5] requesting {chunk[0]}-{chunk[-1]}")
        c.retrieve(cfg["copernicus"]["era5_dataset"], {
            "product_type": "monthly_averaged_reanalysis",
            "variable": ["2m_temperature", "total_precipitation"],
            "year": [str(y) for y in chunk],
            "month": [f"{m:02d}" for m in range(1, 13)],
            "time": "00:00",
            "area": cfg["copernicus"]["bbox_nwse"],
            "data_format": "netcdf",
            "download_format": "unarchived",
        }, str(target))


def zonal_stats(ds, provinces) -> pd.DataFrame:
    """ds: xarray.Dataset with t2m, tp, dims (time, latitude, longitude).
    provinces: GeoDataFrame (EPSG:4326) with province_code. Returns a province_code x year table."""
    import geopandas as gpd
    tname = "valid_time" if "valid_time" in ds.coords else "time"
    for dim in ("expver", "number"):                 # ERA5T/ensemble dims (not present in final monthly files)
        if dim in ds["t2m"].dims:
            ds = ds.mean(dim, skipna=True)
    lat, lon = ds["latitude"].values, ds["longitude"].values
    t = ds["t2m"].values - 273.15
    land = np.isfinite(t[0])                         # ERA5-Land is NaN over the sea: use land cells only
    LON, LAT = np.meshgrid(lon, lat)
    pts = gpd.GeoDataFrame({"iy": np.repeat(np.arange(len(lat)), len(lon)), "ix": np.tile(np.arange(len(lon)), len(lat))},
                           geometry=gpd.points_from_xy(LON.ravel(), LAT.ravel()), crs=4326)
    pts = pts[land[pts["iy"].to_numpy(), pts["ix"].to_numpy()]]
    joined = gpd.sjoin(pts, provinces[["province_code", "geometry"]], predicate="within", how="inner")
    cells = {k: g[["iy", "ix"]].to_numpy() for k, g in joined.groupby("province_code")}
    # provinces smaller than one grid cell: use the nearest grid point to the centroid
    missing = provinces[~provinces["province_code"].isin(cells)]
    if len(missing):
        cen = missing.to_crs(3035).copy()
        cen["geometry"] = cen.geometry.centroid
        near = gpd.sjoin_nearest(cen[["province_code", "geometry"]], pts.to_crs(3035), how="left")
        for code, g in near.groupby("province_code"):
            cells[code] = g[["iy", "ix"]].to_numpy()[:1]

    times = pd.to_datetime(ds[tname].values)
    dim = np.asarray(times.days_in_month)[:, None, None]
    pr = ds["tp"].values * dim * 1000.0          # mm / month
    out = []
    for code, idx in cells.items():
        ts = np.nanmean(t[:, idx[:, 0], idx[:, 1]], axis=1)
        ps = np.nanmean(pr[:, idx[:, 0], idx[:, 1]], axis=1)
        m = pd.DataFrame({"t": ts, "p": ps, "year": times.year, "month": times.month})
        ann = m.groupby("year").agg(t2m_mean_c=("t", "mean"), precip_mm=("p", "sum")).reset_index()
        jja = m[m["month"].isin([6, 7, 8])].groupby("year")["t"].mean().rename("t2m_summer_c").reset_index()
        ann = ann.merge(jja, on="year")
        ann.insert(0, "province_code", code)
        out.append(ann)
    return pd.concat(out, ignore_index=True)[["province_code", "year", "t2m_mean_c", "t2m_summer_c", "precip_mm"]]


def build_climate_table(cfg: dict, provinces) -> None:
    import xarray as xr
    files = sorted(data_path(cfg, "raw", "climate", "era5").glob("*.nc"))
    if not files:
        raise SystemExit("No ERA5 files found - run the climate download first (needs ~/.cdsapirc).")
    parts = [xr.open_dataset(f) for f in files]
    tname = "valid_time" if "valid_time" in parts[0].coords else "time"
    ds = xr.concat(parts, dim=tname).sortby(tname)
    df = zonal_stats(ds, provinces)
    target = data_path(cfg, "raw", "climate", "climate_province_year.csv")
    df.to_csv(target, index=False)
    print(f"[era5] zonal stats -> {target}")
