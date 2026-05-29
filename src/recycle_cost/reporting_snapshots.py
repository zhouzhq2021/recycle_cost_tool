from __future__ import annotations

import pandas as pd

from .parameters import workbook_sheet
from .transport import _num


def _valid(value) -> bool:
    return value is not None and str(value).strip() not in {"", "0"}


def _label(value) -> str:
    return str(value).strip()


def output_cell_pack_summary() -> pd.DataFrame:
    ws = workbook_sheet("Output")
    records = []
    columns = {
        "Virgin Manufacture": 3,
        "Pyro recycled manufacturing": 4,
        "Hydro recycled manufacturing": 5,
        "Direct recycled manufacturing": 6,
        "Custom recycled manufacturing": 7,
        "Pack Virgin Manufacture": 8,
    }
    rows = [11, *range(13, 19), *range(20, 33)]
    for row in rows:
        metric = ws.cell(row, 2).value
        if not _valid(metric):
            continue
        record = {"metric": _label(metric)}
        for column, col_idx in columns.items():
            record[column] = _num(ws.cell(row, col_idx).value)
        records.append(record)
    return pd.DataFrame(records)


def output_process_stage_summary() -> pd.DataFrame:
    ws = workbook_sheet("Output")
    records = []
    specs = [
        ("Collection & Transport", 2, {"total": 3}),
        ("Disassembly", 5, {"pack_to_module": 6, "module_to_cell": 7}),
        ("Recycle", 9, {"Pyro": 10, "Hydro": 11, "Direct": 12, "Custom": 13}),
        ("Cathode Production", 15, {"Pyro": 16, "Hydro": 17, "Custom": 18, "Virgin": 19, "Direct regeneration": 20}),
    ]
    rows = [37, *range(39, 45), *range(46, 60)]
    for stage, label_col, value_cols in specs:
        for row in rows:
            metric = ws.cell(row, label_col).value
            if not _valid(metric):
                continue
            record = {"stage": stage, "metric": _label(metric)}
            for column, col_idx in value_cols.items():
                record[column] = _num(ws.cell(row, col_idx).value)
            records.append(record)
    return pd.DataFrame(records)


def output_cost_breakdown() -> pd.DataFrame:
    ws = workbook_sheet("Output")
    sections = [
        ("Battery production cost", 2, range(3, 9)),
        ("Recycling cost", 10, range(11, 16)),
        ("Cathode production cost", 17, range(18, 23)),
    ]
    records = []
    for section, label_col, cols in sections:
        headers = [_label(ws.cell(201, col).value) for col in cols]
        for row in range(202, 211):
            item = ws.cell(row, label_col).value
            if not _valid(item):
                continue
            record = {"section": section, "item": _label(item)}
            for header, col in zip(headers, cols, strict=True):
                if _valid(header):
                    record[header] = _num(ws.cell(row, col).value)
            records.append(record)
    return pd.DataFrame(records)


def output_recycling_revenue_table() -> pd.DataFrame:
    ws = workbook_sheet("Output")
    records = []
    processes = {"Pyro": (12, 16), "Hydro": (13, 17), "Direct": (14, 18), "Custom": (15, 19)}
    for row in range(216, 228):
        for process, (material_col, value_col) in processes.items():
            material = ws.cell(row, material_col).value
            if _valid(material):
                records.append(
                    {
                        "process": process,
                        "material": _label(material),
                        "value_per_kg_feedstock": _num(ws.cell(row, value_col).value),
                    }
                )
    return pd.DataFrame(records)


def report_manufacturing_comparison() -> pd.DataFrame:
    ws = workbook_sheet("Report")
    records = []
    columns = {"Virgin Manufacture": 28, "Pyro": 29, "Hydro": 30, "Direct": 31}
    for row in range(20, 28):
        metric = ws.cell(row, 27).value
        if not _valid(metric):
            continue
        record = {"metric": _label(metric)}
        for column, col_idx in columns.items():
            record[column] = _num(ws.cell(row, col_idx).value)
        records.append(record)
    return pd.DataFrame(records)


def report_closed_loop_total_results() -> pd.DataFrame:
    ws = workbook_sheet("Report")
    records = []
    columns = {"Pyro": 28, "Hydro": 29, "Direct": 30, "Custom": 31}
    for row in range(39, 46):
        metric = ws.cell(row, 27).value
        if not _valid(metric):
            continue
        record = {"metric": _label(metric)}
        for column, col_idx in columns.items():
            record[column] = _num(ws.cell(row, col_idx).value)
        records.append(record)
    return pd.DataFrame(records)
