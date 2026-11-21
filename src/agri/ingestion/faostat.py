"""Download FAOSTAT bulk files (national level)."""
from __future__ import annotations
import io
import zipfile
import requests
from ..config import data_path


def download(cfg: dict) -> None:
    out = data_path(cfg, "raw", "faostat")
    out.mkdir(parents=True, exist_ok=True)
    for name, url in cfg["faostat"]["datasets"].items():
        print(f"[faostat] downloading {name} ...")
        r = requests.get(url, timeout=600)
        r.raise_for_status()
        with zipfile.ZipFile(io.BytesIO(r.content)) as z:
            for member in z.namelist():
                # keep only the main data file (skip Flags / AreaCodes / ItemCodes)
                if member.endswith(".csv") and "All_Data" in member:
                    target = out / f"faostat_{name}.csv"
                    target.write_bytes(z.read(member))
                    print(f"[faostat]   -> {target}")
