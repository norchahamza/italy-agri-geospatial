"""Download province boundaries: ISTAT shapefile zip, or a Eurostat GISCO NUTS geojson."""
from __future__ import annotations
import io
import zipfile
import requests
from ..config import data_path


def download(cfg: dict) -> None:
    out = data_path(cfg, "raw", "boundaries")
    out.mkdir(parents=True, exist_ok=True)
    url = cfg["boundaries"]["url"]
    r = requests.get(url, timeout=600)
    r.raise_for_status()
    if url.lower().endswith(".geojson"):
        (out / url.rsplit("/", 1)[-1]).write_bytes(r.content)
        print(f"[boundaries] saved {url.rsplit('/', 1)[-1]}")
        return
    with zipfile.ZipFile(io.BytesIO(r.content)) as z:
        z.extractall(out)
    print(f"[boundaries] extracted to {out}")
