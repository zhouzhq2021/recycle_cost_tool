from __future__ import annotations

import math
from dataclasses import dataclass

import pandas as pd

from .model import FeedstockInput, Scenario
from .schemas import CommonColumns
from .transport import _num
from .workbook import load_everbatt_workbook


PACK_COMPONENTS = ("Copper", "Aluminum", "Plastics", "Steel", "Electronic part", "Insulation")
MODULE_COMPONENTS = ("Copper", "Aluminum", "Plastics", "Steel", "Electronic part", "Insulation")


@dataclass(frozen=True)
class DisassemblyParameters:
    cells_per_module: float
    modules_per_pack: float
    labor_hours_pack_removal: float
    labor_hours_pack_disassembly: float
    labor_hours_module_disassembly: float
    labor_rate_pack_removal: float
    labor_rate_pack_disassembly: float
    labor_rate_module_disassembly: float
    packs_per_year_reference: float
    modules_per_pack_reference: float
    pack_equipment_scale_cost: float
    pack_equipment_scale_exponent: float
    module_equipment_scale_cost: float
    module_equipment_scale_exponent: float
    building_cost_per_m2: float
    depreciation_capital_share: float
    depreciation_building_share: float
    variable_overhead_labor_share: float
    variable_overhead_depreciation_share: float
    gsa_labor_overhead_share: float
    gsa_depreciation_share: float
    rnd_depreciation_share: float
    launch_material_share: float
    launch_labor_overhead_share: float
    working_capital_overhead_share: float
    price_by_component: dict[str, float]


def default_disassembly_parameters() -> DisassemblyParameters:
    disassembly = load_everbatt_workbook(data_only=True)["Disassembly"]
    batpac = load_everbatt_workbook(data_only=True)["BatPaC IO"]
    return DisassemblyParameters(
        cells_per_module=_num(disassembly["C17"].value),
        modules_per_pack=_num(disassembly["C18"].value),
        labor_hours_pack_removal=_num(disassembly["C24"].value),
        labor_hours_pack_disassembly=_num(disassembly["C25"].value),
        labor_hours_module_disassembly=_num(disassembly["C26"].value),
        labor_rate_pack_removal=_num(disassembly["C30"].value),
        labor_rate_pack_disassembly=_num(disassembly["C31"].value),
        labor_rate_module_disassembly=_num(disassembly["C32"].value),
        packs_per_year_reference=_num(batpac["K53"].value),
        modules_per_pack_reference=_num(batpac["L53"].value),
        pack_equipment_scale_cost=_num(batpac["T49"].value),
        pack_equipment_scale_exponent=_num(batpac["T34"].value),
        module_equipment_scale_cost=_num(batpac["S49"].value),
        module_equipment_scale_exponent=_num(batpac["S34"].value),
        building_cost_per_m2=_num(batpac["A59"].value),
        depreciation_capital_share=_num(batpac["K59"].value),
        depreciation_building_share=_num(batpac["L59"].value),
        variable_overhead_labor_share=_num(batpac["F59"].value),
        variable_overhead_depreciation_share=_num(batpac["G59"].value),
        gsa_labor_overhead_share=_num(batpac["H59"].value),
        gsa_depreciation_share=_num(batpac["I59"].value),
        rnd_depreciation_share=_num(batpac["J59"].value),
        launch_material_share=_num(batpac["B59"].value),
        launch_labor_overhead_share=_num(batpac["C59"].value),
        working_capital_overhead_share=_num(batpac["D59"].value),
        price_by_component={component: _num(disassembly[f"C{row}"].value) for component, row in zip(PACK_COMPONENTS, range(54, 60), strict=True)},
    )


def _table_by_chemistry(sheet: str, top_left_col: int, header_row: int, first_value_row: int, rows: int) -> dict[str, list[float]]:
    ws = load_everbatt_workbook(data_only=True)[sheet]
    table: dict[str, list[float]] = {}
    for offset in range(8):
        column = top_left_col + offset
        chemistry = ws.cell(header_row, column).value
        if chemistry is None:
            continue
        table[str(chemistry)] = [_num(ws.cell(first_value_row + row, column).value) for row in range(rows)]
    return table


