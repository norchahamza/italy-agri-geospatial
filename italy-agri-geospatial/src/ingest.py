"""Download helpers for real data. NOT covered by offline tests: run them yourself and check the output.
Verify dataset names, versions and URLs on the provider pages before relying on them.

ISTAT agricultural statistics and administrative boundaries: download manually from istat.it / esploradati.istat.it
and put the files in data/raw/. Record the exact table, date and 'accessed' date for the Harvard references.
"""
import zipfile
from pathlib import Path
import requests
from src.config import RAW


def download_landcover(year: int, out_dir: Path = RAW, version: str | None = None) -> Path:
    """ESA CCI land cover from the Copernicus Climate Data Store (needs a free CDS account and ~/.cdsapirc).
    CCI land cover versions change over time (v2.0.7 up to 2015, v2.1.1 afterwards): document the break."""
    import cdsapi
    version = version or ("v2_0_7cds" if year <= 2015 else "v2_1_1")
    target = Path(out_dir) / f"landcover_{year}.zip"
    cdsapi.Client().retrieve("satellite-land-cover", {
        "variable": "all", "year": [str(year)], "version": [version], "format": "zip"}, str(target))
    return target


def download_faostat(url: str, out_dir: Path = RAW) -> Path:
    """Download a FAOSTAT bulk file. Copy the exact URL from the 'Bulk downloads' page of fao.org/faostat."""
    target = Path(out_dir) / Path(url).name
    r = requests.get(url, timeout=120)
    r.raise_for_status()
    target.write_bytes(r.content)
    if target.suffix == ".zip":
        with zipfile.ZipFile(target) as z:
            z.extractall(Path(out_dir))
    return target
