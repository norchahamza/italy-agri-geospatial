"""Explore ISTAT crop dataflows: which one has provinces and 1995+ data?
Run from the project root:  python scripts/explore_istat.py
Needs: pip install pandas requests
"""
import io
import re
import sys
import time
from pathlib import Path

import pandas as pd
import requests

BASE = "https://esploradati.istat.it/SDMXWS/rest"
CSV = {"Accept": "application/vnd.sdmx.data+csv;version=1.0.0"}
OUT = Path("data/real/raw/istat_explore")
OUT.mkdir(parents=True, exist_ok=True)

xml = requests.get(f"{BASE}/dataflow/IT1", headers={"Accept": "application/xml"}, timeout=120).text
ids = sorted(set(re.findall(r'Dataflow id="(101_1015_DF_DCSP_COLTIVAZIONI_\d+)"', xml)))
print("Dataflows found:", ids)

for i in ids:
    block = xml[xml.index(f'Dataflow id="{i}"'):][:3000]
    names = re.findall(r'<common:Name xml:lang="(\w+)">([^<]+)</common:Name>', block)
    print(f"\n=== {i} ===")
    for lang, n in names[:2]:
        print(f"  name[{lang}]: {n}")
    r = requests.get(f"{BASE}/data/{i}/all?startPeriod=1990&endPeriod=2026", headers=CSV, timeout=600)
    if r.status_code != 200 or not r.text.startswith("DATAFLOW"):
        print("  ! no data:", r.status_code, r.text[:120])
        time.sleep(15)
        continue
    (OUT / f"{i}.csv").write_text(r.text, encoding="utf-8")
    df = pd.read_csv(io.StringIO(r.text), dtype=str)
    print(f"  rows: {len(df):,}")
    print("  columns:", [c for c in df.columns if not c.startswith("NOTE")])
    for col in ("REF_AREA", "DATA_TYPE", "TYPE_OF_CROP"):
        if col in df:
            vals = sorted(df[col].dropna().unique())
            print(f"  {col}: {len(vals)} values, e.g. {vals[:12]}")
    if "TIME_PERIOD" in df:
        print("  years:", df.TIME_PERIOD.min(), "->", df.TIME_PERIOD.max())
    if "UNIT_MEAS" in df:
        print("  UNIT_MEAS:", df.UNIT_MEAS.dropna().unique()[:6], " UNIT_MULT:", df.UNIT_MULT.dropna().unique()[:6])
    time.sleep(15)   # ISTAT rate limit

print("\nFiles saved in", OUT)
