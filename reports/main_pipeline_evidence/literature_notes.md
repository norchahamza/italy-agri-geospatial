# Literature Notes: Italy Agricultural Transformation (Main Pipeline)

## Scope and evidence base
- Evidence reviewed: main pipeline outputs in `agri_outputs.zip` (from `main` commit `cc2505c`, 2026-11-25 artifact timestamp) covering ISTAT province crop data 2006–2024 and FAOSTAT national context.
- Tables reviewed: `tables/kpi_relocation.csv`, `tables/trends_area.csv`, `tables/spatial_clusters.csv`, `tables/province_diversity.csv`, `tables/cagr.csv`, `tables/crop_centroids.csv`, `tables/shift_share.csv`.
- Figures/report reviewed: `final_report.md`, `charts/national_trends.html`, `charts/hhi_by_region.html`, `charts/centroid_shift.html`, `charts/fao_env.html`, `maps/lq_*.html`, `maps/lisa_clusters.html`.
- Method reference: `README.md`, `config/sources.yml`, `src/agri/report.py` on `main`.

## Key literature/method concepts relevant to the findings

| Concept | What it measures | Why relevant here | Caution |
|---|---|---|---|
| Location Quotient (LQ) | Provincial crop specialization relative to Italy | Used in crop LQ maps to show where crops are over/under-represented | Descriptive specialization, not profitability or suitability alone |
| Shift-share (regional effect) | Local change not explained by national/crop-mix effects | Core relocation KPI in `kpi_relocation.csv` | Accounting decomposition, not causal attribution |
| Mann-Kendall + Sen slope | Monotonic trend significance and magnitude | `trends_area.csv` classifies increasing/decreasing/no trend | Sensitive to period, series breaks, and short/noisy series |
| Local Moran's I / Getis-Ord Gi* | Spatial clustering/hot-cold spots | `spatial_clusters.csv`, `lisa_clusters.html` | Depends on spatial weights (k-nearest neighbours) and boundaries |
| HHI / effective N crops | Crop concentration/diversification | `province_diversity.csv`, `hhi_by_region.html` | Concentration can reflect specialization or vulnerability |
| Area-weighted centroid | Geographic center of crop area | `crop_centroids.csv`, `centroid_shift.html` | Centroid shift summarizes distribution change, not farm movement |

## Notes by theme

### 1) Relocation and territorial specialization
- Shift-share regional effects identify where crop area grew or declined beyond national/crop-mix expectations. Largest gains include wheat in Foggia+Bari+BAT and Palermo, grapes in Agrigento and Treviso; largest losses include wheat in Sardegna and Perugia/Siena, olives in Lecce. Evidence: `tables/kpi_relocation.csv`, `tables/shift_share.csv`, `final_report.md` section 1.
- Interpretation should separate absolute change from regional effect: Torino maize has negative total change but positive regional effect, meaning it declined less than expected given national/crop-mix pressures.

### 2) Crop trends and structural change
- Mann-Kendall results show 255 decreasing, 193 no trend, 116 increasing area series (`trends_area.csv`; `final_report.md` section 2). This indicates widespread contraction or stability in provincial crop-area series, with selected growth pockets.
- Strong positive Sen slopes are often on small-base areas (e.g., olives in Venezia/Sondrio, sunflower in several northern provinces), so percent growth should be read alongside mean area.

### 3) Spatial clustering
- Local Moran's I counts shift from 2006 to 2024 toward more Low-Low and slightly more High-High clusters, with fewer Not-significant cells (`spatial_clusters.csv`; `final_report.md` section 3; `maps/lisa_clusters.html`). This suggests increasing spatial organization/polarization for some crop-area patterns.

### 4) Diversification and concentration
- Mean provincial HHI changed slightly from 0.476 (2006) to 0.470 (2024) (`province_diversity.csv`). The small change suggests no uniform national diversification story; province-level trajectories should be inspected.

### 5) Geographic shift of production
- Crop centroids move over 2006–2024 (`crop_centroids.csv`, `charts/centroid_shift.html`). Sugar beet and tomatoes show notable centroid movement; rice and olives are comparatively stable. These movements should be interpreted with merged-province geometry and crop coverage limits.

## Data quality / limitations to carry into recommendations
- Province ISTAT crop data starts 2006; not a 30-year province series (`README.md`, `config/sources.yml`).
- Reformed provinces merged into stable units: Milano+Monza, Ascoli Piceno+Fermo, Foggia+Bari+BAT, Sardegna all provinces (`config/sources.yml`, `final_report.md`).
- Possible ISTAT series breaks (e.g., tomatoes around 2019–2020) require caution before interpreting sudden jumps (`README.md`).
- FAOSTAT indicators are national; cannot support province-level causal claims (`final_report.md`, `charts/fao_env.html`).
- Correlations/models are not causal; prices, CAP/policy, technology, irrigation, and farm structure are not modelled (`README.md`, `final_report.md`).
