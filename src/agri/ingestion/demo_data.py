"""Synthetic dataset that mimics the *raw* shape of the real sources.

It lets you run and test the whole pipeline offline. Geometry = fake grid "provinces"
over Italy's bounding box (NOT real borders). Planted signals:
  * tomatoes shift north over time, olives expand south, maize declines
  * yield responds to temperature/precipitation
"""
from __future__ import annotations
import json
import numpy as np
import pandas as pd
from shapely.geometry import box, mapping

from ..config import data_path

CROPS_IT = {"wheat": "Frumento", "maize": "Mais", "rice": "Riso", "olives": "Olivo",
            "grapes": "Uva da vino", "tomatoes": "Pomodoro"}
CROPS_FAO = {"wheat": "Wheat", "maize": "Maize (corn)", "rice": "Rice", "olives": "Olives",
             "grapes": "Grapes", "tomatoes": "Tomatoes"}


def _provinces(n_cols=8, n_rows=6):
    lons = np.linspace(7.0, 18.5, n_cols + 1)
    lats = np.linspace(36.5, 46.5, n_rows + 1)
    rows = []
    code = 1
    for r in range(n_rows):
        for c in range(n_cols):
            lat_c = (lats[r] + lats[r + 1]) / 2
            region = "Nord (demo)" if lat_c > 43.5 else ("Centro (demo)" if lat_c > 40.5 else "Sud (demo)")
            rows.append(dict(COD_PROV=code, DEN_UTS=f"Prov_{code:03d}", REGIONE=region,
                             lat=lat_c, lon=(lons[c] + lons[c + 1]) / 2,
                             geom=box(lons[c], lats[r], lons[c + 1], lats[r + 1])))
            code += 1
    return rows


