# recycle-cost

Streamlit work-in-progress replica of `EverBatt 2023.xlsm`.

## Setup

```bash
source /home/zhouzhq/recycle_cost/.venv/bin/activate
```

The uv environment has already been initialized. To recreate it:

```bash
UV_CACHE_DIR=/tmp/uv-cache uv sync
```

## Run The App

```bash
streamlit run app.py --server.port 8502
```

Current local URL:

```text
http://localhost:8502
```

## Analysis

The workbook reconnaissance script extracts worksheet metadata, formulas, dependency edges,
and VBA macro text:

```bash
python scripts/analyze_everbatt.py
```

Generated files:

- `docs/analysis/everbatt_logic.md`
- `docs/analysis/everbatt_analysis.json`
- `docs/analysis/vba_olevba.txt`

## Current Implementation Status

The Streamlit app is now organized as a user-facing EverBatt analysis tool rather than
a migration dashboard. It exposes:

- Chinese/English language switching.
- Scenario presets for the workbook default black-mass case and common NMC(622) pack,
  hydro, pyro, direct, and manufacturing-scrap cases.
- Editable production, feedstock, cathode, recycling-process, and transport inputs.
- Input guidance for zero-flow, black-mass bypass, unsupported process, and zero cathode
  throughput cases.
- Overview, recycling process, cathode/manufacturing, parameter, and export workflows.
- JSON import/export for scenarios, CSV export for calculated result tables, and a ZIP
  export containing the active scenario plus result tables.
- Structured reference tables for material prices, geographic parameters, BatPaC costs,
  and GREET combustion factors.
- Parameter sheet previews for users who still need to inspect workbook source data.

Python-ported modules:

- `Input` scenario model for key manufacturing, feedstock, recycling, and transport fields.
- `Col&Trans Par.` transportation cost calculation, validated against the saved workbook
  default scenario at the segment level.
- `Col&Trans Par.` transportation environmental impacts (`C81:I100`), including energy,
  water, pollutant emissions, CO2 with carbon in VOC/CO, and GHGs.
- `Disassembly` feedstock conversion, pack/cell weight summary, pack and module
  disassembly cost, and recovered component revenue. The default workbook scenario has
  no module/cell feedstock, so this module is also tested with a synthetic NMC(622)
  end-of-life module scenario.
- `Preproc. Par.` generic preprocessing core: eligible feedstock streams, weighted
  material composition, product outputs, preprocessed black mass composition,
  environment summary, equipment sizing, CAPEX, OPEX, and cost summary.
- `CM Rec Par.` Pyro/Hydro/Direct recovery: black-mass throughput, selected product
  outputs, equipment sizing, CAPEX/OPEX, and cost summary. Default workbook CAPEX,
  OPEX, working capital, and total recycling cost snapshots are covered by tests.
- `Mat. Conv Par.` material conversion: recovered material inputs, available precursor
  conversion, recycling economics, allocation factors, recycling environmental impacts,
  precursor conversion costs, conversion environmental impacts, and total conversion
  summary.
- `Cath. Prod. Par.` cathode production workbook tables: general production inputs,
  available recycled precursors, material/energy demand by cathode chemistry, chemical
  and utility prices, precursor conversion costs, required precursor recipes, recycled
  versus virgin material split, environmental summaries, and CAPEX/OPEX cost snapshots.
  It also includes scenario-aware cathode throughput, available precursor tonnage,
  recycled/virgin/surplus split, virgin environmental totals, and raw material cost
  calculations.
- `Man Par.` and `Man Rec Par.` manufacturing snapshots: virgin cell and pack
  manufacturing inputs, material composition, energy/yield parameters, cell material
  inputs, formula-calculated cell material input audits, formula-calculated process
  energy input environmental audits, formula-calculated recycled material burden audits,
  environmental summaries, material cost, cost summary, pack masses, pack environmental
  impacts, and recycled cathode-material environment/cost tables.
- `Output` and `Report` reporting snapshots: cell/pack manufacturing summaries,
  process-stage output tables, cost breakdowns, recycling revenue tables, report
  comparison tables, closed-loop totals, a Python-calculated virgin cell/pack
  manufacturing output summary, a Python-calculated recycled manufacturing output
  wrapper for Pyro/Hydro/Direct/Custom columns, and a Python-port stage summary that
  combines currently migrated modules.

## Reproduction Plan

The migration target is not only to display saved workbook values, but to reproduce the
EverBatt calculation graph in Python so scenario edits in Streamlit recalculate the same
technical, cost, and environmental outputs as `EverBatt 2023.xlsm`. Workbook cached values
remain the regression oracle until the equivalent formula block is fully ported.

### Guiding Rules

- Port one worksheet block at a time, preserving the workbook row/column meaning in
  narrow, named Python tables.
