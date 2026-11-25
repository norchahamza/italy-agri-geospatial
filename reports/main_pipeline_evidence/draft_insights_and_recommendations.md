# Draft Insights and Recommendations (Main Pipeline)

*Draft for team review. All claims should be read with limitations in `literature_notes.md` and `evidence_log.md`.*

## Draft insights

1. **Relocation is crop- and place-specific, not uniform.**  
   Shift-share shows strong positive regional effects for wheat in Foggia+Bari+BAT (+50,711 ha regional effect, 2006–2024) and Palermo (+23,844 ha), while Sardegna wheat has a large negative regional effect (-39,815 ha). Grapes gain in Agrigento and Treviso; Lecce olives and Puglia grapes show losses.  
   *Evidence:* `tables/kpi_relocation.csv`; `final_report.md` §1; `maps/lq_wheat.html`, `maps/lq_grapes.html`, `maps/lq_olives.html`.

2. **Area decline/no-trend dominates, but there are localized growth pockets.**  
   Mann-Kendall classifies 255 decreasing, 193 no trend, 116 increasing province-crop area series. Strongest percent increases include small-base olives/sunflower series in northern provinces; strongest declines include sugar beet, maize, tomatoes in selected provinces.  
   *Evidence:* `tables/trends_area.csv`; `final_report.md` §2; `charts/national_trends.html`.

3. **Spatial clustering intensified slightly.**  
   Low-Low clusters increased from 155 (2006) to 201 (2024), High-High from 78 to 82, while Not-significant decreased from 529 to 479. This suggests more spatially structured crop-area patterns.  
   *Evidence:* `tables/spatial_clusters.csv`; `final_report.md` §3; `maps/lisa_clusters.html`.

4. **Crop geography is moving for some crops.**  
   Centroids show movement from 2006 to 2024, especially sugar beet (43.93N,12.43E to 44.72N,11.57E) and tomatoes (42.04N,13.45E to 42.36N,12.81E), while rice remains relatively stable.  
   *Evidence:* `tables/crop_centroids.csv`; `charts/centroid_shift.html`.

5. **Diversification is not a simple national trend.**  
   Mean provincial HHI is nearly flat (0.476 in 2006 vs 0.470 in 2024), so diversification/concentration should be assessed by province and crop mix rather than assumed nationally.  
   *Evidence:* `tables/province_diversity.csv`; `charts/hhi_by_region.html`.

## Draft recommendations

### Policymakers
- **Target adaptation where losses concentrate.** Prioritize provinces with large negative regional effects (e.g., Sardegna wheat, Lecce olives, Perugia wheat/sunflower, Siena wheat) for water, soil, and farm-transition support, after validating local drivers. *Evidence:* `tables/kpi_relocation.csv`.
- **Protect and monitor emerging/growing specializations.** Provinces with positive regional effects or significant growth (Foggia+Bari+BAT wheat/olives, Palermo wheat, Agrigento/Trapani grapes/olives, Veneto/Emilia wheat gains) may need infrastructure, processing, and climate-risk planning. *Evidence:* `tables/kpi_relocation.csv`, `tables/trends_area.csv`.
- **Use spatial clusters for regional programs.** High-High and Low-Low clusters can inform where to coordinate interventions across neighboring provinces rather than province-by-province only. *Evidence:* `tables/spatial_clusters.csv`, `maps/lisa_clusters.html`.

### Agribusiness / supply chain
- **Stress-test sourcing maps for relocating crops.** For crops with centroid movement or strong regional effects (wheat, grapes, tomatoes, sugar beet), review procurement, storage, and transport exposure. *Evidence:* `tables/crop_centroids.csv`, `tables/kpi_relocation.csv`.
- **Distinguish volume decline from competitive relocation.** A province can lose area but still outperform national/crop-mix expectations (positive regional effect). Use shift-share before making exit/entry decisions. *Evidence:* `tables/shift_share.csv`, `tables/kpi_relocation.csv`.

### Investors / risk analysts
- **Treat concentration as risk signal, not just efficiency.** Inspect high-HHI provinces and recent trend direction before exposure to single-crop regional shocks. *Evidence:* `tables/province_diversity.csv`, `tables/trends_area.csv`.
- **Require causal follow-up before capital allocation.** Current evidence is descriptive/accounting; add climate, water, prices, CAP subsidies, irrigation, and farm structure before attributing relocation causes. *Evidence:* `final_report.md` limitations; `charts/fao_env.html`.

## Next validation steps
1. Resolve ISTAT series breaks (especially tomatoes 2019–2020) and annotate affected trends.
2. Add climate (ERA5) and land-cover (CCI) overlays before causal interpretation.
3. Confirm province merge/crosswalk impacts with domain team.
4. Produce province profiles for top gain/loss cases with local context.