def generate(cfg: dict, seed: int = 7) -> None:
    rng = np.random.default_rng(seed)
    raw = data_path(cfg, "raw")
    for sub in ("istat", "faostat", "climate", "landcover", "boundaries"):
        (raw / sub).mkdir(parents=True, exist_ok=True)
    years = cfg["years"]["range"]
    y0 = years[0]
    provs = _provinces()

    # ---- boundaries (geojson, EPSG:4326) ----
    feats = [dict(type="Feature", geometry=mapping(p["geom"]),
                  properties={k: p[k] for k in ("COD_PROV", "DEN_UTS", "REGIONE")}) for p in provs]
    (raw / "boundaries" / "provinces_demo.geojson").write_text(
        json.dumps({"type": "FeatureCollection", "features": feats}), encoding="utf-8")

    # ---- climate + landcover ----
    clim, lc = [], []
    for p in provs:
        for y in years:
            t = 16 - 0.6 * (p["lat"] - 41) + 0.04 * (y - y0) + rng.normal(0, 0.4)
            pr = 800 - 3 * (y - y0) + 40 * (p["lat"] - 41) + rng.normal(0, 60)
            clim.append(dict(province_code=f"{p['COD_PROV']:03d}", year=y, t2m_mean_c=round(t, 3),
                             t2m_summer_c=round(t + 9.5, 3), precip_mm=round(max(pr, 150), 1)))
            lc.append(dict(province_code=f"{p['COD_PROV']:03d}", year=y,
                           cropland_pct=round(float(np.clip(45 - 0.25 * (y - y0) + rng.normal(0, 1.5), 5, 90)), 2)))
    clim = pd.DataFrame(clim)
    clim.to_csv(raw / "climate" / "climate_province_year.csv", index=False)
    pd.DataFrame(lc).to_csv(raw / "landcover" / "landcover_province_year.csv", index=False)
    cl = clim.set_index(["province_code", "year"])

    # ---- crops by province (ISTAT-like raw: ints w/o zero padding, quintals, Italian names) ----
    def suitability(crop, lat, t):
        if crop == "tomatoes":
            return np.exp(-((lat - (38.5 + 0.09 * t)) / 2.2) ** 2)
        if crop == "olives":
            return np.exp(-((lat - 38.0) / 3.0) ** 2) * (1 + 0.012 * t)
        if crop == "maize":
            return np.exp(-((lat - 45.0) / 2.0) ** 2) * (1 - 0.015 * t)
        if crop == "rice":
            return np.exp(-((lat - 45.3) / 0.9) ** 2)
        if crop == "wheat":
            return np.exp(-((lat - 41.0) / 3.5) ** 2) * (1 - 0.004 * t)
        return np.exp(-((lat - 42.5) / 4.0) ** 2)  # grapes

    base_area = {"wheat": 9000, "maize": 8000, "rice": 6000, "olives": 7000, "grapes": 5000, "tomatoes": 4000}
    base_yield = {"wheat": 3.5, "maize": 9.0, "rice": 6.0, "olives": 2.0, "grapes": 8.0, "tomatoes": 55.0}
    rows = []
    for p in provs:
        size = rng.uniform(0.6, 1.4)
        for crop, it in CROPS_IT.items():
            for y in years:
                t = y - y0
                area = base_area[crop] * size * suitability(crop, p["lat"], t) * rng.normal(1, 0.05)
                if area < 30:
                    continue
                c = cl.loc[(f"{p['COD_PROV']:03d}", y)]
                yld = base_yield[crop] * (1 + 0.008 * t) * (1 + 0.03 * (c.t2m_mean_c - 15)
                      - 0.0004 * (c.precip_mm - 800) * (-1 if crop == "rice" else 1)) * rng.normal(1, 0.04)
                rows.append(dict(COD_PROV=p["COD_PROV"], PROVINCIA=p["DEN_UTS"], REGIONE=p["REGIONE"],
                                 COLTURA=it, ANNO=y, SUPERFICIE_HA=area, PRODUZIONE_Q=area * yld * 10))
    df = pd.DataFrame(rows)
    # dirty it up on purpose so the cleaning step has work to do
    df["SUPERFICIE_HA"] = df["SUPERFICIE_HA"].round(1).astype(str)
    df["PRODUZIONE_Q"] = df["PRODUZIONE_Q"].round(1).astype(str)
    comma = rng.random(len(df)) < 0.1
    df.loc[comma, "SUPERFICIE_HA"] = df.loc[comma, "SUPERFICIE_HA"].str.replace(".", ",", regex=False)
    df = pd.concat([df, df.sample(40, random_state=1)], ignore_index=True)           # duplicates
    df.loc[df.sample(30, random_state=2).index, "SUPERFICIE_HA"] = ""               # missing
    df.loc[df.sample(5, random_state=3).index, "PRODUZIONE_Q"] = "-100"             # invalid
    df.to_csv(raw / "istat" / "istat_crops_demo.csv", index=False)

    # ---- FAOSTAT-like (national) ----
    num = df.drop_duplicates(["COD_PROV", "COLTURA", "ANNO"]).copy()
    num["a"] = pd.to_numeric(num["SUPERFICIE_HA"].str.replace(",", "."), errors="coerce")
    num["q"] = pd.to_numeric(num["PRODUZIONE_Q"], errors="coerce").clip(lower=0)
    inv = {v: k for k, v in CROPS_IT.items()}
    num["crop"] = num["COLTURA"].map(inv)
    nat = num.groupby(["crop", "ANNO"]).agg(a=("a", "sum"), q=("q", "sum")).reset_index()
    fao = []
    for _, r in nat.iterrows():
        fao.append(dict(Area="Italy", Item=CROPS_FAO[r.crop], Element="Area harvested", Year=r.ANNO, Unit="ha", Value=r.a))
        fao.append(dict(Area="Italy", Item=CROPS_FAO[r.crop], Element="Production", Year=r.ANNO, Unit="tonnes", Value=r.q / 10))
        fao.append(dict(Area="France", Item=CROPS_FAO[r.crop], Element="Production", Year=r.ANNO, Unit="tonnes", Value=1e6))
    pd.DataFrame(fao).to_csv(raw / "faostat" / "faostat_crops_demo.csv", index=False)
    pest, fert = [], []
    for y in years:
        pest.append(dict(Area="Italy", Item="Pesticides (total)", Element="Agricultural Use", Year=y, Unit="tonnes",
                         Value=60000 - 600 * (y - y0) + rng.normal(0, 1500)))
        fert.append(dict(Area="Italy", Item="Nutrient nitrogen N (total)", Element="Agricultural Use", Year=y, Unit="tonnes",
                         Value=900000 - 9000 * (y - y0) + rng.normal(0, 20000)))
    pd.DataFrame(pest).to_csv(raw / "faostat" / "faostat_pesticides_demo.csv", index=False)
    pd.DataFrame(fert).to_csv(raw / "faostat" / "faostat_fertilizers_demo.csv", index=False)
    print(f"[demo] raw demo data written to {raw}")
