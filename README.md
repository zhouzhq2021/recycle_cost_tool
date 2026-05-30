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

## Run Scenarios From CLI

Use `scripts/run_scenario.py` to run one or more scenarios without Streamlit and export
calculated result tables:

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run python scripts/run_scenario.py \
  --preset pack_hydro \
  --out-dir scenario_runs \
  --include-parameters
```

Inputs:

- `--preset`: built-in scenario preset. Can be provided multiple times.
- `--scenario-json`: scenario JSON exported by the app. Can be provided multiple times.
- `--process`: optional process override: `Pyro`, `Hydro`, `Direct`, or `Custom`.
- `--include-parameters`: also export current model parameter tables.

Each scenario gets its own output directory with `scenario.json`, `summary.json`, and CSV
files for stage summary, process-stage output, cost breakdown, recycling revenue,
manufacturing summary, output summary, and report results.

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

## Current Roadmap

The current app uses Python-calculated tables for user-facing Streamlit workflows and
keeps workbook snapshots as regression oracles. The detailed module status is tracked in
`docs/analysis/migration_checklist.md`.

Remaining work:

- Move remaining workbook-backed constants out of ad hoc cell reads and into typed,
  grouped parameter objects.
- Keep snapshot readers confined to tests and developer audit paths.
- Expand the UI scenario model from a single editable feedstock stream to the full
  multi-row feedstock model already supported by `Scenario.feedstocks`.
- Clarify and document the `Custom` route boundary: unsupported, user-specified, or
  workbook-audit-only.
- Strengthen scenario validation for incompatible chemistry, process, feedstock, and
  throughput combinations.
- Split `app.py` further so translation strings, presets, sidebar scenario construction,
  validation, result-table assembly, and page layout have separate ownership.
- Continue replacing local table-schema string literals with shared constants from
  `schemas.py`.

Maintenance rules:

- Workbook snapshots remain the regression oracle, not the user-facing calculation path.
- Formula ports need tests against workbook defaults plus at least one scenario-sensitive
  test when user inputs should affect the result.
- Known deviations from workbook behavior should be documented in
  `docs/analysis/migration_checklist.md`.

## Tests

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q
```
