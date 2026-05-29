from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class CalculationStatus:
    workflow: str
    workbook_area: str
    status: str
    source: str
    notes: str


STATUS_STYLES = {
    "Python port": {
        "label": "PYTHON PORT",
        "background": "#dcfce7",
        "foreground": "#166534",
        "border": "#86efac",
    },
    "Mixed": {
        "label": "MIXED",
        "background": "#fef3c7",
        "foreground": "#92400e",
        "border": "#fcd34d",
    },
    "Workbook snapshot": {
        "label": "WORKBOOK SNAPSHOT",
        "background": "#e0f2fe",
        "foreground": "#075985",
        "border": "#7dd3fc",
    },
}


CALCULATION_STATUSES = (
    CalculationStatus(
        "Collection & transport",
        "Col&Trans Par.; Output!B37:C59",
        "Python port",
        "Python formulas",
        "Cost and environmental rows are scenario-driven from transport segment distances.",
    ),
    CalculationStatus(
        "Disassembly",
        "Disassembly Par.; Output!E37:G59",
        "Python port",
        "Python formulas",
        "Cost, revenue, and recovered-material flows are scenario-driven.",
    ),
    CalculationStatus(
        "Preprocessing",
        "Preproc. Par.",
        "Python port",
        "Python formulas",
        "Feedstock composition, product split, equipment, CAPEX, OPEX, and environment are scenario-driven.",
    ),
    CalculationStatus(
        "CM recovery",
        "CM Rec Par.",
        "Python port",
        "Python formulas",
        "Plant parameters, equipment selections, OPEX baselines, feed costs, product prices, product outputs, CAPEX/OPEX, and Output revenue rows are scenario-driven Python paths.",
    ),
    CalculationStatus(
        "Material conversion",
        "Mat Conv Par.",
        "Python port",
        "Python formulas with workbook audit deltas",
        "Available precursors, allocation/economics/environment audit factors, conversion cost, and total summary are scenario-derived.",
    ),
    CalculationStatus(
        "Cathode production",
        "Cath. Prod. Par.; Output!O37:T58; Output!Q202:V209",
        "Python port",
        "Python formulas",
        "Split, raw materials, utilities, labor, CAPEX, maintenance, total cost, and Output audit rows are ported.",
    ),
    CalculationStatus(
        "Cell and pack manufacturing",
        "Manuf. Par.; Man Rec Par.; Output!B11:H32; Output!B202:H209",
        "Python port",
        "Python formulas",
        "Virgin/recycled cell, pack mass/environment, and Output cost rows are ported.",
    ),
    CalculationStatus(
        "Output and report",
        "Output; Report",
        "Python port",
        "Python formulas with optional workbook audit deltas",
        "User-facing Output summary, process-stage, cost-breakdown, recycling-revenue, and Report tables use Python calculations.",
    ),
)


def calculation_status_rows() -> pd.DataFrame:
    return pd.DataFrame([status.__dict__ for status in CALCULATION_STATUSES])


def status_style(status: str) -> dict[str, str]:
    return STATUS_STYLES.get(status, STATUS_STYLES["Workbook snapshot"])