def chemistry_weight_table() -> dict[str, dict[str, float]]:
    ws = load_everbatt_workbook(data_only=True)["Disassembly"]
    table: dict[str, dict[str, float]] = {}
    for offset in range(8):
        column = 30 + offset
        chemistry = str(ws.cell(2, column).value)
        table[chemistry] = {
            "pack_kg": _num(ws.cell(3, column).value),
            "module_kg": _num(ws.cell(4, column).value),
            "cell_kg": _num(ws.cell(5, column).value),
        }
    return table


def pack_component_table() -> dict[str, dict[str, float]]:
    raw = _table_by_chemistry("Man Par.", 30, 27, 28, 13)
    table = {}
    for chemistry, values in raw.items():
        table[chemistry] = {
            "steel_1": values[0],
            "insulation_1": values[1],
            "steel_2": values[2],
            "battery_jacket": values[3],
            "aluminum": values[4],
            "steel_3": values[5],
            "coolant": values[6],
            "insulation_2": values[7],
            "copper_1": values[8],
            "copper_2": values[9],
            "copper_3": values[10],
            "plastic": values[11],
            "electronics": values[12],
        }
    return table


def module_component_table() -> dict[str, dict[str, float]]:
    raw = _table_by_chemistry("Man Par.", 30, 18, 19, 6)
    table = {}
    for chemistry, values in raw.items():
        table[chemistry] = {
            "copper_1": values[0],
            "plastics": values[1],
            "copper_2": values[2],
            "aluminum": values[3],
            "steel": values[4],
            "electronics": values[5],
        }
    return table


def _stream_output_type(feedstock_type: str) -> str:
    normalized = feedstock_type.strip().casefold()
    if normalized == "end-of-life battery: module":
        return "Module"
    if normalized == "end-of-life battery: cell":
        return "Cell"
    return ""


def _active_disassembly_feedstocks(scenario: Scenario) -> list[FeedstockInput]:
    return [item for item in scenario.feedstocks if _stream_output_type(item.feedstock_type)]


def disassembly_feedstock_table(scenario: Scenario) -> pd.DataFrame:
    weights = chemistry_weight_table()
    rows = []
    for item in _active_disassembly_feedstocks(scenario):
        output_type = _stream_output_type(item.feedstock_type)
        chemistry_weights = weights.get(item.chemistry, {})
        pack_kg = chemistry_weights.get("pack_kg", 0.0)
        module_kg = chemistry_weights.get("module_kg", 0.0)
        cell_kg = chemistry_weights.get("cell_kg", 0.0)
        if output_type == "Module" and module_kg:
            pack_equivalent_tonnes = item.tonnes_per_year / module_kg * pack_kg
        elif output_type == "Cell" and cell_kg:
            pack_equivalent_tonnes = item.tonnes_per_year / cell_kg * pack_kg
        else:
            pack_equivalent_tonnes = 0.0
        rows.append(
            {
                CommonColumns.CHEMISTRY: item.chemistry,
                "feedstock_type": item.feedstock_type,
                "output_type": output_type,
                "input_tonnes_per_year": item.tonnes_per_year,
                "pack_equivalent_tonnes_per_year": pack_equivalent_tonnes,
            }
        )

    frame = pd.DataFrame(rows)
    if frame.empty:
        return pd.DataFrame(
            columns=[
                CommonColumns.CHEMISTRY,
                "feedstock_type",
                "output_type",
                "input_tonnes_per_year",
                "pack_equivalent_tonnes_per_year",
                "share",
            ]
        )
    total = float(frame["pack_equivalent_tonnes_per_year"].sum())
    frame["share"] = frame["pack_equivalent_tonnes_per_year"] / total if total else 0.0
    return frame


def _weighted_component_values(feedstocks: pd.DataFrame, component_table: dict[str, dict[str, float]]) -> dict[str, float]:
    totals: dict[str, float] = {}
    for row in feedstocks.to_dict("records"):
        chemistry = row[CommonColumns.CHEMISTRY]
        share = float(row["share"])
        for name, value in component_table.get(chemistry, {}).items():
            totals[name] = totals.get(name, 0.0) + share * value
    return totals


def _pack_components(feedstocks: pd.DataFrame) -> dict[str, float]:
    values = _weighted_component_values(feedstocks, pack_component_table())
    return {
        "Copper": values.get("copper_3", 0.0) * 0.9 + values.get("copper_2", 0.0) + values.get("copper_1", 0.0),
        "Aluminum": values.get("aluminum", 0.0) + 0.2,
        "Plastics": 0.0,
        "Steel": values.get("steel_1", 0.0) + values.get("steel_2", 0.0) + values.get("steel_3", 0.0),
        "Electronic part": 3.5776000000000003,
        "Insulation": values.get("copper_3", 0.0) * 0.1 + values.get("insulation_1", 0.0) + values.get("insulation_2", 0.0),
    }


