# Product-version boundary diagnostic: Italy, 2015–2016

Analysis and source access: 30 October 2026. Supplement to the 28 October report.

## Main finding

The mapped strict-cropland decline was already present before the product-version boundary. The 2015–2016 strict decline is smaller than the 2014–2015 decline. This short diagnostic therefore does not show an unusually large national strict net loss at the boundary. It does not establish that product-version effects are absent. The broad definition has a larger boundary-year decline than either neighboring one-year comparison and warrants particular sensitivity analysis and independent reference checks.

## National results

All values below are mapped area changes in km². Negative values mean net loss. The 2012–2015 and 2012–2017 columns span three and five years respectively and must not be compared directly with annual columns as rates.

| Definition | 2012–2015 | 2014–2015 | 2015–2016 (version boundary) | 2016–2017 | 2012–2017 |
|---|---:|---:|---:|---:|---:|
| Strict | -423.48 | -150.55 | -119.68 | -55.35 | -598.52 |
| Medium (+30) | -468.57 | -162.73 | -155.17 | -61.39 | -685.13 |
| Broad (+30,+40) | -515.27 | -163.81 | -241.24 | -71.99 | -828.50 |

For strict cropland, 2015 area is 139,846.04 km² and 2016 area is 139,726.36 km². The boundary interval contains 9.99 km² gross gain and 129.67 km² gross loss, giving −119.68 km² net change (approximately −0.086% of 2015 strict cropland). Of the −598.52 km² strict net change from 2012 to 2017, −423.48 km² occurs from 2012 to 2015, before the version boundary. These are descriptive decompositions, not attribution estimates.

All three definitions have zero mapped gross gain in the 2014–2015 comparison. That is an observed map result, not evidence that no agricultural expansion occurred. It reinforces the need to examine temporal mapping behavior and independent reference imagery rather than interpret annual map transitions as exact real-world events.

## Methods and checks

Five Italy subsets (2012, 2014, 2015, 2016 and 2017) were extracted from the Microsoft Planetary Computer ESA CCI/C3S archive. Source tile metadata confirm v2.0.7cds through 2015 and v2.1.1 from 2016. Each year uses both N45E000 and N00E000 tiles; exact item identifiers, unsigned URLs, versions, access dates and subset SHA-256 hashes are in `outputs/version_boundary/version_boundary_source_manifest.json`.

The diagnostic uses the original 4680 × 4680 Italy grid, fixed 2026 ISTAT boundaries, pixel-center assignment, and the existing per-latitude WGS84 geodesic cell areas. No nearest-neighbor remapping to another grid, hectares conversion, historical-boundary crosswalk or new land-cover rule is introduced. The common Italy footprint has no missing class cells and measures 301,441.207572 km². Grids agree with the production grid within 1e-10 degrees; 2012 and 2017 national areas match the verified production totals within 1e-6 km² for all three definitions. Province and region sums reconcile with national metrics within 1e-6 km².

The geographic boundary table has 2,340 rows: 130 geographies × three rules × six metrics. It contains 2015–2016 persistence, gross gain, gross loss, both endpoint areas and net change using the agreed 11 columns plus region_id. Identifiers are text codes; join using geography_type and geography_id. The complete national class-to-class transition table is provided for follow-up inspection. Broad area is a mixed-landscape footprint, not cultivated fractional area.

## Interpretation and integration recommendation

Time and version are confounded: the available 2015 map uses one version and the 2016 map the other. A difference between them combines possible real change, map error and methodological/observing-system effects. The national net metric can also conceal offsetting local errors. This analysis provides neither a causal version-effect estimate nor an independent accuracy estimate, statistical break test or confidence interval. Two neighboring annual intervals are insufficient to establish a general distribution of normal annual change.

Keep all three cropland definitions separate, retain product-version metadata, and present model sensitivity to exclusion of intervals spanning the boundary. Treat the stronger broad-definition boundary loss as a specific follow-up item. If same-year alternative-version maps become available, compare them on the identical grid; otherwise inspect independent historical imagery for a separately designed boundary-focused sample. The current 265-cell sample assesses strict 1992–2022 endpoints and does not validate 2015–2016 changes. Do not reuse its endpoint labels as boundary-year validation.

The existing seven-year tables and validation forms are unchanged. No ad hoc correction or subtraction of the boundary-year loss is justified. Harmonization of Benjamin's older statistical geographies with constant 2026 geography remains a separate team task requiring an agreed code/boundary crosswalk.

## Reproduction

Use `scripts/fetch_version_comparison.py` and `scripts/compare_product_versions.py`; commands are in the main remote-sensing README. Raw GeoTIFFs and the ISTAT source archive remain outside git. Software versions and numerical checks accompany the outputs. Reference labels remain blank and mentoring dates remain proposed until team agreement.

## References (Harvard)

Copernicus Climate Change Service (C3S) (n.d.) *Land cover classification gridded maps from 1992 to present derived from satellite observations*. DOI: 10.24381/cds.006f2c9a. Available at: https://cds.climate.copernicus.eu/datasets/satellite-land-cover (Accessed: 30 October 2026). The catalogue states that both versions use the same processing chain; continuity is intended, but that does not establish local error-free comparability.

European Space Agency (ESA) (n.d.) *Release of C3S Global Land Cover products for 2016, 2017 & 2018 consistent with CCI 1992–2015 map series*. Available at: https://climate.esa.int/en/projects/land-cover/news-and-events/news/new-release-c3s-global-land-cover-products-2016-2017-2018-consistent-cci-1992-2015-map-series/ (Accessed: 30 October 2026).

Istituto Nazionale di Statistica (ISTAT) (2026) *Confini delle unità amministrative a fini statistici al 1 gennaio 2026: versione non generalizzata*. Available at: https://www.istat.it/storage/cartografia/confini_amministrativi/non_generalizzati/2026/Limiti01012026.zip (Accessed: 30 October 2026).

Microsoft (n.d.) *ESA CCI Land Cover*, Planetary Computer. Available at: https://planetarycomputer.microsoft.com/dataset/group/esa-cci-lc (Accessed: 30 October 2026).
