from __future__ import annotations

import pandas as pd

from .cm_recovery import (
    cm_recovery_product_outputs,
    cm_recovery_product_prices,
    cm_recovery_throughput,
)
from .model import Scenario
from .parameters import workbook_sheet
from .schemas import AuditColumns, CommonColumns, StageSummaryColumns
from .transport import _num

# Stoichiometry constants from ``Mat. Conv Par.`` rows 41-47.
MOLAR_MASSES = {
    "2Li+": 14.0,
    "CaO": 56.08,
    "2LiOH": 48.0,
    "Li2CO3": 74.0,
    "Co2+": 58.9,
    "H2SO4": 98.0,
    "CoSO4": 154.9,
    "2HCl": 72.9,
    "1/3Co3O4": 80.23333333333333,
    "Ni2+": 58.7,
    "NiSO4": 154.7,
    "Mn": 54.94,
    "Mn2+": 54.9,
    "MnSO4": 150.9,
}

CONVERSION_INTENSITIES = {
    "Lithium Hydroxide": {
        "Lime": 1.1666666666666667,
        "Water": 7.382688374129172,
        "Natural gas": 11.275483091573868,
    },
    "Cobalt Sulfate": {
        "Sulfuric Acid": 0.6326662362814719,
        "Water": 0.2,
    },
    "Cobalt Oxide": {
        "Sodium Hydroxide": 0.4699074316327166,
        "Ammonium Bicarbonate": 1.3583261695633215,
        "Water": 2.66006719577489,
        "Electricity": 0.09525980158730159,
        "Natural gas": 15.781373796296295,
    },
    "Nickel Sulfate": {
        "Sulfuric Acid": 0.6334841628959277,
        "Water": 0.2,
    }
}

PROCESS_COLUMNS = {
    "Pyro": 3,
    "Hydro": 4,
    "Direct": 5,
    "Custom": 6,
}

PROCESSES = ("Pyro", "Hydro", "Direct", "Custom")
MJ_PER_MMBTU = 1055.06

ENERGY_METRICS = {
    "Total Energy",
    "Fossil fuels",
    "Coal",
    "Natural gas",
    "Petroleum",
}

OUTPUT_METRIC_BY_MAT_CONV_METRIC = {
    "Water consumption (gal/kg)": "Water use in gallon",
}

TRANSPORT_METRIC_BY_MAT_CONV_METRIC = {
    "Water consumption (gal/kg)": "Water consumption",
}

NON_CATHODE_ALLOCATION_PRODUCTS = {
    "Graphite",
    "Electrolyte organics",
    "Copper metal",
}

NON_CATHODE_REVENUE_PRODUCTS = {
    "Copper",
    "Aluminum",
    "Graphite",
    "Plastics",
    "Steel",
    "Electrolyte: solvents",
    "Copper metal",
}

CONVERSION_COST_CELLS = {
    "Cobalt Oxide": ("AB49", "AB50", "AB51"),
    "Cobalt Sulfate": ("AC49", "AC50", "AB51"), # Corrected from AC51 which was likely a typo in original if referencing same block
    "Nickel Sulfate": ("BB47", "BB48", "BB49"),
    "Lithium Hydroxide": ("CB47", "CB48", "CB49"),
}

CONVERSION_ENV_BLOCKS = {
    "Cobalt Oxide": (27, 28, 26, 45),
    "Cobalt Sulfate": (27, 29, 26, 45),
    "Nickel Sulfate": (53, 54, 24, 43),
    "Lithium Hydroxide": (79, 80, 24, 43),
}


def _mat_conv_ws():
    return workbook_sheet("Mat. Conv Par.")