def _module_components(feedstocks: pd.DataFrame) -> dict[str, float]:
    values = _weighted_component_values(feedstocks, module_component_table())
    modules_per_pack = default_disassembly_parameters().modules_per_pack
    return {
        "Copper": (values.get("copper_1", 0.0) + values.get("copper_2", 0.0)) * modules_per_pack / 1000,
        "Aluminum": values.get("aluminum", 0.0) * modules_per_pack / 1000,
        "Plastics": values.get("plastics", 0.0) * modules_per_pack / 1000,
        "Steel": values.get("steel", 0.0) * modules_per_pack / 1000,
        "Electronic part": values.get("electronics", 0.0) * modules_per_pack / 1000,
        "Insulation": 0.0,
    }


def disassembly_material_recovery(scenario: Scenario) -> pd.DataFrame:
    feedstocks = disassembly_feedstock_table(scenario)
    params = default_disassembly_parameters()
    pack = _pack_components(feedstocks) if not feedstocks.empty else {component: 0.0 for component in PACK_COMPONENTS}
    module = _module_components(feedstocks) if not feedstocks.empty else {component: 0.0 for component in MODULE_COMPONENTS}
    rows = []
    for component in PACK_COMPONENTS:
        rows.append(
            {
                CommonColumns.COMPONENT: component,
                "pack_disassembly_kg_per_pack": pack[component],
                "module_disassembly_kg_per_pack": module[component],
                "price_per_kg": params.price_by_component[component],
                "pack_revenue_per_pack": pack[component] * params.price_by_component[component],
                "module_revenue_per_pack": module[component] * params.price_by_component[component],
            }
        )
    return pd.DataFrame(rows)


def _weighted_cell_weight(feedstocks: pd.DataFrame) -> float:
    if feedstocks.empty:
        return 0.0
    man_cell_weights = _table_by_chemistry("Man Par.", 4, 14, 16, 1)
    return sum(float(row["share"]) * man_cell_weights.get(row[CommonColumns.CHEMISTRY], [0.0])[0] for row in feedstocks.to_dict("records"))


def disassembly_weight_summary(scenario: Scenario) -> dict[str, float]:
    feedstocks = disassembly_feedstock_table(scenario)
    if feedstocks.empty or float(feedstocks["pack_equivalent_tonnes_per_year"].sum()) <= 0:
        return {
            "pack_equivalent_tonnes_per_year": 0.0,
            "pack_weight_kg": 0.0,
            "cell_weight_kg": 0.0,
            "pack_count_per_year": 0.0,
        }

    params = default_disassembly_parameters()
    cell_weight_kg = _weighted_cell_weight(feedstocks) * params.cells_per_module * params.modules_per_pack
    materials = disassembly_material_recovery(scenario)
    pack_components = float(materials["pack_disassembly_kg_per_pack"].sum())
    module_components = float(materials["module_disassembly_kg_per_pack"].sum())
    values = _weighted_component_values(feedstocks, pack_component_table())
    pack_weight_kg = (
        cell_weight_kg
        + pack_components
        + module_components
        + values.get("battery_jacket", 0.0)
        + values.get("coolant", 0.0)
    )
    total_tonnes = float(feedstocks["pack_equivalent_tonnes_per_year"].sum())
    pack_count = math.ceil(total_tonnes * 1000 / pack_weight_kg * params.modules_per_pack * params.cells_per_module) if pack_weight_kg else 0
    return {
        "pack_equivalent_tonnes_per_year": total_tonnes,
        "pack_weight_kg": pack_weight_kg,
        "cell_weight_kg": cell_weight_kg,
        "pack_count_per_year": float(pack_count),
    }


