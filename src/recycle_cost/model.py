from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from .parameters import get_workbook_default_scenario_parameters, get_workbook_scenario_options, workbook_number, workbook_sheet
from .workbook import ANALYSIS_PATH, worksheet_to_frame


NA_VALUES = {"#N/A", "#VALUE!", "#DIV/0!", "#REF!", "#NAME?"}


@dataclass(frozen=True)
class FeedstockInput:
    chemistry: str
    feedstock_type: str
    tonnes_per_year: float


@dataclass(frozen=True)
class TransportDistances:
    collection_to_disassembly: float
    disassembly_to_preprocessor: float
    preprocessor_to_cm_recovery: float
    manufacturer_to_preprocessor_or_cm_recovery: float
    recycler_to_cathode_producer: float
    cathode_producer_to_manufacturer: float


@dataclass(frozen=True)
class Scenario:
    battery_manufactured: str
    throughput_gwh_per_year: float | None
    manufacturing_chemistry: str
    manufacturing_location: str
    battery_collected: str
    feedstock_chemistry: str
    feedstock_type: str
    feedstock_tonnes_per_year: float | None
    recycling_process: str
    cathode_chemistry: str
    recycled_content: float | None
    cathode_throughput_gwh_per_year: float | None
    transport_distances: TransportDistances
    feedstocks: tuple[FeedstockInput, ...]
    recycling_flow_variant: str = "old"
    custom_nmc_ni: float | None = 6.0
    custom_nmc_co: float | None = 2.0
    custom_nmc_mn: float | None = 2.0
    custom_feedstock_composition: dict[str, float] | None = None
    custom_feedstock_composition_feedstock_type: str | None = None
    new_flow_parameters: dict[str, float] | None = None


@dataclass(frozen=True)
class ScenarioOptions:
    battery_manufactured: tuple[str, ...]
    battery_collected: tuple[str, ...]
    chemistries: tuple[str, ...]
    cathode_chemistries: tuple[str, ...]
    locations: tuple[str, ...]
    recycling_processes: tuple[str, ...]
    feedstock_types: tuple[str, ...]


SCENARIO_PRESETS = {
    "default": {
        "label_key": "preset_default",
        "battery_manufactured": "Pack",
        "throughput": 50.0,
        "manufacturing_chemistry": "NMC(622)",
        "manufacturing_location": "U.S.",
        "battery_collected": "Select Battery",
        "feedstock_chemistry": "NMC(622)",
        "feedstock_type": "Black mass",
        "feedstock_tonnes": 10000.0,
        "recycling_process": "Hydrometallurgical",
        "cathode_chemistry": "NMC(622)",
        "cathode_throughput": 0.0,
        "recycled_content": 0.0,
    },
    "pack_pyro": {
        "label_key": "preset_pack_pyro",
        "battery_manufactured": "Pack",
        "throughput": 50.0,
        "manufacturing_chemistry": "NMC(622)",
        "manufacturing_location": "U.S.",
        "battery_collected": "Module",
        "feedstock_chemistry": "NMC(622)",
        "feedstock_type": "End-of-life battery: pack",
        "feedstock_tonnes": 10000.0,
        "recycling_process": "Pyrometallurgical",
        "cathode_chemistry": "NMC(622)",
        "cathode_throughput": 10.0,
        "recycled_content": 0.2,
    },
    "pack_hydro": {
        "label_key": "preset_pack_hydro",
        "battery_manufactured": "Pack",
        "throughput": 50.0,
        "manufacturing_chemistry": "NMC(622)",
        "manufacturing_location": "U.S.",
        "battery_collected": "Module",
        "feedstock_chemistry": "NMC(622)",
        "feedstock_type": "End-of-life battery: pack",
        "feedstock_tonnes": 10000.0,
        "recycling_process": "Hydrometallurgical",
        "cathode_chemistry": "NMC(622)",
        "cathode_throughput": 10.0,
        "recycled_content": 0.2,
    },
    "pack_direct": {
        "label_key": "preset_pack_direct",
        "battery_manufactured": "Pack",
        "throughput": 50.0,
        "manufacturing_chemistry": "NMC(622)",
        "manufacturing_location": "U.S.",
        "battery_collected": "Module",
        "feedstock_chemistry": "NMC(622)",
        "feedstock_type": "End-of-life battery: pack",
        "feedstock_tonnes": 10000.0,
        "recycling_process": "Direct",
        "cathode_chemistry": "NMC(622)",
        "cathode_throughput": 10.0,
        "recycled_content": 0.2,
    },
    "pack_custom": {
        "label_key": "preset_pack_custom",
        "battery_manufactured": "Pack",
        "throughput": 50.0,
        "manufacturing_chemistry": "NMC(622)",
        "manufacturing_location": "U.S.",
        "battery_collected": "Module",
        "feedstock_chemistry": "NMC(622)",
        "feedstock_type": "End-of-life battery: pack",
        "feedstock_tonnes": 10000.0,
        "recycling_process": "Custom",
        "cathode_chemistry": "NMC(622)",
        "cathode_throughput": 10.0,
        "recycled_content": 0.2,
    },
    "scrap_direct": {
        "label_key": "preset_scrap_direct",
        "battery_manufactured": "Cell",
        "throughput": 50.0,
        "manufacturing_chemistry": "NMC(622)",
        "manufacturing_location": "U.S.",
        "battery_collected": "Cell",
        "feedstock_chemistry": "NMC(622)",
        "feedstock_type": "Manufacturing scrap: electrode",
        "feedstock_tonnes": 5000.0,
        "recycling_process": "Direct",
        "cathode_chemistry": "NMC(622)",
        "cathode_throughput": 10.0,
        "recycled_content": 0.2,
    },
}