def mat_conv_available_precursors(scenario: Scenario, process: str) -> pd.DataFrame:
    """Return available precursor from recycling, in kg precursor per kg feedstock."""
    cm_products = cm_recovery_product_outputs(scenario, process).set_index("product")["kg_per_kg_black_mass"].to_dict()
    
    co2 = cm_products.get("Co2+ in product", 0.0)
    ni2 = cm_products.get("Ni2+ in product", 0.0)
    mn2 = cm_products.get("Mn2+ in product", 0.0)
    li2co3 = cm_products.get("Lithium carbonate (crude)", 0.0)
    
    precursors = {
        "Cobalt Oxide": co2 / MOLAR_MASSES["Co2+"] * MOLAR_MASSES["1/3Co3O4"],
        "Cobalt Sulfate": co2 / MOLAR_MASSES["Co2+"] * MOLAR_MASSES["CoSO4"],
        "Nickel Sulfate": ni2 / MOLAR_MASSES["Ni2+"] * MOLAR_MASSES["NiSO4"],
        "Lithium Carbonate": li2co3,
        "Lithium Hydroxide": li2co3 / MOLAR_MASSES["Li2CO3"] * MOLAR_MASSES["2LiOH"],
        "Manganese Sulfate": mn2 / MOLAR_MASSES["Mn2+"] * MOLAR_MASSES["MnSO4"],
        "Aluminum Sulfate": 0.0,
    }
    
    records = [{CommonColumns.MATERIAL: k, "kg_per_kg_feedstock": v} for k, v in precursors.items()]
    return pd.DataFrame(records)


def mat_conv_recovered_materials(scenario: Scenario) -> pd.DataFrame:
    ws = _mat_conv_ws()
    processes = ("Pyro", "Hydro", "Direct", "Custom")
    records = []
    product_maps = {
        process: cm_recovery_product_outputs(scenario, process).set_index("product")["kg_per_kg_black_mass"].to_dict()
        if process != "Custom"
        else {}
        for process in processes
    }
    for row in range(10, 29):
        material = ws.cell(row, 2).value
        if material is None:
            continue
        record = {CommonColumns.MATERIAL: str(material)}
        for process in processes:
            record[process] = product_maps[process].get(str(material), _num(ws.cell(row, PROCESS_COLUMNS[process]).value))
        records.append(record)
    return pd.DataFrame(records)


def mat_conv_workbook_available_precursors() -> pd.DataFrame:
    ws = _mat_conv_ws()
    records = []
    for row in range(31, 38):
        precursor = ws.cell(row, 2).value
        if precursor is None:
            continue
        records.append(
            {
                CommonColumns.MATERIAL: str(precursor),
                "Pyro": _num(ws.cell(row, 3).value),
                "Hydro": _num(ws.cell(row, 4).value),
                "Custom": _num(ws.cell(row, 5).value),
            }
        )
    return pd.DataFrame(records)


def mat_conv_recycling_economics() -> pd.DataFrame:
    ws = _mat_conv_ws()
    rows = [
        ("total_recycling_cost", 58),
        ("revenue_all_recycled_materials", 61),
        ("cost_recycled_materials_to_convert", 64),
    ]
    records = []
    for item, row in rows:
        record = {CommonColumns.ITEM: item}
        for process, col in PROCESS_COLUMNS.items():
            record[process] = _num(ws.cell(row, col).value)
        records.append(record)
    return pd.DataFrame(records)