def disassembly_cost_breakdown(scenario: Scenario) -> pd.DataFrame:
    params = default_disassembly_parameters()
    weights = disassembly_weight_summary(scenario)
    pack_weight = weights["pack_weight_kg"]
    total_kg = weights["pack_equivalent_tonnes_per_year"] * 1000
    if pack_weight <= 0 or total_kg <= 0:
        return pd.DataFrame(
            [
                {CommonColumns.ITEM: item, "pack_disassembly": 0.0, "module_disassembly": 0.0}
                for item in [
                    "Materials",
                    "Direct labor",
                    "Depreciation",
                    "Variable overhead",
                    "General, sales, administration",
                    "Research and development",
                    "Total cost",
                    "Total investment",
                ]
            ]
        )

    pack_labor_per_pack = (
        params.labor_hours_pack_removal * params.labor_rate_pack_removal
        + params.labor_hours_pack_disassembly * params.labor_rate_pack_disassembly
    )
    module_labor_per_pack = params.labor_hours_module_disassembly * params.labor_rate_module_disassembly
    pack_labor = pack_labor_per_pack / pack_weight
    module_labor = module_labor_per_pack / pack_weight

    pack_throughput = total_kg / pack_weight / params.packs_per_year_reference
    module_throughput = weights["pack_count_per_year"] / params.cells_per_module / (
        params.packs_per_year_reference * params.modules_per_pack_reference
    )
    pack_area = params.pack_equipment_scale_cost * pack_throughput ** params.pack_equipment_scale_exponent
    module_area = params.module_equipment_scale_cost * module_throughput ** params.module_equipment_scale_exponent
    pack_building = pack_area * params.building_cost_per_m2 / total_kg
    module_building = module_area * params.building_cost_per_m2 / total_kg

    def build(labor: float, building: float) -> dict[str, float]:
        materials = 0.0
        capital_equipment = 0.0
        depreciation = capital_equipment * params.depreciation_capital_share + params.depreciation_building_share * building
        variable_overhead = labor * params.variable_overhead_labor_share + params.variable_overhead_depreciation_share * depreciation
        gsa = (labor + variable_overhead) * params.gsa_labor_overhead_share + params.gsa_depreciation_share * depreciation
        rnd = depreciation * params.rnd_depreciation_share
        launch_cost = materials * params.launch_material_share + params.launch_labor_overhead_share * (labor + variable_overhead)
        working_capital = variable_overhead * params.working_capital_overhead_share
        total_variable = materials + labor + variable_overhead
        total_investment = launch_cost + working_capital + capital_equipment + building
        total_cost = materials + labor + depreciation + variable_overhead + gsa + rnd
        return {
            "Materials": materials,
            "Direct labor": labor,
            "Depreciation": depreciation,
            "Variable overhead": variable_overhead,
            "General, sales, administration": gsa,
            "Research and development": rnd,
            "Total variable": total_variable,
            "Total investment": total_investment,
            "Building": building,
            "Total cost": total_cost,
        }

    pack_costs = build(pack_labor, pack_building)
    module_costs = build(module_labor, module_building)
    rows = []
    for item in [
        "Materials",
        "Direct labor",
        "Depreciation",
        "Variable overhead",
        "General, sales, administration",
        "Research and development",
        "Total variable",
        "Total investment",
        "Building",
        "Total cost",
    ]:
        rows.append({CommonColumns.ITEM: item, "pack_disassembly": pack_costs[item], "module_disassembly": module_costs[item]})
    return pd.DataFrame(rows)


def disassembly_revenue_summary(scenario: Scenario) -> pd.DataFrame:
    weights = disassembly_weight_summary(scenario)
    pack_weight = weights["pack_weight_kg"]
    cell_weight = weights["cell_weight_kg"]
    materials = disassembly_material_recovery(scenario)
    pack_per_pack = float(materials["pack_revenue_per_pack"].sum())
    module_per_pack = float(materials["module_revenue_per_pack"].sum())
    if pack_weight <= 0 or cell_weight <= 0:
        pack_per_kg = module_per_kg = pack_per_kg_cell = module_per_kg_cell = 0.0
    else:
        pack_per_kg = pack_per_pack / pack_weight
        module_per_kg = module_per_pack / pack_weight
        pack_per_kg_cell = pack_per_kg * pack_weight / cell_weight
        module_per_kg_cell = module_per_kg * pack_weight / cell_weight
    return pd.DataFrame(
        [
            {"basis": "$/kg battery pack", "pack_disassembly": pack_per_kg, "module_disassembly": module_per_kg},
            {"basis": "$/kg battery cell", "pack_disassembly": pack_per_kg_cell, "module_disassembly": module_per_kg_cell},
        ]
    )
