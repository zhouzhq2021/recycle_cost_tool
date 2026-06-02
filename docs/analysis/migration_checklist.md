# EverBatt Migration Checklist

This checklist tracks the Python migration status at the module/block level. Workbook
snapshot readers remain regression oracles; user-facing Streamlit paths should prefer
Python-calculated tables.

| Area | Workbook range / source | Status | Notes |
| --- | --- | --- | --- |
| Scenario inputs | `Input` | ported | `Scenario` is typed; workbook default construction now uses `parameters.py`. |
| Parameter access | workbook sheets/cells | in progress | Shared workbook access lives in `src/recycle_cost/parameters.py`; remaining modules should move direct sheet reads here over time. |
| Collection and transport | `Col&Trans Par.`, `GREET IO`, `Output!B37:C59` | ported | Scenario distances drive cost and environment; snapshot deltas remain in tests. |
| Disassembly | `Disassembly`, `BatPaC IO`, `Output!E37:G59` | ported | Scenario feedstock flow drives cost, revenue, and recovered materials. |
| Preprocessing | `Preproc. Par.` | ported with centralized parameters | Formula path is Python; fixed plant/OPEX/environment parameters are Python constants; large composition and unit-operation source tables remain centralized parameter lookups. |
| CM recovery | `CM Rec Par.` | ported with parity caveat | Plant parameters, equipment selections, OPEX baselines, feed costs, product prices, product outputs, CAPEX/OPEX, and revenue rows are Python-calculated. CM throughput is split into material-flow, routed, and cost-design tonnes to mirror Excel's mixed throughput formulas. |
| Material conversion | `Mat. Conv Par.` | ported | Available precursor conversion, allocation audit factors, recycling economics, recycling environment audit tables, and total summary are scenario-derived Python calculations with workbook deltas. |
| Cathode production | `Cath. Prod. Par.`, `Mat. Conv Par.`, `GREET IO` | ported with workbook parameters | Cost, split, raw material, utility, labor, CAPEX/OPEX, and direct regeneration paths are Python-calculated. |
| Cell and pack manufacturing | `Man Par.`, `Man Rec Par.`, `Output!B11:H32` | ported with workbook parameters | Virgin/recycled manufacturing summaries are Python-calculated. |
| Output snapshots | `Output` | oracle only | Snapshot readers moved to `reporting_snapshots.py`; UI/export uses Python-calculated tables. |
| Report snapshots | `Report` | oracle only | Snapshot readers moved to `reporting_snapshots.py`; UI/export uses Python-calculated report tables. |
| Streamlit service layer | `app.py` | refactored | Scenario serialization, user table cleaning, parameter tables, CSV, and ZIP export moved to `app_services.py`. |
| Table schemas | Python outputs | in progress | Shared column constants in `schemas.py` now cover common, audit, output, stage, transport, manufacturing, and cathode table fields; continue replacing remaining local string literals opportunistically. |

## Formula Work Status

1. [DONE] `Mat. Conv Par.` total-summary formula port is available through `mat_conv_total_summary_calculated()`.
2. [DONE] Direct/Custom recycling-environment deltas are retained as audit deltas; Python uses scenario-derived allocation and transport values consistently.
3. [DONE] Non-default scenario tests cover material-conversion chemistry sensitivity, cathode chemistry switching, and transport-distance linkage into material-conversion environment.
4. [DONE] `CM Rec Par.` process parameter rows used by the runtime path are now ported into Python constants, and OPEX scales with scenario throughput.
5. [ONGOING] Some workbook constants remain as centralized workbook parameters in `parameters.py`; major CM recovery and fixed preprocessing runtime parameters are now Python constants, while larger source tables should move to typed dataclass/grouped parameter modules next.
6. [DONE] CM recovery throughput semantics are split into typed objects: material-flow tonnes for process composition, routed tonnes for Output aggregation, and `DC25`-style cost-design tonnes for unit cost formulas.
7. [DONE] `Manufacturing scrap: electrode` Direct recycling GHG now uses the feedstock-specific preprocessing process GHG path and matches LibreOffice output.

## Snapshot Boundary

- Snapshot readers in `reporting_snapshots.py` remain regression oracles only.
- User-facing Streamlit sections, exports, Output tables, and Report tables prefer Python-calculated tables.
- Workbook columns and delta columns are intentionally preserved in audit tables, then hidden by `user_table()` for normal UI display.
