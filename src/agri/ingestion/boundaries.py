"""Download ISTAT province boundaries (shapefile zip)."""
from __future__ import annotations
import io
import zipfile
import requests
from ..config import data_path


def download(cfg: dict) -> None:
    out = data_path(cfg, "raw", "boundaries")
    out.mkdir(parents=True, exist_ok=True)
    r = requests.get(cfg["boundaries"]["url"], timeout=600)
    r.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(r.content)) as z:
        z.extractall(out)
    print(f"[boundaries] extracted to {out}  (the province shapefile is the *ProvCM* / *Prov* one)")
