# Italy agriculture: geospatial analytics (1995-2024)

How did the geography of Italian crop production change over 30 years? Pipeline from API to final deliverables:
**Collect → Bronze → Silver → Integrate → Gold → Model → Visualise → Report** (PySpark + GeoPandas + scikit-learn/statsmodels, runs locally or on Databricks).

## Quick start (no internet / no accounts needed)
```bash
python -m venv .venv && source .venv/bin/activate     # Java 17+ is required by PySpark
pip install -r requirements.txt
python scripts/run_pipeline.py --mode demo --steps all   # synthetic data, ~1-2 min
open outputs/demo/index.html                              # maps + charts
streamlit run app/dashboard.py                            # dashboard
pytest -q                                                 # tests
```
The demo uses **synthetic data on fake grid "provinces"** with planted signals (tomatoes move north, maize declines,
yield reacts to climate). Use it to check the pipeline works, never to draw conclusions.

## Running on real data
| Step | What to do |
|---|---|
| ISTAT crops (province) | `python scripts/run_pipeline.py --list-istat-dataflows`, put the dataflow id in `config/sources.yml` → `istat.dataflow`. Or download a CSV by hand from esploradati.istat.it into `data/real/raw/istat/`. Then fix `istat.columns` (source → canonical names) and `production_unit`. |
| FAOSTAT | automatic (bulk zips, national level only) |
| Boundaries | automatic (ISTAT generalised limits, URL in config) |
| ERA5-Land climate | free account at cds.climate.copernicus.eu, accept the dataset licence, put your key in `~/.cdsapirc` |
| ESA CCI land cover | **not automated.** Compute cropland share per province-year (e.g. with `rasterstats` / `exactextract` on the CDS `satellite-land-cover` NetCDF) and save `data/real/raw/landcover/landcover_province_year.csv` with `province_code,year,cropland_pct`. The pipeline picks it up automatically; skipped if absent. |
```bash
python scripts/run_pipeline.py --mode real --steps all
```
**Things I could not test without network/credentials, so verify them first:** the ISTAT SDMX endpoint and dataflow id,
the ISTAT column names/units, the FAOSTAT and ISTAT-boundary URLs (they change between releases), and the CDS request
format. The ERA5 zonal-statistics function itself *is* unit-tested on synthetic grids.

## Province boundary changes
Provinces were merged/created over 30 years (e.g. Sardinia). Put `old_code,new_code` pairs in
`config/province_crosswalk.csv`; Silver remaps and re-aggregates. `integrate` prints any province code without a polygon.

## What each layer does
- **Bronze**: raw CSV as strings + `_ingestion_ts`, `_source`, `_file`.
- **Silver**: canonical columns, zero-padded codes, decimal-comma parsing, crop harmonisation (`crop_map`), quintals→tonnes, duplicate/invalid removal, yield-outlier flag, data-quality JSON (`data/<mode>/silver/_dq_istat.json`). No imputation.
- **Integrate**: crops × province attributes × ERA5 climate × land cover.
- **Gold**: Location Quotient, share, HHI diversity, national series, CAGR per decade, shift-share (national / crop-mix / regional effect).
- **Models**: Mann-Kendall + Sen slope; Local Moran's I and Getis-Ord Gi* (KNN weights); crop centre-of-gravity shift; panel fixed-effects regression (climate→yield); Random Forest with time-based split + permutation importance.
- **Outputs** (`outputs/<mode>/`): `index.html`, animated maps, charts, `tables/*.csv`, `final_report.md` (auto-generated draft to edit).

## Databricks
Import the repo in Repos and run `databricks/run_on_databricks.py` (sets `AGRI_TABLE_FORMAT=delta` and Volume paths).

## Layout
```
config/sources.yml  config/province_crosswalk.csv
src/agri/{ingestion,cleaning,features,models,viz}  src/agri/report.py
scripts/run_pipeline.py   app/dashboard.py   databricks/   notebooks/   tests/
```

## Caveats for the report
FAOSTAT environmental indicators are national, so the sustainability link is at trend level, not per province.
Climate effects are associations (technology, prices and CAP policy are not modelled).
