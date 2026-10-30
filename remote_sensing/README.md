# Remote sensing contribution — revision 2

Submission date: 28 October 2026. This update extends the province endpoint contribution in pull request #1. It includes the seven-year panel, validation preparation and revised report for team review.

## Completed work

Five intermediate land-cover snapshots were acquired: 1997, 2002, 2007, 2012 and 2017. Together with the original 1992 and 2022 CDS endpoints, seven snapshots and six consecutive intervals are summarized for 110 ISTAT provinces and 20 regions under all three cropland definitions. There are 2,730 snapshot rows and 14,040 interval-metric rows across both geographic levels. The national summary has 21 rows.

The Microsoft Planetary Computer archive supplies CCI/C3S cloud-optimized class rasters. Its 1992 Italy subset matches the original CDS 1992 raster pixel for pixel across all 21,902,400 subset cells. All snapshots have the same valid Italy footprint. Grid transforms, province/region/national sums and interval accounting were checked. National strict endpoints reproduce the original report. These are reproducibility/accounting checks, not independent classification validation. Version or observing-system discontinuities are not eliminated by the bridge check.

A 265-cell strict national endpoint validation sample and independent second-review sheet are prepared. No reference labels are supplied and no observed accuracy has been calculated. Read `validation/README.md` before assigning reviewers. Labelling assignments and mentoring dates require team agreement.

The revised report removes team names and personal submission wording, includes province and seven-year evidence, replaces the one-month plan with a November 2026–February 2027 window and five proposed mentoring checkpoints, uses Harvard references, and explicitly distinguishes retrospective WorldCover masking in the Bologna pilot from the historical production workflow.

## Files to review first

1. `reports/Remote_Sensing_Analysis_Report_Revision_2.docx`
2. `outputs/Italy_Cropland_Snapshot_Panel_1992_2022.csv`
3. `outputs/Italy_Cropland_Interval_Changes_1992_2022.csv`
4. `outputs/Italy_National_Cropland_Seven_Years.csv`
5. `validation/reference_labels_blind.csv` and `validation/sample_cells_blind.geojson`
6. `validation/README.md` and `validation/sample_design.json`

The map key contains the assessed map's class and stratum. Keep it with the coordinator until independent interpretation is complete; primary reviewers should receive the blind files. The secondary blind CSV contains 133 independent records: 100 change cells and 33 stable cells. All reference fields are blank.

## Model schema

All geographic snapshot and interval rows include `geography_id, geography_type, period_start, period_end, variable, value, unit, source_product, product_version, class_definition, quality_note` plus `region_id`.

`geography_type` distinguishes region and province; never join on geography_id alone. Province ID uses COD_PROV padded to three digits; region ID uses COD_REG padded to two. Import identifiers as text. Reference names are not join keys.

Snapshot rows use variable `cropland_area` and equal period_start/period_end (the snapshot year). To construct a province-year panel, filter geography_type=province, select ONE class_definition, and rename period_end to year. Each such panel has 110 × 7 = 770 observations. Interval rows provide persistence, gain, loss, cropland_t0, cropland_t1 and net_change. Values are km²; multiply by 100 only when a downstream model requires hectares. They do not identify specific crops.

Rules map to the existing model settings:
- strict_10_11_12_20 = strict
- strict_plus_mosaic_30 = with_mosaic
- strict_plus_mosaic_30_40 = broad

Keep rules separate; sensitivity variants are not additional independent observations. Broad mosaic area is the footprint of mixed landscape, not actual cultivated area. Five-year snapshots cannot reveal exact conversion dates. Adjacent 2015/2016 checks would help assess the product-version boundary before interpreting a temporal jump.

## Sources and access dates

Original CDS inputs, accessed 20 October 2026:
- ESACCI-LC-L4-LCCS-Map-300m-P1Y-1992-v2.0.7cds.area-subset.48.19.35.6.nc
- C3S-LC-L4-LCCS-Map-300m-P1Y-2022-v2.1.1.area-subset.48.19.35.6.nc

Intermediate archive rasters, accessed 28 October 2026, use v2.0.7cds for 1997, 2002, 2007 and 2012; 2017 uses v2.1.1. `outputs/intermediate_source_manifest.json` records every source tile's exact identifier, version and unsigned source URL, plus extracted-subset hashes. No temporary signed credential URLs are retained.

