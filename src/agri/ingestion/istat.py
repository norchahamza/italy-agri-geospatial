"""ISTAT SDMX access (esploradati.istat.it).

NOTE: ISTAT's API is rate limited (a few requests/minute). The dataflow ID changes between
releases, so list them first:   python scripts/run_pipeline.py --list-istat-dataflows
Alternative (always works): download the CSV manually from esploradati.istat.it and drop it in
data/real/raw/istat/ , then adjust `istat.columns` in config/sources.yml.
"""
from __future__ import annotations
import re
import requests
from ..config import data_path

CSV_ACCEPT = {"Accept": "application/vnd.sdmx.data+csv;version=1.0.0"}


def list_dataflows(cfg: dict, pattern: str = r"coltiv|agric|produzion|superfic") -> None:
    url = f"{cfg['istat']['sdmx_base']}/dataflow/IT1"
    r = requests.get(url, timeout=120)
    r.raise_for_status()
    for m in re.finditer(r'<str:Dataflow id="([^"]+)".*?<com:Name[^>]*>([^<]+)</com:Name>', r.text, re.S):
        if re.search(pattern, m.group(2), re.I):
            print(f"{m.group(1):40s} {m.group(2)}")


def download(cfg: dict) -> None:
    icfg = cfg["istat"]
    out = data_path(cfg, "raw", "istat")
    out.mkdir(parents=True, exist_ok=True)
    if icfg["dataflow"] == "REPLACE_ME":
        if any(out.glob("*.csv")):
            print("[istat] dataflow not set but manual CSV found in raw/istat -> using it")
            return
        raise SystemExit("Set istat.dataflow in config/sources.yml (see --list-istat-dataflows) "
                         "or place a CSV in " + str(out))
    key = icfg.get("key") or "all"
    url = (f"{icfg['sdmx_base']}/data/{icfg['dataflow']}/{key}"
           f"?startPeriod={cfg['years']['start']}&endPeriod={cfg['years']['end']}")
    print(f"[istat] GET {url}")
    r = requests.get(url, headers=CSV_ACCEPT, timeout=600)
    r.raise_for_status()
    (out / f"{icfg['dataflow']}.csv").write_bytes(r.content)
