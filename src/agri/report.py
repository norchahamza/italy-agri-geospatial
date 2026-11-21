"""Auto-generates a first draft of the final report (markdown) from the result tables."""
from __future__ import annotations
import json
import pandas as pd
from .config import out_path


def _md(df: pd.DataFrame, cols, n=10, fmt=None) -> str:
    d = df[cols].head(n).copy()
    lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for _, r in d.iterrows():
        lines.append("| " + " | ".join(f"{r[c]:,.2f}" if isinstance(r[c], float) else str(r[c]) for c in cols) + " |")
    return "\n".join(lines)


def run(cfg: dict) -> None:
    t = lambda n: out_path(cfg, "tables", n)
    y0, y1 = cfg["years"]["start"], cfg["years"]["end"]
    parts = [f"# Geospatial analytics of Italy's agricultural transformation ({y0}-{y1})",
             f"_Auto-generated draft - mode: **{cfg['mode']}**. Edit and complete the interpretation._\n"]
    if cfg["mode"] == "demo":
        parts.append("> **DEMO DATA**: synthetic numbers on fake provinces. Do not interpret as real findings.\n")
    if t("kpi_relocation.csv").exists():
        k = pd.read_csv(t("kpi_relocation.csv"), dtype={"province_code": str})
        cols = ["province_code", "crop", "e0", "e1", "regional_effect"]
        parts += ["## 1. Where did crops relocate? (shift-share regional effect, hectares)",
                  "**Largest gains**", _md(k[k.kind == "relocation_gain"], cols),
                  "\n**Largest losses**", _md(k[k.kind == "relocation_loss"], cols)]
    if t("trends_area.csv").exists():
        tr = pd.read_csv(t("trends_area.csv"), dtype={"province_code": str})
        vc = tr.trend.value_counts().to_dict()
        parts += ["\n## 2. Trends (Mann-Kendall, area)", f"Series by trend: {vc}",
                  "**Strongest growth (% / year)**",
                  _md(tr[tr.trend == "increasing"].sort_values("sen_slope_pct_per_year", ascending=False),
                      ["province_code", "crop", "sen_slope_pct_per_year", "p"]),
                  ]
    if t("spatial_clusters.csv").exists():
        cl = pd.read_csv(t("spatial_clusters.csv"), dtype={"province_code": str})
        s = cl.groupby(["year", "lisa_cluster"]).size().unstack(fill_value=0)
        parts += ["\n## 3. Spatial clusters (Local Moran's I)", s.to_string()]
    if t("climate_fixed_effects.csv").exists():
        fe = pd.read_csv(t("climate_fixed_effects.csv"))
        if len(fe):
            parts += ["\n## 4. Climate and yield (fixed-effects regression)", _md(fe, ["crop", "term", "coef", "p_value"], n=30)]
    if t("rf_metrics.json").exists():
        parts += ["\n## 5. Random-forest check (time-based split)", "```", t("rf_metrics.json").read_text(), "```"]
    parts += ["\n## 6. Limitations",
              "- FAOSTAT is national only; environmental links are trend-level, not province-level.",
              "- Province boundaries changed over 30 years (see config/province_crosswalk.csv).",
              "- Correlation with climate is not causation; technology, prices and policy are not modelled here.",
              "\n## 7. Strategic insights (to write)", "- Policymakers: ...", "- Agribusiness: ...", "- Investors: ..."]
    out_path(cfg, "final_report.md").write_text("\n".join(parts), encoding="utf-8")
    print(f"[report] {out_path(cfg, 'final_report.md')}")
