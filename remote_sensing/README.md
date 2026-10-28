# Remote sensing contribution

This branch contains the 1992–2022 province endpoint table, processing script, reconciliation results, and four original Bologna pilot CSV exports. Intermediate years and independent validation are not yet included.

## Province data

`outputs/Italy_Province_Land_Cover_1992_2022.csv` provides 110 ISTAT province-level units in long format, six variables and three cropland definitions. `geography_id` is zero-padded `COD_PROV`; `region_id` is `COD_REG` and `istat_uts_id` is `COD_UTS`. Province names are descriptive only. Codes may be read as strings to preserve leading zeroes. Year fields are integer years, area units are km². The common valid area is 301441.207572 km²; independent province and regional rasters agree on national coverage and regional metric totals to within 3e-10 km². Per province, net gain equals gain minus loss, and the national strict totals reproduce the 20 October report. See `outputs/province_checks.json`.

`class_definition` maps to repository rules as follows: `strict_10_11_12_20` = `strict`; `strict_plus_mosaic_30` = `with_mosaic`; `strict_plus_mosaic_30_40` = `broad`. The broad definition counts complete mixed-landscape pixels, not the amount of actual cultivated land. These are map estimates with no independent validation.

Both dates use the 1 January 2026 ISTAT administrative boundaries; pixels are assigned by center. The source has 110 distinct province-level `COD_PROV` values. `COD_UTS` may differ from `COD_PROV` for metropolitan cities, so choose and document the correct crosswalk before joining other data.

## Inputs and reproducibility

The NetCDFs are intentionally excluded from git. Files used, available from the Copernicus Climate Data Store, both accessed 20 October 2026:

- `ESACCI-LC-L4-LCCS-Map-300m-P1Y-1992-v2.0.7cds.area-subset.48.19.35.6.nc`
- `C3S-LC-L4-LCCS-Map-300m-P1Y-2022-v2.1.1.area-subset.48.19.35.6.nc`

Bounding box: north 48, west 6, south 35, east 19. Variable: `lccs_class`. ISTAT non-generalised 2026 regional and province boundaries were accessed 27 October 2026 at https://www.istat.it/storage/cartografia/confini_amministrativi/non_generalizzati/2026/Limiti01012026.zip . The earlier report used the same 2026 boundary vintage.

Run with Python and packages `numpy xarray netCDF4 rasterio pyshp pyproj shapely`. Arrange extracted files as:

```
input-root/
  lc1992/<1992 .nc>
  lc2022/<2022 .nc>
  bounds/ProvCM01012026/ProvCM01012026_WGS84.{shp,shx,dbf,prj}
  bounds/Reg01012026/Reg01012026_WGS84.{shp,shx,dbf,prj}
```

Then run:

```
python remote_sensing/notebooks/province_analysis.py --input-root /path/to/input-root --output-dir /path/to/output
```

The script computes a geodesic WGS84 ellipsoidal polygon area per latitude row using corners `[0,s,s,0]`, latitudes `[c-s/2,c-s/2,c+s/2,c+s/2]`, where `s=1/360` degree and `c` is the cell-center latitude; divide square meters by 1,000,000 for km². That row value is broadcast to each pixel in the row. It tests both common raster coordinates and reconciliation. Checks are accounting checks, not classification accuracy.

The `main` branch's current `italy-agri-geospatial/src/landcover.py` still appears to multiply cell counts by a scalar area; verify any unpublished per-pixel-area update before integrating. The independent script here uses per-row geodesic cell area.

## Bologna pilot

The four original CSV exports are preserved, with their original column names. They describe the Bologna rectangle, not the full province or Italy. The pilot applies a fixed 2021 WorldCover cropland mask even to 2019–2020. This is a pilot-specific choice and should not be described as the proposed historical production mask. June NDVI uses a minimum of three valid image records; records are not necessarily unique dates. Sentinel-1 is a descending relative-orbit-95 radar summary. No drought attribution or independent accuracy estimate is implied.

## Outstanding coordination

Confirm the location and permission for the shared drive before placing the large input files there. Intermediate land-cover years, reference-image sample labeling, validation accuracy, the final impersonal report and the November–February mentoring dates remain to be completed with the team.
