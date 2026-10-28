# Reference labelling package

Status: 265 sample cells selected; no reference labels or measured accuracy yet.

## Design and files

The strict 1992–2022 change map is split into stable cropland (76 draws), gain (50), loss (50), and stable other land (89). Including stable other land is necessary for whole-study-area assessment. The team sampling module gives nominal n=169 using a planning target SE of 0.02 and assumed user's accuracies 0.90/0.80/0.80/0.95. A minimum 50 draws per stratum increases the sample to 265. These assumed accuracies are planning inputs, not findings. The resulting forecast SE is about 0.0197, conditional on those inputs; actual precision may be worse.

Each stratum is sampled with replacement with probability proportional to the cell's WGS84 ellipsoidal area. This makes draws representative of area within a stratum despite latitude-dependent cell sizes. All draws are retained; this particular draw has no repeated cells. The seed is 20261028. Treat the stratum-area weights as authoritative when using the team's area-adjusted estimator. No finite-population correction is applied to these with-replacement draws. The design concerns national strict endpoint change only; it does not establish accuracy for every province, intermediate interval or mosaic definition.

- `reference_labels_blind.csv`: coordinate, footprint and empty reference fields. Send this to annotators.
- `sample_cells_blind.geojson`: whole-cell footprints in EPSG:4326, with ID only.
- `coordinator_map_key.csv`: mapped classes/strata and draw probabilities. Keep this away from primary annotators until independent interpretation is complete.
- `sample_design.json`: weights, assumed accuracies, allocation and design.
- `estimate_validation.py`: combines finalized labels with the map key and uses the team's `src/sampling.py`; refuses incomplete labels.

## Proposed division of work awaiting team agreement

The remote sensing lead can coordinate primary interpretation. The modeling lead should appoint a second reviewer, preferably someone who did not prepare the map. A manageable proposal is independent second interpretation of all 100 gain/loss draws and a reproducible 20% random subset of stable draws, followed by adjudication of disagreements. This is an allocation proposal, not a confirmed assignment or completed activity. Estimate time after a 10-cell calibration exercise. Do not replace difficult points opportunistically.

## Response protocol

1. Freeze the class definition and sample before interpreting imagery. Treat each approximately 300 m cell as the assessment unit, not just its center point. Use the GeoJSON footprint.
2. Inspect independently sourced imagery appropriate to both 1992 and 2022. Historic aerial photographs or contemporaneous Landsat scenes may assist; recent high-resolution imagery cannot establish the 1992 class by itself. Review seasons/crop calendars and multiple dates. Do not use the CCI/C3S map, its derivative, or the 2021 WorldCover mask as reference truth for this assessment. Land-cover sources sharing underlying inputs are not automatically independent.
3. For each date enter `1` for cropland and `0` for other land under the agreed strict legend. Use the product's definitions for mixed cells; record the rule used for unresolved mixtures. Set a documented classification rule during calibration before completing the sample.
4. Record the reference provider, scene/photo identifier or stable URL, actual acquisition date(s), reviewer ID, confidence, and evidence note. A viewing date is not an acquisition date. Any temporal tolerance around 1992/2022 must be agreed and documented; do not silently replace a target year with a convenient year.
5. If evidence is missing or mixed, leave the binary label blank and use status `uncertain` with a reason. Do not guess. Adjudicate with a second reviewer. Report unresolved nonresponse and assess its possible bias; the supplied estimator withholds accuracy when labels are incomplete.
6. The coordinator checks agreement on duplicate review cells and resolves discrepancies. Set status `final` only after reference fields and required evidence are complete. Keep original annotator records separately from the adjudicated table.
7. Once all draws are finalized, run the estimator. Retain a complete confusion matrix, area weights, user's/producer's accuracy, overall accuracy and its SE, corrected area proportions and uncertainty. The script also computes corrected net gain-minus-loss with the covariance implicit in the sample. Do not report province-specific accuracy from this national sample.

## Run after labelling

```
python estimate_validation.py --labels reference_labels_blind.csv --key coordinator_map_key.csv --design sample_design.json --team-sampling /path/to/italy-agri-geospatial/src/sampling.py --out accuracy_results
```

The estimator calls the team's existing estimator; it does not modify that module. It adds validation of input labels and a corrected-net uncertainty calculation consistent with these independent area-proportional draws. The normal-approximation confidence intervals can be unsuitable near boundaries; review the interval method before final reporting.

Reference: Olofsson, P., Foody, G.M., Herold, M., Stehman, S.V., Woodcock, C.E. and Wulder, M.A. (2014) 'Good practices for estimating area and assessing accuracy of land change', Remote Sensing of Environment, 148, pp. 42–57. doi:10.1016/j.rse.2014.02.015.

A separate `secondary_reference_labels_blind.csv` contains 133 blank independent-review records (100 change cells and 33 randomly selected stable cells; selection seed 20261028). No primary labels are exposed. Exact reviewer assignments are awaiting team agreement.