def mat_conv_recycling_economics_calculated(scenario: Scenario) -> pd.DataFrame:
    from .reporting import python_ported_process_stage_output_summary

    workbook = mat_conv_recycling_economics().set_index(CommonColumns.ITEM)
    prices = cm_recovery_product_prices()
    output = python_ported_process_stage_output_summary(scenario, include_workbook=False).set_index(
        [StageSummaryColumns.STAGE, CommonColumns.METRIC, "column"]
    )
    front_end_cost = output.loc[("Collection & Transport", "Cost per kgfeedstock", "total"), AuditColumns.PYTHON_VALUE]
    front_end_cost += output.loc[("Disassembly", "Cost per kg feedstock", "pack_to_module"), AuditColumns.PYTHON_VALUE]
    front_end_cost += output.loc[("Disassembly", "Cost per kg feedstock", "module_to_cell"), AuditColumns.PYTHON_VALUE]
    front_end_revenue = output.loc[("Disassembly", "Revenue per kg feedstock", "pack_to_module"), AuditColumns.PYTHON_VALUE]
    front_end_revenue += output.loc[("Disassembly", "Revenue per kg feedstock", "module_to_cell"), AuditColumns.PYTHON_VALUE]
    total_feedstock = sum(feedstock.tonnes_per_year for feedstock in scenario.feedstocks)

    records = {
        "total_recycling_cost": {CommonColumns.ITEM: "total_recycling_cost"},
        "revenue_all_recycled_materials": {CommonColumns.ITEM: "revenue_all_recycled_materials"},
        "cost_recycled_materials_to_convert": {CommonColumns.ITEM: "cost_recycled_materials_to_convert"},
    }
    for process in PROCESSES:
        cm_throughput = cm_recovery_throughput(scenario)
        if total_feedstock > 0:
            weighted_recycle_cost = output.loc[("Recycle", "Cost per kg feedstock processed", process), AuditColumns.PYTHON_VALUE]
            weighted_revenue = (
                front_end_revenue
                + output.loc[("Recycle", "Revenue per kg feedstock processed", process), AuditColumns.PYTHON_VALUE]
            )
            non_cathode_revenue = _non_cathode_revenue_per_kg_feed(scenario, process, prices) * cm_throughput / total_feedstock
        else:
            weighted_recycle_cost = weighted_revenue = non_cathode_revenue = 0.0

        values = {
            "total_recycling_cost": front_end_cost + weighted_recycle_cost,
            "revenue_all_recycled_materials": weighted_revenue,
            "cost_recycled_materials_to_convert": front_end_cost + weighted_recycle_cost - non_cathode_revenue,
        }
        for item, value in values.items():
            records[item][AuditColumns.calculated(process)] = value
            records[item][AuditColumns.workbook(process)] = workbook.loc[item, process]
            records[item][f"{process.lower()}_delta"] = value - workbook.loc[item, process]
    return pd.DataFrame(records.values())


def _non_cathode_revenue_per_kg_feed(scenario: Scenario, process: str, prices: dict[str, float]) -> float:
    products = cm_recovery_product_outputs(scenario, process)
    if products.empty:
        return 0.0
    return float(
        sum(
            row["kg_per_kg_black_mass"] * _price_for_product(prices, str(row["product"]))
            for row in products.to_dict("records")
            if str(row["product"]) in NON_CATHODE_REVENUE_PRODUCTS
        )
    )


def mat_conv_allocation_factors() -> pd.DataFrame:
    ws = _mat_conv_ws()
    records = []
    for row in range(71, 86):
        material = ws.cell(row, 2).value
        if material is None:
            continue
        records.append(
            {
                CommonColumns.MATERIAL: str(material),
                "mass_pyro": _num(ws.cell(row, 3).value),
                "mass_hydro": _num(ws.cell(row, 4).value),
                "mass_direct": _num(ws.cell(row, 5).value),
                "mass_custom": _num(ws.cell(row, 6).value),
                "economic_pyro": _num(ws.cell(row, 7).value),
                "economic_hydro": _num(ws.cell(row, 8).value),
                "economic_direct": _num(ws.cell(row, 9).value),
                "economic_custom": _num(ws.cell(row, 10).value),
            }
        )
    return pd.DataFrame(records)


