"""Download the code lists of the ISTAT crop dataflow and translate DATA_TYPE / TYPE_OF_CROP codes.
Run from the project root, AFTER f1.csv exists:  python scripts/istat_codelists.py
"""
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pandas as pd
import requests

BASE = "https://esploradati.istat.it/SDMXWS/rest"
DF = "101_1015_DF_DCSP_COLTIVAZIONI_1"
OUT = Path("data/real/raw/istat_explore")
XML_LANG = "{http://www.w3.org/XML/1998/namespace}lang"
KEYWORDS = r"frument|grano|mais|granturco|riso|oliv|uva|vite|pomodor|girasole|barbabietol|wheat|maize|rice|olive|grape|tomato|sunflower|sugar"


def local(tag):
    return tag.split("}")[-1]


def parse_codelists(xml_text):
    root = ET.fromstring(xml_text)
    rows = []
    for cl in root.iter():
        if local(cl.tag) != "Codelist":
            continue
        for code in cl:
            if local(code.tag) != "Code":
                continue
            names = {n.get(XML_LANG): (n.text or "") for n in code if local(n.tag) == "Name"}
            rows.append(dict(codelist=cl.get("id"), code=code.get("id"),
                             name_en=names.get("en", ""), name_it=names.get("it", "")))
    return pd.DataFrame(rows)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    cl = pd.DataFrame()
    for ref in ("descendants", "all"):
        r = requests.get(f"{BASE}/dataflow/IT1/{DF}/1.0?references={ref}",
                         headers={"Accept": "application/xml"}, timeout=300)
        if r.status_code == 200:
            cl = parse_codelists(r.text)
        if len(cl):
            break
    if cl.empty:
        sys.exit("Could not read code lists from the API (try again later).")
    cl.to_csv(OUT / "istat_codelists.csv", index=False, encoding="utf-8")
    print(f"{cl.codelist.nunique()} code lists, {len(cl)} codes -> {OUT / 'istat_codelists.csv'}")

    f1 = next((p for p in (OUT / "f1.csv", Path("f1.csv")) if p.exists()), None)
    if f1 is None:
        sys.exit("f1.csv not found (run the curl for COLTIVAZIONI_1 / 2020 first).")
    df = pd.read_csv(f1, dtype=str, usecols=["REF_AREA", "DATA_TYPE", "TYPE_OF_CROP", "UNIT_MEAS", "UNIT_MULT"])

    def label(codes):
        sub = cl[cl.code.isin(codes)].drop_duplicates("code")
        return sub.set_index("code")[["name_en", "name_it"]]

    print("\n=== DATA_TYPE ===")
    print(label(df.DATA_TYPE.dropna().unique()).to_string())
    print("\nUNIT_MEAS:", df.UNIT_MEAS.dropna().unique()[:10], " UNIT_MULT:", df.UNIT_MULT.dropna().unique()[:10])

    crops = label(df.TYPE_OF_CROP.dropna().unique())
    print(f"\n=== TYPE_OF_CROP: {df.TYPE_OF_CROP.nunique()} codes, {len(crops)} with a label ===")
    hit = crops[(crops.name_en + " " + crops.name_it).str.contains(KEYWORDS, case=False, regex=True)]
    print(hit.to_string())

    print("\n=== odd REF_AREA codes ===")
    odd = sorted(c for c in df.REF_AREA.dropna().unique() if c.startswith("IT1"))
    print(label(odd).to_string())


if __name__ == "__main__":
    main()
