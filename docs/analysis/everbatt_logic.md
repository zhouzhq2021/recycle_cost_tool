# EverBatt 2023 Logic Reconnaissance

## Current Project State

- A uv project has been initialized in this folder.
- The virtual environment is at `.venv`.
- Installed dependencies: `streamlit`, `pandas`, `openpyxl`, `oletools`.
- Analysis artifacts:
  - `docs/analysis/everbatt_analysis.json`
  - `docs/analysis/vba_olevba.txt`
  - `scripts/analyze_everbatt.py`

Run the analyzer with:

```bash
source /home/zhouzhq/recycle_cost/.venv/bin/activate
python scripts/analyze_everbatt.py
```

## Key Finding

The workbook is not primarily implemented as VBA business logic. The VBA macros are lightweight UI helpers:

- `Show_Cellc`, `Show_Recyclec`, `Show_Cathodec`, `Show_Revenuec`: recalculate and toggle visible charts on `Output`.
- `Show_comp_chart`, `Show_breakdwon_chart`: recalculate and show comparison/breakdown charts on `Report`.
- `Reset_recycle`, `Reset_Cathode`: temporarily set `K33` or `Q33` to `0`, calculate, then set back to `1`.
- `Workbook_Open` and worksheet event handlers are effectively empty.

Therefore, the Streamlit replica should focus on translating Excel formulas, parameter tables, validation rules, and report/chart layouts rather than porting VBA.

## Workbook Structure

The workbook has 17 sheets:

- `ReadMe`: introductory notes.
- `Input`: main user input surface and validation prompts.
- `Output`: main numerical outputs and charts.
- `Report`: high-level comparison report.
- `Man Par.`: battery/cell manufacturing with virgin materials.
- `Col&Trans Par.`: collection and transportation.
- `Disassembly`: pack/module/cell disassembly parameters.
- `Preproc. Par.`: preprocessing parameters.
- `CM Rec Par.`: critical material recovery parameters for pyro, hydro, direct, and custom recycling.
- `Cath. Prod. Par.`: cathode powder production.
- `Man Rec Par.`: battery manufacturing with recycled materials.
- `Mat. Conv Par.`: recovered material conversion to precursors.
- `Unit Ops`: unit operation cost and power curves.
- `Materials`: material and chemical prices.
- `Geographic Par.`: regional cost and energy parameters.
- `BatPaC IO`: BatPaC-derived battery manufacturing inputs.
- `GREET IO`: GREET-derived fuel, energy, and emissions factors.

Formula-heavy sheets are:

- `CM Rec Par.`: 6,926 formulas.
- `Cath. Prod. Par.`: 3,837 formulas.
- `Preproc. Par.`: 2,490 formulas.
- `Man Rec Par.`: 793 formulas.
- `Man Par.`: 659 formulas.
- `Unit Ops`: 654 formulas.

## Calculation Flow

The dependency scan shows the model is a spreadsheet calculation graph:

1. `Input` captures scenario choices: battery chemistry, plant locations, battery metric, transport distances, feedstock mix, recycling process, cathode chemistry, recycled content, and throughput.
2. Shared data tables supply defaults:
   - `BatPaC IO`: battery bill of materials and manufacturing references.
   - `GREET IO`: energy and emissions factors.
   - `Materials`: commodity, chemical, and recovered material prices.
   - `Geographic Par.`: region-specific labor, utility, transport, and capital adjustment factors.
3. Process modules calculate costs, material flows, energy use, water use, emissions, and revenues:
   - manufacturing: `Man Par.`, `Man Rec Par.`
   - logistics: `Col&Trans Par.`, `Disassembly`
   - recycling: `Preproc. Par.`, `CM Rec Par.`
   - conversion and cathode production: `Mat. Conv Par.`, `Cath. Prod. Par.`
4. `Output` aggregates module results by scenario, unit, chemistry, process, and selected battery metric.
5. `Report` pulls selected output rows into comparison charts and normalized summaries.

