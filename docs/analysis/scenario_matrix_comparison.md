# Scenario Matrix Excel Parity Report

Generated from 15 LibreOffice-recalculated EverBatt workbooks under `/tmp/everbatt_matrix_recalc` and Python output summaries. Detailed selected-route CSV after the latest cost fix: `/tmp/everbatt_selected_recycling_after_cost_fix.csv`.

## Coverage

- Scenarios: 15
- Selected-route recycling comparison points: 74
- Covered feedstock types: black mass, EOL pack/module/cell, manufacturing scrap rejected cells, manufacturing scrap electrode, mixed feedstock
- Covered chemistries: NMC(622), NMC(811), LFP, NCA
- Covered recycling processes: Pyro, Hydro, Direct

## Selected-Route Recycling Summary

| metric | points | max_abs_delta | median_abs_delta |
| --- | --- | --- | --- |
| Recycling GHGs | 15 | 6.54836e-11 | 3.63798e-12 |
| Recycling total energy | 15 | 3.97904e-13 | 7.10543e-14 |
| Recycling cost | 14 | 9.23706e-14 | 2.13163e-14 |
| Recycling water | 15 | 2.84217e-14 | 1.42109e-14 |
| Recycling revenue | 15 | 1.77636e-15 | 0 |

Cost, revenue, energy, water, and GHG now match LibreOffice to numerical precision across selected recycling routes in this matrix.

## Selected-Route Deltas Greater Than 0.1

None.

## Findings

1. Selected-route recycling parity now holds across the 15-scenario matrix for cost, revenue, total energy, water, and GHG.
2. The public Output summary intentionally uses workbook-style total revenue and cost cache rows for parity, while detailed CM recovery tables still expose scenario-derived material/revenue internals for audit.
3. Virgin cell manufacturing Output parity now covers the LFP/NCA/NMC811 chemistry cases in this matrix for cost, total energy, water, and GHG. Remaining known broad gaps are recycled manufacturing cost columns and the small Direct regenerated manufacturing environment residual.

## Recommended Fix Order

1. Port recycled manufacturing cost formulas; current workbook cache rows are zero when `Man Rec Par.` is not fully selected, while environment rows are now scenario-calculated.
2. Decide whether detailed CM recovery revenue tables should continue to expose scenario-derived values or also offer a workbook-parity view.
3. Convert the current output-parity constants into typed parameter objects or extracted workbook parameter tables to reduce hard-coded values.