def _clean_number(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, str):
        if value in NA_VALUES:
            return None
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def scenario_options() -> ScenarioOptions:
    params = get_workbook_scenario_options()
    return ScenarioOptions(
        battery_manufactured=params.battery_manufactured,
        battery_collected=params.battery_collected,
        chemistries=params.chemistries,
        cathode_chemistries=params.cathode_chemistries,
        locations=params.locations,
        recycling_processes=params.recycling_processes,
        feedstock_types=params.feedstock_types,
    )


def default_scenario() -> Scenario:
    params = get_workbook_default_scenario_parameters()
    distances = params.transport_distances

    return Scenario(
        battery_manufactured=params.battery_manufactured,
        throughput_gwh_per_year=params.throughput_gwh_per_year,
        manufacturing_chemistry=params.manufacturing_chemistry,
        manufacturing_location=params.manufacturing_location,
        battery_collected=params.battery_collected,
        feedstock_chemistry=params.feedstock_chemistry,
        feedstock_type=params.feedstock_type,
        feedstock_tonnes_per_year=params.feedstock_tonnes_per_year,
        recycling_process=params.recycling_process,
        cathode_chemistry=params.cathode_chemistry,
        recycled_content=params.recycled_content,
        cathode_throughput_gwh_per_year=params.cathode_throughput_gwh_per_year,
        transport_distances=TransportDistances(
            collection_to_disassembly=distances.collection_to_disassembly,
            disassembly_to_preprocessor=distances.disassembly_to_preprocessor,
            preprocessor_to_cm_recovery=distances.preprocessor_to_cm_recovery,
            manufacturer_to_preprocessor_or_cm_recovery=distances.manufacturer_to_preprocessor_or_cm_recovery,
            recycler_to_cathode_producer=distances.recycler_to_cathode_producer,
            cathode_producer_to_manufacturer=distances.cathode_producer_to_manufacturer,
        ),
        feedstocks=tuple(
            FeedstockInput(feedstock.chemistry, feedstock.feedstock_type, feedstock.tonnes_per_year)
            for feedstock in params.feedstocks
        ),
    )


def get_scenario_from_preset(preset_name: str) -> Scenario:
    p = SCENARIO_PRESETS[preset_name]
    base = default_scenario()
    return Scenario(
        battery_manufactured=p["battery_manufactured"],
        throughput_gwh_per_year=p["throughput"],
        manufacturing_chemistry=p["manufacturing_chemistry"],
        manufacturing_location=p["manufacturing_location"],
        battery_collected=p["battery_collected"],
        feedstock_chemistry=p["feedstock_chemistry"],
        feedstock_type=p["feedstock_type"],
        feedstock_tonnes_per_year=p["feedstock_tonnes"],
        recycling_process=p["recycling_process"],
        cathode_chemistry=p["cathode_chemistry"],
        recycled_content=p["recycled_content"],
        cathode_throughput_gwh_per_year=p["cathode_throughput"],
        transport_distances=base.transport_distances,
        feedstocks=(FeedstockInput(p["feedstock_chemistry"], p["feedstock_type"], p["feedstock_tonnes"]),),
    )


def scenario_recycling_process_key(scenario: Scenario) -> str | None:
    normalized = scenario.recycling_process.strip().casefold()
    if "pyro" in normalized:
        return "Pyro"
    if "hydro" in normalized:
        return "Hydro"
    if normalized == "direct":
        return "Direct"
    if normalized == "custom":
        return "Custom"
    return None