def mat_conv_allocation_factors_calculated(scenario: Scenario) -> pd.DataFrame:
    """Return scenario-derived mass/economic allocation factors by recovered product."""
    workbook = mat_conv_allocation_factors().set_index(CommonColumns.MATERIAL)
    prices = cm_recovery_product_prices()
    processes = ("Pyro", "Hydro", "Direct", "Custom")
    materials = list(workbook.index)
    product_maps = {
        process: cm_recovery_product_outputs(scenario, process).set_index("product")["kg_per_kg_black_mass"].to_dict()
        for process in processes
    }
    total_mass = {process: sum(product_maps[process].values()) for process in processes}
    total_value = {
        process: sum(quantity * _price_for_product(prices, product) for product, quantity in product_maps[process].items())
        for process in processes
    }

    records = []
    for material in materials:
        record = {CommonColumns.MATERIAL: material}
        for process in processes:
            quantity = product_maps[process].get(material, 0.0)
            mass = quantity / total_mass[process] if total_mass[process] else 0.0
            economic = (
                quantity * _price_for_product(prices, material) / total_value[process]
                if total_value[process]
                else 0.0
            )
            process_key = process.lower()
            record[AuditColumns.calculated(f"mass_{process_key}")] = mass
            record[AuditColumns.workbook(f"mass_{process_key}")] = workbook.loc[material, f"mass_{process_key}"]
            record[f"mass_{process_key}_delta"] = mass - workbook.loc[material, f"mass_{process_key}"]
            record[AuditColumns.calculated(f"economic_{process_key}")] = economic
            record[AuditColumns.workbook(f"economic_{process_key}")] = workbook.loc[material, f"economic_{process_key}"]
            record[f"economic_{process_key}_delta"] = economic - workbook.loc[material, f"economic_{process_key}"]
        records.append(record)
    return pd.DataFrame(records)


def _price_for_product(prices: dict[str, float], product: str) -> float:
    return prices.get(product, prices.get(product.casefold(), 0.0))


def mat_conv_recycling_environment_summary(cathode_materials_only: bool = False) -> pd.DataFrame:
    ws = _mat_conv_ws()
    first_row, last_row = (114, 133) if cathode_materials_only else (91, 110)
    records = []
    for row in range(first_row, last_row + 1):
        metric = ws.cell(row, 2).value
        if metric is None or str(metric).startswith("Energy Use") or str(metric).startswith("Total Emissions"):
            continue
        records.append(
            {
                CommonColumns.METRIC: str(metric).strip(),
                "Pyro": _num(ws.cell(row, 3).value),
                "Hydro": _num(ws.cell(row, 4).value),
                "Direct": _num(ws.cell(row, 5).value),
                "Custom": _num(ws.cell(row, 6).value),
            }
        )
    return pd.DataFrame(records)


def mat_conv_recycling_environment_summary_calculated(
    scenario: Scenario,
    cathode_materials_only: bool = False,
) -> pd.DataFrame:
    """Return scenario-derived recycling environment values with workbook deltas.

    The workbook combines the Output recycle-stage environmental rows with
    collection transport impacts. Output stores recycle-stage energy in MJ/kg,
    while ``Mat. Conv Par.`` reports energy rows in mmBtu/kg.
    """
    from .reporting import python_ported_process_stage_output_summary
    from .transport import scenario_transport_segments, transport_environment_breakdown

    workbook = mat_conv_recycling_environment_summary(cathode_materials_only).set_index(CommonColumns.METRIC)
    output = python_ported_process_stage_output_summary(scenario, include_workbook=False).set_index(
        [StageSummaryColumns.STAGE, CommonColumns.METRIC, "column"]
    )
    transport = transport_environment_breakdown(
        segments=scenario_transport_segments(scenario)
    ).set_index(CommonColumns.METRIC)
    allocation_factors = _calculated_cathode_mass_allocation_factors(scenario) if cathode_materials_only else {}

    records = []
    for metric in workbook.index:
        record = {CommonColumns.METRIC: metric}
        output_metric = OUTPUT_METRIC_BY_MAT_CONV_METRIC.get(metric, metric)
        transport_metric = TRANSPORT_METRIC_BY_MAT_CONV_METRIC.get(metric, metric)
        for process in PROCESSES:
            recycle_value = output.loc[("Recycle", output_metric, process), AuditColumns.PYTHON_VALUE]
            if metric in ENERGY_METRICS:
                recycle_value = recycle_value / MJ_PER_MMBTU
            transport_value = transport.loc[transport_metric, "calculated_total"]
            calculated = recycle_value + transport_value
            if cathode_materials_only:
                calculated *= allocation_factors.get(process, 0.0)
            workbook_value = workbook.loc[metric, process]
            record[AuditColumns.calculated(process)] = calculated
            record[AuditColumns.workbook(process)] = workbook_value
            record[f"{process.lower()}_delta"] = calculated - workbook_value
        records.append(record)
    return pd.DataFrame(records)