- Keep every migrated formula covered by tests against the default workbook snapshot.
- For formulas depending on user scenario inputs, add at least one synthetic scenario test
  so the code is not only reading cached workbook values.
- Keep workbook snapshot readers separate from Python-calculated functions. Snapshot
  functions are the oracle; Python functions are the replacement.
- Prefer explicit intermediate tables over one large final formula. This makes future
  audit against Excel formulas easier.
- When a workbook formula uses lookups, encode the lookup table and selected key rather
  than hard-coding a selected cell value.

### Phase 1: Stabilize Workbook Formula Inventory

Goal: make the remaining Excel migration scope explicit and measurable.

Tasks:

- Extend `scripts/analyze_everbatt.py` outputs with formula counts by worksheet block and
  by output region.
- Add a manual formula map for high-value ranges:
  `Output!B11:H32`, `Output!B37:T59`, `Output!B201:V227`, `Report!AA20:AE46`,
  `Man Rec Par.`, `Cath. Prod. Par.`, `CM Rec Par.`, and `Preproc. Par.`.
- Tag formulas as `ported`, `snapshot-only`, `blocked-by-input-model`, or
  `needs-domain-check`.
- Add a migration checklist table under `docs/analysis/` so future work can update status
  without rereading the workbook.

Acceptance criteria:

- Every user-facing Output and Report table has a documented source range.
- Every currently Python-ported table links to the worksheet range it replaces.
- The checklist identifies the next unported formula block and its dependencies.

### Phase 2: Complete Scenario Input Model

Goal: replace remaining implicit workbook selections with typed Python scenario fields.

Tasks:

- Expand `Scenario` to cover all input switches used by migrated modules: battery
  manufactured/collected, chemistry, location, feedstock mix, recycling process,
  cathode production settings, recycled content, transport distances, and plant
  throughput.
- Add validation for option compatibility, for example process-specific product outputs
  and chemistry-specific cathode precursor requirements.
- Replace direct reads of selected workbook cells in Python-calculated paths with values
  from `Scenario` where the user is expected to edit them.
- Keep workbook default scenario construction as the reference baseline.

Acceptance criteria:

- The default `Scenario` reproduces workbook default outputs.
- Changing a Streamlit sidebar input changes the corresponding Python-calculated module.
- Snapshot-only tables are clearly marked in the UI until they become dynamic.

### Phase 3: Finish Manufacturing Formula Port

Goal: make `Man Par.`, `Man Rec Par.`, and the manufacturing part of `Output` dynamic.

Tasks:

- Replace virgin cell mass, material input, energy, yield, cost, and environmental summary
  calculations with Python formulas rather than cached worksheet totals.
- Port virgin pack configuration: cells per module, modules per pack, module/pack mass,
  component cost, BMS, capital, building, profit, warranty, and total pack cost.
- Port recycled cell manufacturing for Pyro, Hydro, Direct, and Custom routes, including
  recycled cathode material inputs, material cost, environmental burdens, and selected
  recycled content.
- Extend `python_ported_manufacturing_output_summary()` from virgin cell/pack C/H columns
  to recycled manufacturing columns D:G.
- Add tests for each route using workbook default values and synthetic recycled-content
  scenarios.

Acceptance criteria:

- `Output!C11:H32` is Python-calculated for all manufacturing columns.
- Max absolute delta versus workbook default is within floating-point tolerance.
- Streamlit shows which manufacturing columns are Python-calculated and which, if any,
  remain snapshots.

### Phase 4: Complete Recycling And Material Conversion Dynamics

Goal: make preprocessing, CM recovery, and material conversion respond correctly to
feedstock and process choices.

Tasks:

- Audit `Preproc. Par.` generic and chemistry-specific branches for feedstock splits,
  black mass composition, equipment sizing, CAPEX, OPEX, and environmental totals.
- Complete `CM Rec Par.` Pyro, Hydro, and Direct formulas beyond the current default
  summaries: reagent consumption, product purity, product mass, equipment scaling,
  working capital, and revenue/cost allocation.
- Port Custom route formulas if the workbook exposes enough consistent logic; otherwise
  document it as user-specified/custom-input driven.
- Finish `Mat. Conv Par.` route-dependent precursor availability, conversion burden,
  allocation, and cost formulas.
- Add scenario tests for at least one Pyro, one Hydro, and one Direct case.

Acceptance criteria:

- `Output` recycle-stage rows for Pyro/Hydro/Direct are Python-calculated.
- CM recovery product and cost summaries change when feedstock chemistry or throughput
  changes.
- Material conversion totals are traceable back to recovered product inputs.

### Phase 5: Complete Cathode Production Port

Goal: fully reproduce `Cath. Prod. Par.` for virgin and recycled cathode production.

Tasks:

- Replace remaining cathode CAPEX/OPEX snapshots with formula-based equipment, capital,
  labor, utility, material, profit, and warranty calculations.
