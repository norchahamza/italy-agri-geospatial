# Italy's agricultural transformation: geospatial analytics

How did the geography of Italian crop production change, province by province?
This project builds a reproducible pipeline **API → Bronze → Silver → Gold → models → maps/charts → report**
(PySpark + GeoPandas + statsmodels/scikit-learn), runs in Docker, and produces interactive maps and a draft report.

> **Status**: the pipeline runs end to end on real ISTAT crop data (2006–2024, ~100 provinces, 8 crops).
> The climate (ERA5) and land-cover (ESA CCI) layers are prepared but optional; see [Roadmap](#roadmap).
> Results are **preliminary** and need domain review before being quoted.

## What you get
- Interactive **maps** per crop with a year slider (Location Quotient by province), a **spatial-cluster** map (Local Moran's I), and **charts** (national trends, crop concentration, centre-of-gravity shift, FAO fertiliser/pesticide trends).
- A draft **report** (`final_report.md`) with relocation winners/losers, trends and clusters.
- Analysis tables (CSV) and a **Streamlit dashboard**.

## Data sources
| Layer | Source | Level | Years |
|---|---|---|---|
| Crop area & production | ISTAT SDMX API, dataflow `101_1015_DF_DCSP_COLTIVAZIONI_1` | province (NUTS3) | 2006–2024 (nothing earlier exists at province level) |
| National context, fertilisers, pesticides | FAOSTAT bulk files | country | 1961– |
| Province boundaries | Eurostat GISCO NUTS3 (2013 version, matches ISTAT's NUTS 2010 codes) | province | – |
| Climate (optional) | Copernicus ERA5-Land monthly means | grid → province | 1950– |
| Land cover (optional, not automated) | ESA CCI Land Cover | 300 m | 1992– |

## Quick start with Docker (demo, no downloads)
Install [Docker Desktop](https://www.docker.com/products/docker-desktop/) (Windows/Mac) or Docker Engine (Linux), then:
```bash
git clone https://github.com/norchahamza/italy-agri-geospatial.git
cd italy-agri-geospatial
docker compose run --rm pipeline        # builds the image the first time (a few minutes), then runs the demo
docker compose up dashboard             # dashboard on http://localhost:8501
```
Results appear in `./outputs/demo/`; open `outputs/demo/index.html` in a browser.
The **demo uses synthetic data on fake provinces** (planted signals) just to prove the pipeline works.
Give Docker at least 4 GB of memory (Docker Desktop → Settings → Resources).

## Real data (ISTAT + FAOSTAT + Eurostat)
```bash
docker compose run --rm pipeline --mode real --steps collect --skip-climate   # ~15 min: 19 ISTAT requests, rate-limited
docker compose run --rm pipeline --mode real --steps bronze,silver,integrate,gold,model,viz,report
```
- The ISTAT API is rate limited and sometimes cuts connections; the downloader retries and **skips years already downloaded**, so just re-run if it stops.
- Data goes to `./data/real/` and results to `./outputs/real/` (both git-ignored).
- Climate (optional): create a free account at cds.climate.copernicus.eu, accept the *ERA5-Land monthly* licence, put your key in `~/.cdsapirc`, uncomment the `.cdsapirc` volume line in `docker-compose.yml`, and run `collect` without `--skip-climate`.
- The Docker path was tested with the demo data. Real mode uses the same code; the real-data runs so far were done without Docker (Ubuntu/WSL).

## Run without Docker (Linux, macOS, or WSL2 on Windows)
```bash
sudo apt install -y openjdk-21-jdk python3-venv      # PySpark needs Java 17+
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python scripts/run_pipeline.py --mode demo --steps all
pytest -q
```
**Windows**: use WSL2 or Docker. PySpark on native Windows needs `winutils`/Hadoop binaries and often fails.

## Looking at the results
`outputs/<mode>/` contains:
```
index.html          start here (links to everything)
maps/               animated crop maps (lq_<crop>.html) and spatial clusters (lisa_clusters.html)
charts/             national trends, crop concentration (HHI), centre-of-gravity shift, FAO indicators
tables/             CSVs: trends, clusters, shift-share, diversity, ...
final_report.md     auto-generated draft report
```
**Sharing**: zip the whole folder and send it. Any computer with a browser can open `index.html`; no Python or Docker needed.
Keep the folder together (the pages load `plotly.min.js` from the same folder). Only `lisa_clusters.html` needs internet (Leaflet + OpenStreetMap tiles).

## Method in one minute
- **Silver (cleaning)**: typed columns, harmonised crop codes (e.g. durum + common wheat summed; split codes excluded to avoid double counting), quintals → tonnes, duplicates and invalid values removed, no imputation, yield outliers flagged, data-quality report in `data/<mode>/silver/_dq_istat.json`.
- **Gold (indicators)**: Location Quotient (specialisation vs Italy), HHI (crop concentration), CAGR per period, **shift-share** (national / crop-mix / regional effect = relocation).
- **Models**: Mann-Kendall + Sen's slope (trends), Local Moran's I and Getis-Ord Gi* (spatial clusters, k-nearest-neighbour weights), area-weighted centre of gravity per crop, and (when ERA5 is present) panel fixed-effects regression and Random Forest with a time-based split for climate ↔ yield.

## Configuration (`config/sources.yml`)
- `istat.sdmx.crop_codes`: which ISTAT crop codes make each crop. `area_data_type` / `production_data_type` pick area and production measures.
- `mode_overrides.real`: study period (2006–2024) and boundary settings.
- `boundaries.merge` + `config/province_crosswalk.csv`: reformed provinces are merged into stable units so reforms do not look like crop shifts (Milano+Monza, Ascoli Piceno+Fermo, Foggia+Bari+BAT, all of Sardinia).

## Known limitations (read before quoting results)
- Province-level ISTAT data starts in 2006, so this is a 19-year study, not 30. FAOSTAT gives national context from 1961.
- ISTAT's NUTS 2010 codes are mapped to NUTS 2013 boundaries by a crosswalk; merging reformed provinces reduces resolution in Puglia, Lombardy, Marche and Sardinia.
- Possible series breaks in ISTAT data (e.g. tomatoes around 2019–2020) are being checked; treat sudden one-year jumps with caution.
- FAOSTAT environmental indicators are national, so links to crop shifts are trend-level only.
- Associations with climate are not causal; technology, prices and policy are not modelled.

## Project layout
```
config/            sources.yml, province_crosswalk.csv
src/agri/          ingestion/  cleaning/ (bronze, silver, integrate)  features/ (gold)  models/  viz/  report.py
scripts/           run_pipeline.py (entry point), explore_istat.py, istat_codelists.py (API exploration helpers)
app/dashboard.py   Streamlit dashboard
tests/             pytest (10 tests)
databricks/        notebook to run the pipeline on Databricks (Delta tables)
Dockerfile, docker-compose.yml
```

## Roadmap
- [ ] ERA5 climate layer and climate ↔ yield models
- [ ] ESA CCI land-cover layer (cropland share per province)
- [ ] Resolve and document ISTAT series breaks
- [ ] Extend to other countries / crop groups; compare with Eurostat regional data

## Data licences
ISTAT, Eurostat GISCO, FAOSTAT and Copernicus data are open data under their own terms; cite the sources when publishing.
