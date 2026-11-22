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
    """SDMX format: one request per year (the full 2006-2024 request is too heavy for ISTAT's API)."""
    icfg = cfg["istat"]
    out = data_path(cfg, "raw", "istat")
    out.mkdir(parents=True, exist_ok=True)
    if icfg["dataflow"] == "REPLACE_ME":
        if any(out.glob("*.csv")):
            print("[istat] dataflow not set but manual CSV found in raw/istat -> using it")
            return
        raise SystemExit("Set istat.dataflow in config/sources.yml or place a CSV in " + str(out))
    import time
    for year in cfg["years"]["range"]:
        target = out / f"istat_{icfg['dataflow']}_{year}.csv"
        if target.exists():
            continue
        url = f"{icfg['sdmx_base']}/data/{icfg['dataflow']}/all?startPeriod={year}&endPeriod={year}"
        r = None
        for attempt in range(6):
            wait = 30 * (attempt + 1)
            try:
                r = requests.get(url, headers=CSV_ACCEPT, timeout=900)
                if r.status_code == 200:
                    break
                print(f"[istat] {year}: HTTP {r.status_code}, retry in {wait}s")
            except requests.exceptions.RequestException as e:      # connection cut, timeout...
                print(f"[istat] {year}: network error ({type(e).__name__}), retry in {wait}s")
            r = None
            time.sleep(wait)
        if r is None:
            raise SystemExit(f"ISTAT request failed for {year} after 6 attempts - just re-run, finished years are skipped")
        if not r.text.startswith("DATAFLOW"):
            print(f"[istat] {year}: no records ({r.text[:40]!r}) - skipped")
        else:
            target.write_bytes(r.content)
            print(f"[istat] {year}: {r.text.count(chr(10)):,} rows -> {target.name}")
        time.sleep(icfg.get("request_pause_s", 13))
