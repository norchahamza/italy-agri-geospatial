"""Auto-generates a first draft of the final report (markdown) from the result tables."""
from __future__ import annotations
import json
import pandas as pd
from .config import data_path, out_path


def _md(df: pd.DataFrame, cols, n=10, fmt=None) -> str:
    d = df[cols].head(n).copy()
    lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for _, r in d.iterrows():
        lines.append("| " + " | ".join(f"{r[c]:,.2f}" if isinstance(r[c], float) else str(r[c]) for c in cols) + " |")
    return "\n".join(lines)


MIN_HA = 500          # ignore tiny series in growth/decline rankings (a 20 ha -> 80 ha jump is not a trend)


def _names(cfg: dict) -> dict:
    p = data_path(cfg, "silver", "provinces.parquet")
    if not p.exists():
        return {}
    import geopandas as gpd
    g = gpd.read_parquet(p)
    return dict(zip(g.province_code, g.province_name))


def _label(df: pd.DataFrame, names: dict) -> pd.DataFrame:
    df = df.copy()
    df.insert(0, "province", df["province_code"].map(lambda c: f"{c} {names.get(c, '')}".strip()))
    return df


def run(cfg: dict) -> None:
    names = _names(cfg)
    t = lambda n: out_path(cfg, "tables", n)
    y0, y1 = cfg["years"]["start"], cfg["years"]["end"]
    merged = (cfg.get("boundaries") or {}).get("merge") or {}
    mnames = (cfg.get("boundaries") or {}).get("merge_names") or {}
    prov_note = "- Province boundaries changed during the period; reformed provinces were merged into stable units: " + (
        "; ".join(mnames.get(k, k) for k in merged) if merged else "none") + " (config/sources.yml, config/province_crosswalk.csv)."
    parts = [f"# Geospatial analytics of Italy's agricultural transformation ({y0}-{y1})",
             f"_Auto-generated draft - mode: **{cfg['mode']}**. Edit and complete the interpretation._\n"]
    if cfg["mode"] == "demo":
        parts.append("> **DEMO DATA**: synthetic numbers on fake provinces. Do not interpret as real findings.\n")
    if t("kpi_relocation.csv").exists():
        k = pd.read_csv(t("kpi_relocation.csv"), dtype={"province_code": str})
        k = _label(k, names)
        cols = ["province", "crop", "e0", "e1", "regional_effect"]
        parts += ["## 1. Where did crops relocate? (shift-share regional effect, hectares)",
                  "**Largest gains**", _md(k[k.kind == "relocation_gain"], cols),
                  "\n**Largest losses**", _md(k[k.kind == "relocation_loss"], cols)]
    if t("trends_area.csv").exists():
        tr = pd.read_csv(t("trends_area.csv"), dtype={"province_code": str})
        vc = tr.trend.value_counts().to_dict()
        big = _label(tr[tr.mean_value >= MIN_HA], names)
        cols = ["province", "crop", "mean_value", "sen_slope_pct_per_year", "p"]
        parts += ["\n## 2. Trends (Mann-Kendall on cultivated area)", f"Series by trend: {vc}",
                  f"(rankings only include series with mean area >= {MIN_HA} ha)",
                  "**Strongest growth (% / year)**",
                  _md(big[big.trend == "increasing"].sort_values("sen_slope_pct_per_year", ascending=False), cols),
                  "\n**Strongest decline (% / year)**",
                  _md(big[big.trend == "decreasing"].sort_values("sen_slope_pct_per_year"), cols)]
    if t("spatial_clusters.csv").exists():
        cl = pd.read_csv(t("spatial_clusters.csv"), dtype={"province_code": str})
        s = cl.groupby(["year", "lisa_cluster"]).size().unstack(fill_value=0)
        parts += ["\n## 3. Spatial clusters (Local Moran's I)", s.to_string()]
    if t("climate_trends.csv").exists():
        ct = pd.read_csv(t("climate_trends.csv"), dtype={"province_code": str})
        if len(ct):
            parts.append(f"\n## 3b. Climate trends ({ct.years.iloc[0]}, Mann-Kendall + Sen's slope per province)")
            for var, unit in (("t2m_mean_c", "C / decade"), ("t2m_summer_c", "C / decade"), ("precip_mm", "mm / decade")):
                v = ct[ct.variable == var]
                if len(v):
                    sig_up = int(((v.trend == "increasing")).sum())
                    sig_dn = int(((v.trend == "decreasing")).sum())
                    parts.append(f"- {var}: median {v.sen_slope_per_decade.median():+.2f} {unit}; "
                                 f"significant increase in {sig_up}/{len(v)} provinces, decrease in {sig_dn}")
    if t("climate_fixed_effects.csv").exists():
        fe = pd.read_csv(t("climate_fixed_effects.csv"))
        if len(fe):
            parts += ["\n## 4. Climate and yield (fixed-effects regression)", _md(fe, ["crop", "term", "coef", "p_value"], n=30)]
    if t("rf_metrics.json").exists():
        parts += ["\n## 5. Random-forest check (time-based split)", "```", t("rf_metrics.json").read_text(), "```"]
    parts += ["\n## 6. Limitations",
              "- FAOSTAT is national only; environmental links are trend-level, not province-level.",
              prov_note,
              "- Correlation with climate is not causation; technology, prices and policy are not modelled here.",
              "\n## 7. Strategic insights (to write)", "- Policymakers: ...", "- Agribusiness: ...", "- Investors: ..."]
    out_path(cfg, "final_report.md").write_text("\n".join(parts), encoding="utf-8")
    print(f"[report] {out_path(cfg, 'final_report.md')}")