ISTAT non-generalised 2026 province and region files were downloaded on 27 October 2026 from https://www.istat.it/storage/cartografia/confini_amministrativi/non_generalizzati/2026/Limiti01012026.zip . Both dates and all intermediate snapshots use these same boundaries, with pixel-center rasterization.

The bounding box is north 48, west 6, south 35, east 19. The grid has 4680 rows × 4680 columns. The computed cell areas are in `outputs/Cell_Area_By_Latitude.csv`; broadcast each row's value across every longitude column. The precise grid step and formula are recorded in `outputs/panel_checks.json`. No whole-cell cultivated fraction is inferred for mosaics.

No large NetCDF or intermediate GeoTIFF rasters, logins or private tokens are included. Shared-drive placement of the raw data awaits a specified team folder.

## Reproduce

Install the packages listed in `scripts/requirements.txt`; `outputs/software_versions.json` records the analysis environment. Keep large inputs outside the repository:

```
inputs/
  lc1992/<original 1992 .nc>
  lc2022/<original 2022 .nc>
  bounds/ProvCM01012026/ProvCM01012026_WGS84.{shp,shx,dbf,prj}
  bounds/Reg01012026/Reg01012026_WGS84.{shp,shx,dbf,prj}
```

From the folder containing remote_sensing:

```
python remote_sensing/scripts/fetch_intermediate.py --out /path/outside/repo/intermediate --cds-1992 /path/inputs/lc1992/original.nc
python remote_sensing/scripts/analyse_panel.py --input-root /path/inputs --intermediate /path/outside/repo/intermediate --out remote_sensing/outputs
python remote_sensing/scripts/prepare_validation.py --input-root /path/inputs --out remote_sensing/validation --sampling-module /path/to/team/src/sampling.py
```

The third command regenerates blank sampling forms: run it only before labelling begins or into a new output directory. It must not overwrite completed annotations. The initial sample uses the team's sampling module from base commit 465de099e878a198b2df9cec04050221f39f41ce, with its SHA-256 stored in the design.

The downloader uses certificate-verified HTTPS and a loopback-only range proxy for GDAL. Its temporary access URLs stay in memory. Public archive retrieval can take several minutes and requires network access. Output GeoTIFFs belong outside git.

The labelling estimator deliberately refuses incomplete labels. An internal synthetic perfect-reference check verified its accounting and net-area calculation; synthetic labels were discarded and are not in this package. Run the real estimator only after reference evidence and adjudicated labels exist.

## Remaining decisions and analysis

Confirm exact dates and placement of the five mentoring sessions, primary and secondary reviewers, and the historical reference sources and temporal tolerances. Reviewer assignments and checkpoint month allocations in the report are proposals. Complete labelling and adjudication before claiming observed accuracy. Province-specific and interval-specific validation would require additional sampling support. Agricultural/climate covariates, model fits and causal or policy claims remain with the wider project workstreams.

The original endpoint table and `scripts/province_analysis.py` remain available alongside this update.

## Repository corrections and 2015–2016 version diagnostic (30 October 2026)

The executable Python directory is now `scripts/`; the interrupted-transfer `.dfaBlB` artefact has been removed. `reports/Remote_Sensing_Analysis_Report_Revision_2.docx` is the archived 28 October report, so use this README for current executable paths and the later diagnostic. The seven-year production tables and blind validation samples are unchanged.

The separate diagnostic is described in `reports/Product_Version_Comparison_2015_2016.md`. It uses the 2015 v2.0.7cds and 2016 v2.1.1 maps, plus 2014–2015 and 2016–2017 within-version comparisons and the broader 2012–2017 interval. Outputs are in `outputs/version_boundary/`; the 2015–2016 province/region metrics retain the agreed long-format schema. This is a diagnostic, not an estimated causal effect of the version change.

Reproduce with large inputs stored outside git:

```bash
python remote_sensing/scripts/fetch_version_comparison.py --out /path/outside/repo/version_comparison
python remote_sensing/scripts/compare_product_versions.py --rasters /path/outside/repo/version_comparison --boundaries /path/to/extracted/ISTAT2026 --existing-outputs remote_sensing/outputs --out remote_sensing/outputs/version_boundary
```

Before joining Benjamin's historical statistics, agree and document the target geography and a defensible historical-code/boundary crosswalk. Matching text names or current ISTAT codes alone does not harmonize historical boundaries. Any remapping weights, splits, merges and unresolvable units must be recorded jointly with `statistics/`; the current remote-sensing data remain on constant 2026 geography.