Important cross-sheet dependency hotspots:

- `Output` depends heavily on `CM Rec Par.`, `Input`, `Preproc. Par.`, `Cath. Prod. Par.`, `Man Rec Par.`, `Man Par.`, and `Disassembly`.
- `CM Rec Par.` depends heavily on `Unit Ops`, `GREET IO`, `Preproc. Par.`, `Input`, `Geographic Par.`, and `Materials`.
- `Cath. Prod. Par.` depends heavily on `GREET IO`, `Mat. Conv Par.`, `Input`, `Geographic Par.`, `Materials`, and `Unit Ops`.
- `Mat. Conv Par.` depends heavily on `GREET IO`, `CM Rec Par.`, `Input`, `Preproc. Par.`, and `Col&Trans Par.`.

## Public Reference Material

Publicly available references indicate:

- EverBatt is Argonne's closed-loop battery recycling cost and environmental impact model.
- The 2019 report `ANL-19/16` describes the methodology: cost analysis, life-cycle analysis, process scaling, geographic variation, battery manufacturing, transportation, recycling, material conversion, and cathode powder production.
- Argonne has an `EverBatt Lite` web app. Its own landing page states that it is a user-friendly web interface for the larger Excel model, but only a small subset is implemented and current modules focus on greenhouse gas emissions.
- I did not find a public full source-code implementation of the Excel workbook logic. EverBatt Lite and its API documentation are useful design references, but not a full replacement for translating `EverBatt 2023.xlsm`.

Reference links:

- EverBatt Lite: https://everbatt.amd.anl.gov/
- EverBatt Lite recycling benefits module: https://everbatt.amd.anl.gov/recycling_benefits
- OSTI technical report record: https://www.osti.gov/biblio/1530874
- Argonne PDF report: https://publications.anl.gov/anlpubs/2019/07/153050.pdf

## Streamlit Porting Strategy

Recommended implementation order:

1. Build a workbook extraction layer:
   - Parse parameters from each worksheet into typed `pandas` tables.
   - Preserve original sheet/cell references in metadata for traceability.
   - Keep the Excel workbook as a regression oracle during early development.
2. Implement a formula evaluation layer:
   - Start with formulas feeding `Output` and `Report`.
   - Translate repeated formula blocks into explicit Python functions.
   - Use dataclasses or Pydantic-style structures for scenario inputs and intermediate process outputs.
3. Implement modules in this order:
   - `Input` schema and defaults.
   - `Geographic Par.`, `Materials`, `BatPaC IO`, `GREET IO`.
   - `Man Par.` and `Col&Trans Par.`.
   - `Preproc. Par.` and `CM Rec Par.` because they drive most recycling outputs.
   - `Mat. Conv Par.`, `Cath. Prod. Par.`, then `Man Rec Par.`.
   - `Output` and `Report` aggregation.
4. Add Streamlit UI:
   - Sidebar scenario controls corresponding to `Input`.
   - Main tabs: `Inputs`, `Cost`, `Energy & Emissions`, `Material Flows`, `Revenue`, `Report`.
   - Chart toggles can replace the VBA show/hide macros.
5. Add regression tests:
   - Snapshot default scenario outputs from the workbook.
   - Compare Python results against workbook values within tolerances.
   - Add per-module tests before building the full UI.

## Practical Notes

- `openpyxl` could not read the original workbook directly because some XML font `family` values exceed its allowed range. The analyzer creates a temporary fixed copy under `/tmp` and leaves the original workbook unchanged.
- Excel formula cached values are available for many cells, but formula recalculation is not performed by `openpyxl`. For validation, we should either use saved workbook outputs as snapshots or run Excel/LibreOffice externally if exact recalculation is required.
- VBA should be treated as UI behavior only unless future inspection finds hidden compiled logic. Current `olevba` output does not show any substantive calculation macros.