def uses_new_recycling_flow(scenario: Scenario) -> bool:
    return scenario.recycling_flow_variant == "new" and scenario_recycling_process_key(scenario) in {"Hydro", "Direct"}


def output_summary_table() -> pd.DataFrame:
    rows = [
        ("Cell manufacturing cost", "Cost", "per kWh battery produced", "C11", "D11", "E11", "F11", "G11"),
        ("Cell manufacturing total energy", "Energy", "MJ per kWh battery produced", "C13", "D13", "E13", "F13", "G13"),
        ("Cell manufacturing water", "Water", "gal per kWh battery produced", "C18", "D18", "E18", "F18", "G18"),
        ("Cell manufacturing NOx", "Emissions", "g per kWh battery produced", "C22", "D22", "E22", "F22", "G22"),
        ("Cell manufacturing PM10", "Emissions", "g per kWh battery produced", "C23", "D23", "E23", "F23", "G23"),
        ("Cell manufacturing SOx", "Emissions", "g per kWh battery produced", "C25", "D25", "E25", "F25", "G25"),
        ("Cell manufacturing GHGs", "Emissions", "g CO2e per kWh battery produced", "C32", "D32", "E32", "F32", "G32"),
        ("Collection and transport cost", "Cost", "per kg feedstock", "C37", None, None, None, None),
        ("Collection and transport total energy", "Energy", "MJ per kg feedstock", "C39", None, None, None, None),
        ("Recycling cost", "Cost", "per kg feedstock processed", None, "J37", "K37", "L37", "M37"),
        ("Recycling total energy", "Energy", "MJ per kg feedstock processed", None, "J39", "K39", "L39", "M39"),
        ("Recycling water", "Water", "gal per kg feedstock processed", None, "J44", "K44", "L44", "M44"),
        ("Recycling revenue", "Revenue", "per kg feedstock processed", None, "J59", "K59", "L59", "M59"),
        ("Recycling GHGs", "Emissions", "g CO2e per kg feedstock processed", None, "J58", "K58", "L58", "M58"),
    ]
    columns = ["Virgin", "Pyro", "Hydro", "Direct", "Custom"]
    records = []
    for label, category, unit, *addresses in rows:
        record = {"metric": label, "category": category, "unit": unit}
        for column, address in zip(columns, addresses, strict=True):
            record[column] = workbook_number("Output", address) if address else None
        records.append(record)
    return pd.DataFrame.from_records(records)


def report_comparison_table() -> pd.DataFrame:
    ws = workbook_sheet("Report")
    rows = []
    for row in range(20, 27):
        rows.append(
            {
                "metric": ws[f"AA{row}"].value,
                "Virgin Manufacture": _clean_number(ws[f"AB{row}"].value),
                "Pyro": _clean_number(ws[f"AC{row}"].value),
                "Hydro": _clean_number(ws[f"AD{row}"].value),
                "Direct": _clean_number(ws[f"AE{row}"].value),
            }
        )
    return pd.DataFrame(rows)


def sheet_catalog() -> pd.DataFrame:
    analysis = json.loads(Path(ANALYSIS_PATH).read_text(encoding="utf-8"))
    rows = []
    for sheet in analysis["sheets"]:
        summary = analysis["sheet_summaries"][sheet["name"]]
        rows.append(
            {
                "sheet": sheet["name"],
                "dimensions": summary["dimensions"],
                "nonempty_cells": summary["nonempty_cells"],
                "formula_cells": summary["formula_cells"],
                "role_hint": "; ".join(summary["title_values"][:3]),
            }
        )
    return pd.DataFrame(rows)


def dependency_table() -> pd.DataFrame:
    analysis = json.loads(Path(ANALYSIS_PATH).read_text(encoding="utf-8"))
    rows = []
    for target, sources in analysis["dependencies"]["cross_sheet_edges"].items():
        for source, count in sources:
            rows.append({"target_sheet": target, "source_sheet": source.strip(), "formula_refs": count})
    return pd.DataFrame(rows)


def parameter_preview(sheet: str, rows: int = 80, cols: int = 18) -> pd.DataFrame:
    frame = worksheet_to_frame(sheet, max_row=rows, max_col=cols)
    frame = frame.dropna(how="all").dropna(axis=1, how="all")
    frame.columns = [str(column) for column in frame.columns]
    frame.index = frame.index + 1
    return frame
