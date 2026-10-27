# Geospatial Analytics of Agricultural Transformation in Italy, 1992-2022

Code for the Rome Business School Capstone (Master in International Data Science, April 2026 intake).
Research question: how did mapped cropland and provincial crop specialisation change in Italy between 1992 and 2022,
and how are the changes **associated** with climatic and socioeconomic conditions?

## Pipeline
```
raw data (ESA CCI/C3S, ISTAT, FAOSTAT, climate)  ->  src/ingest.py (download, document versions)
  -> src/landcover.py   cropland rules, transition matrices, persistence / gain / loss, per-province summaries
  -> src/sampling.py    stratified validation sample, area-adjusted accuracy with confidence intervals
  -> src/crops.py       location quotient, HHI, emerged / expanded / declined / abandoned labels
  -> src/models.py      fixed-effects panel model, Moran's I on residuals
  -> src/viz.py         maps and charts
```

## Run
```bash
python -m venv .venv && source .venv/Scripts/activate     # Git Bash on Windows
pip install -r requirements.txt
pytest -q                     # offline tests, synthetic data only
python -m scripts.run_demo    # full pipeline on synthetic data with a known effect
```

## Who owns what (from the proposal)
| Module | Owner |
|---|---|
| `landcover.py`, `sampling.py` | EG |
| `crops.py`, ISTAT/FAOSTAT ingestion | AB |
| climate and socioeconomic covariates | KH |
| `models.py`, integration | HN |
| `viz.py`, report figures | AC |

## Status
- **Tested offline (synthetic data):** landcover, crops, sampling, models.
- **NOT tested, needs real data and accounts:** `src/ingest.py` (CDS account, dataset names and versions, FAOSTAT URL),
  `src/viz.py` choropleth, ISTAT download (manual).
- Cropland class rules, change thresholds and the sample-size target are **placeholders**: justify them in the report
  and show sensitivity checks.
- ESA CCI land cover has product-version breaks (v2.0.7 to 2015, v2.1.1 later): document them and check for artificial jumps.
- Regression coefficients are associations, not causal effects.

## For the report
Source code goes in the Annex. Cite every dataset in Harvard style with the accessed date.