- Port required precursor recipes for all supported chemistries and process routes.
- Make recycled/virgin precursor split dynamic for selected recycled content and available
  recovered material.
- Recalculate cathode production cost and environmental totals for Pyro, Hydro, Direct,
  Custom, Virgin, and Direct regeneration paths.
- Add tests for NMC(111), NMC(622), NMC(811), LCO, NCA, LMO, and LFP where workbook data
  is available.

Acceptance criteria:

- Cathode production `Output` columns match workbook default snapshots.
- Chemistry changes in Streamlit recalculate precursor needs, cost, and environmental
  totals.
- Insufficient recovered material is surfaced as virgin makeup or surplus, not hidden.

### Phase 6: Replace Final Output And Report Aggregation

Goal: make `Output` and `Report` calculated from Python module outputs instead of cached
workbook cells.

Tasks:

- Build a Python aggregation layer that maps module outputs to:
  cell/pack manufacturing summaries, process-stage summaries, cost breakdowns, recycling
  revenue tables, manufacturing comparison, and closed-loop total results.
- Preserve workbook labels and units in the returned tables for easy side-by-side review.
- Add delta columns against snapshot tables during migration; hide or move them to an
  audit view once the port is stable.
- Handle workbook error values such as `#N/A` and `#DIV/0!` explicitly instead of
  silently converting them when the Python model should report an invalid scenario.

Acceptance criteria:

- User-facing `Output` and `Report` views are Python-calculated by default.
- Workbook snapshots remain available in an audit expander.
- End-to-end default scenario deltas are tested at key rows for cost, energy, water, and
  GHGs.

### Phase 7: Streamlit Productization

Goal: make the app usable as an analysis tool, not just a migration dashboard.

Tasks:

- Separate views into clear workflows: Overview, Recycling, Cathode/Manufacturing,
  Parameters, and Export.
- Add user controls for scenario save/load as JSON.
- Add CSV export for every calculated table and a one-click export for the full scenario
  result package.
- Keep formula-migration and audit metadata out of the main user flow; preserve it only in
  tests, docs, and developer-facing analysis files.
- Add input validation messages for incompatible scenarios and missing workbook data.
- Keep dense engineering tables available, but add concise summary cards for cost,
  energy, water, and GHGs.

Acceptance criteria:

- A user can change a scenario, run the calculation, inspect module results, and export
  outputs without opening Excel.
- Snapshot-only values are not presented as editable recalculated outputs.
- The app remains responsive on the default workbook.

### Phase 8: Quality, Packaging, And Maintenance

Goal: make the project reliable enough to maintain after the initial replica is complete.

Tasks:

- Add focused unit tests per module plus end-to-end regression tests for default scenario.
- Add a small set of non-default fixture scenarios covering chemistry, feedstock, and
  process variation.
- Add type hints and lightweight data validation for module table schemas.
- Add CI commands for `pytest`, `compileall`, and formatting/linting if a formatter is
  adopted.
- Document known deviations from EverBatt, especially places where Excel behavior is
  ambiguous, error-prone, or intentionally improved.

Acceptance criteria:

- New formula ports require matching tests before being considered complete.
- Known deviations are documented in one place.
- The app can be recreated from a clean checkout with `uv sync` and run with Streamlit.

### Current Priority Queue

Completed in the current migration pass:

- `Man Rec Par.!AH70:AK89` recycled manufacturing total environment summaries
  are now formula-ported from calculated material burdens plus calculated energy
  inputs, with workbook-delta audit columns and Streamlit display.
- `python_ported_manufacturing_output_summary()` now uses the Python-calculated
  recycled manufacturing total columns instead of the cached workbook snapshot.
- `Output!B37:G59` now has a Python-port audit slice for Collection & Transport
  and Disassembly, including cost, revenue, and environmental rows with workbook
  deltas.
- `Output!I37:M59` Recycle-stage cost, environmental, and revenue rows are now
  formula-ported for Pyro, Hydro, Direct, and Custom using preprocessing/CM
  recovery throughput weighting and workbook-delta audit columns.
- `Output!O37:T58` Cathode Production cost and environmental rows are now
  formula-ported from `Cath. Prod. Par.!D9` HLOOKUPs into `Man Rec Par.` and
  `GREET IO`, including the workbook default `Select Chemistry -> #N/A -> 0`
  behavior.
- `Cath. Prod. Par.` recycled/virgin/surplus precursor split now has a
  formula-level audit table that reproduces workbook error propagation at the
  default zero cathode throughput.
- `Cath. Prod. Par.` raw-material OPEX row 488 now has a Python-calculated audit
  table for Pyro, Hydro, Custom, and Virgin annual/per-kg costs.
- `Cath. Prod. Par.` utilities and labor OPEX rows now have Python-calculated
  audit tables for annual utility cost, operating labor, and supervisory/clerical
  labor against workbook rows 494, 490, and 492.