def _calculated_cathode_mass_allocation_factors(scenario: Scenario) -> dict[str, float]:
    allocation = mat_conv_allocation_factors_calculated(scenario).set_index(CommonColumns.MATERIAL)
    factors = {}
    for process in PROCESSES:
        process_key = process.lower()
        column = AuditColumns.calculated(f"mass_{process_key}")
        factors[process] = float(
            allocation.loc[
                [material for material in allocation.index if material not in NON_CATHODE_ALLOCATION_PRODUCTS],
                column,
            ].sum()
        )
    return factors

def mat_conv_conversion_costs(scenario: Scenario) -> pd.DataFrame:
    """Return conversion material, utility, and total cost by precursor."""
    ws = _mat_conv_ws()
    records = []
    for precursor, (material_cell, utility_cell, total_cell) in CONVERSION_COST_CELLS.items():
        records.append(
            {
                CommonColumns.MATERIAL: precursor,
                "material_cost_per_kg": _num(ws[material_cell].value),
                "utility_cost_per_kg": _num(ws[utility_cell].value),
                "cost_per_kg": _num(ws[total_cell].value),
            }
        )
    return pd.DataFrame(records)


def mat_conv_conversion_environment() -> pd.DataFrame:
    ws = _mat_conv_ws()
    records = []
    for precursor, (label_col, value_col, first_row, last_row) in CONVERSION_ENV_BLOCKS.items():
        for row in range(first_row, last_row + 1):
            metric = ws.cell(row, label_col).value
            if metric is None or str(metric).startswith("Energy Use") or str(metric).startswith("Total Emissions"):
                continue
            records.append(
                {
                    CommonColumns.MATERIAL: precursor,
                    CommonColumns.METRIC: str(metric).strip(),
                    CommonColumns.VALUE: _num(ws.cell(row, value_col).value),
                }
            )
    return pd.DataFrame(records)


def mat_conv_total_summary() -> pd.DataFrame:
    ws = _mat_conv_ws()
    records = []
    for row in range(301, 323):
        metric = ws.cell(row, 2).value
        if metric is None or str(metric).startswith("Energy Use") or str(metric).startswith("Total Emissions"):
            continue
        records.append({CommonColumns.METRIC: str(metric).strip(), CommonColumns.VALUE: _num(ws.cell(row, 3).value)})
    return pd.DataFrame(records)


def mat_conv_total_summary_calculated(scenario: Scenario) -> pd.DataFrame:
    """Calculate the total summary across all material conversion blocks."""
    costs = mat_conv_conversion_costs(scenario)
    env = mat_conv_conversion_environment()
    workbook = mat_conv_total_summary().set_index(CommonColumns.METRIC)
    
    records = []
    
    total_cost = costs["cost_per_kg"].sum()
    wb_cost = workbook.loc["Total cost of material conversion ($/kg)", CommonColumns.VALUE]
    records.append({
        CommonColumns.METRIC: "Total cost of material conversion ($/kg)",
        AuditColumns.calculated(CommonColumns.VALUE): total_cost,
        AuditColumns.workbook(CommonColumns.VALUE): wb_cost,
        CommonColumns.VALUE + "_delta": total_cost - wb_cost
    })
    
    env_sum = env.groupby(CommonColumns.METRIC)[CommonColumns.VALUE].sum()
    for metric in workbook.index:
        if metric == "Total cost of material conversion ($/kg)":
            continue
        calc_val = env_sum.get(metric, 0.0)
        wb_val = workbook.loc[metric, CommonColumns.VALUE]
        records.append({
            CommonColumns.METRIC: metric,
            AuditColumns.calculated(CommonColumns.VALUE): calc_val,
            AuditColumns.workbook(CommonColumns.VALUE): wb_val,
            CommonColumns.VALUE + "_delta": calc_val - wb_val
        })
        
    return pd.DataFrame(records)