- `Cath. Prod. Par.` capital, maintenance, fixed-charge, overhead, general
  expense, profit, total product cost, and cost-to-recipient rows now have
  Python-calculated audit tables. Circular workbook relationships are solved
  algebraically for contingency, working capital, patents, distribution, and
  R&D cost rates.
- The Cathode CAPEX/OPEX audit tables now roll up into
  `cathode_cost_per_line_summary_calculated()`, a formula-calculated replacement
  for the workbook cost-per-line summary.
- `Output!Q202:V209` Cathode production cost rows now have a Python-calculated
  audit slice via `python_ported_output_cost_breakdown()`.
- `Output!P37:T58` Cathode Production process-stage rows now use scenario-derived
  cathode chemistry, recycled/virgin precursor availability, raw-material costs,
  and cathode environmental tables instead of the workbook's default
  `Select Chemistry -> #N/A -> 0` cached outputs. Direct regeneration now uses
  `cathode_direct_regeneration_environment_summary()` to reproduce the workbook
  Direct environmental array formulas from `Mat. Conv Par.` and `GREET IO`, plus
  the scenario-derived Direct cathode raw-material cost path instead of the
  workbook `#NAME?` cached cost.
- `Output!B202:H209` Battery production cost rows are now formula-ported from
  the manufacturing cost summaries, including virgin and recycled material
  route columns.
- `Output!J202:O210` Recycling cost rows are now formula-ported for Pyro,
  Hydro, Direct, and Custom. The port preserves preprocessing/CM recovery
  throughput weighting, annualized capital cost column offsets, feedstock payment
  negative-value clipping, and default workbook error propagation to zero.
- `Output!L216:S227` Recycling revenue rows now have a Python-calculated audit
  table via `python_ported_output_recycling_revenue_table()`. The audit now
  uses `cm_recovery_revenue_output_table()` to calculate product revenues from
  CM recovery product slots, quantities, and price lookups instead of reading
  cached `CM Rec Par.` revenue rows.
- CM recovery product and revenue calculations are now fully scenario-derived
  for Pyro, Hydro, Direct, and Custom. Product yields are calculated from the
  current black-mass composition and recovery formulas instead of returning the
  workbook's selected output slots first. The same scenario-derived product map
  now feeds recycling revenue, material-conversion precursor availability,
  cathode recycled/virgin precursor splits, and user-facing export tables.
- `Report!AA20:AE27` and `Report!AA39:AE45` now have Python-calculated report
  tables via `python_ported_report_manufacturing_comparison()`,
  `python_ported_report_closed_loop_total_results()`, and
  `python_ported_report_comparison()`. The Streamlit overview and ZIP export use
  the calculated report table, while workbook snapshot readers remain available
  for regression/audit tests.
- Scenario-level end-to-end fixtures now cover an `NMC(622)` pack feedstock
  recycling case for Pyro, Hydro, and Direct through
  `python_ported_stage_summary()`, including preprocessing throughput/cost,
  CM recovery throughput/cost, material conversion, cathode production, cell
  manufacturing, and pack manufacturing outputs.
- The Streamlit Dashboard now has a workflow status layer with explicit
  calculation badges (`PYTHON PORT`, `MIXED`, and `WORKBOOK SNAPSHOT`) plus
  workflow tabs for scenario flow, Output audit tables, and saved workbook
  snapshots. The status metadata is centralized in `src/recycle_cost/ui_status.py`.
- The Streamlit interface has been refactored into a user-facing tool with
  Chinese/English language switching, workflow tabs for overview, recycling
  process, cathode/manufacturing, parameters, and CSV export. Migration and audit
  details are hidden from the main app experience.
- The user workflow now includes scenario presets, non-negative/range-constrained
  numeric inputs, scenario guidance messages, a current-scenario summary table, CSV
  result exports, and JSON export for the active scenario.
- Scenario files exported from the app can now be uploaded back into the sidebar to
  restore inputs, and the export page offers a one-click ZIP package for the scenario
  plus result CSVs.
- The Parameters page now presents structured current-model parameter tables for
  scenario inputs, feedstock streams, transport distances, preprocessing yields,
  black-mass composition, CM recovery product yields/prices, cathode precursor
  requirements, chemical prices, utility prices, and conversion costs. The previous
  raw workbook row/column preview has been removed from the user-facing interface.
- Collection and transport environmental calculations now use scenario-derived
  transport segment distances rather than reading the workbook route-distance rows
  during Python-calculated runs. Default workbook round-trip distance splits are still
  preserved for regression matching.

Next priorities:

1. Continue replacing remaining workbook snapshot readers in auxiliary audit views
   with formula-derived functions where they are still user-facing or feed exports.

## Tests

```bash
pytest -q
```
