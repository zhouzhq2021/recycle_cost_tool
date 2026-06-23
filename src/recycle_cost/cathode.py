from __future__ import annotations

import math

import pandas as pd

from .mat_conv import mat_conv_available_precursors
from .model import Scenario
from .custom_chemistry import workbook_chemistry
from .parameters import (
    CATHODE_CHEMISTRY_COLUMNS,
    CATHODE_COST_PER_LINE_COLUMNS,
    CATHODE_DETAILED_COST_ROWS,
    CATHODE_ENVIRONMENT_COLUMNS,
    CATHODE_PRICE_COLUMNS,
    CATHODE_PROCESS_COLUMNS,
    CATHODE_PRODUCTION_BLOCKS,
    CATHODE_PRODUCTION_SHEET,
    CATHODE_REQUIRED_PRECURSOR_COLUMNS,
    CATHODE_SPLIT_OFFSETS,
    get_cathode_chemical_prices_data,
    get_cathode_direct_regeneration_data,
    get_cathode_general_default,
    get_cathode_material_conversion_costs_data,
    get_cathode_material_energy_demand_data,
    get_cathode_precursor_rows,
    get_cathode_tonnes_per_gwh_factors,
    get_cathode_utility_prices_data,
    load_everbatt_workbook,
    workbook_sheet,
)
from .schemas import AuditColumns, CathodeColumns, CommonColumns
from .transport import _num


CHEMISTRY_COLUMNS = CATHODE_CHEMISTRY_COLUMNS
PRODUCTION_BLOCKS = CATHODE_PRODUCTION_BLOCKS
CATHODE_PRODUCTION_CHEMISTRIES = tuple(PRODUCTION_BLOCKS)

PROCESSES = ("Pyro", "Hydro", "Direct", "Custom")

PROCESS_COLUMNS = CATHODE_PROCESS_COLUMNS

SCENARIO_PROCESS_COLUMNS = {
    "Pyro": "Pyro",
    "Hydro": "Hydro",
    "Direct": "Custom",
    "Custom": "Custom",
}

PRICE_COLUMNS = CATHODE_PRICE_COLUMNS

REQUIRED_PRECURSOR_COLUMNS = CATHODE_REQUIRED_PRECURSOR_COLUMNS

SPLIT_OFFSETS = CATHODE_SPLIT_OFFSETS

ENVIRONMENT_COLUMNS = CATHODE_ENVIRONMENT_COLUMNS

COST_PER_LINE_COLUMNS = CATHODE_COST_PER_LINE_COLUMNS

DETAILED_COST_ROWS = CATHODE_DETAILED_COST_ROWS


def _cathode_ws():
    return workbook_sheet(CATHODE_PRODUCTION_SHEET)


def _clean_label(value) -> str:
    return str(value).strip()


def _valid_label(value) -> bool:
    if value is None:
        return False
    label = _clean_label(value)
    return bool(label) and label != "0"


def _chemistries(chemistry: str | None) -> tuple[str, ...]:
    chemistry = workbook_chemistry(chemistry)
    if chemistry is None:
        return tuple(PRODUCTION_BLOCKS)
    if chemistry not in PRODUCTION_BLOCKS:
        raise ValueError(f"Unsupported cathode production chemistry: {chemistry}")
    return (chemistry,)


def cathode_chemistry_for_scenario(scenario: Scenario) -> str:
    if scenario.cathode_chemistry:
        mapped = workbook_chemistry(scenario.cathode_chemistry)
        if mapped in PRODUCTION_BLOCKS:
            return mapped
    if scenario.cathode_chemistry in PRODUCTION_BLOCKS:
        return scenario.cathode_chemistry
    mapped_manufacturing = workbook_chemistry(scenario.manufacturing_chemistry)
    if mapped_manufacturing in PRODUCTION_BLOCKS:
        return mapped_manufacturing
    return "NMC(622)"


def cathode_throughput_tonnes_per_year(scenario: Scenario) -> float:
    if scenario.cathode_throughput_gwh_per_year and scenario.cathode_throughput_gwh_per_year > 0:
        return scenario.cathode_throughput_gwh_per_year * _default_cathode_tonnes_per_gwh()
    return 0.0


def _default_cathode_tonnes_per_gwh() -> float:
    factors = get_cathode_tonnes_per_gwh_factors()
    mass_per_kwh = factors.get("mass_per_kwh", 0.0)
    active_share = factors.get("active_share", 0.0)
    kg_per_gwh = 1_000_000.0
    return mass_per_kwh * active_share * kg_per_gwh / 1000.0


def _feedstock_tonnes(scenario: Scenario) -> float:
    return sum(feedstock.tonnes_per_year for feedstock in scenario.feedstocks)


def cathode_general_inputs() -> pd.DataFrame:
    defaults = get_cathode_general_default()
    return pd.DataFrame(
        [
            {CommonColumns.ITEM: "throughput", CommonColumns.UNIT: "tonne/yr", CommonColumns.VALUE: defaults["throughput"]},
            {CommonColumns.ITEM: "cathode_chemistry", CommonColumns.UNIT: "", CommonColumns.VALUE: defaults["cathode_chemistry"]},
            {CommonColumns.ITEM: "geographic_location", CommonColumns.UNIT: "", CommonColumns.VALUE: defaults["geographic_location"]},
        ]
    )


def cathode_available_precursors() -> pd.DataFrame:
    records = []
    for precursor, data in get_cathode_precursor_rows():
        if not _valid_label(precursor):
            continue
        record = {CommonColumns.MATERIAL: _clean_label(precursor)}
        for process in PROCESS_COLUMNS:
            col_index = PROCESS_COLUMNS.get(process)
            record[process] = _num(data.get(col_index, 0.0))
        records.append(record)
    return pd.DataFrame(records)


def cathode_available_precursors_for_scenario(scenario: Scenario) -> pd.DataFrame:
    feedstock_tonnes = _feedstock_tonnes(scenario)
    records = {}
    for process in PROCESSES:
        if process in {"Pyro", "Hydro", "Direct"}:
            available = mat_conv_available_precursors(scenario, process)
            records[process] = available.set_index(CommonColumns.MATERIAL)["kg_per_kg_feedstock"].mul(feedstock_tonnes)
        else:
            records[process] = pd.Series(dtype=float)

    precursors = sorted(set().union(*(series.index for series in records.values())))
    rows = []
    for precursor in precursors:
        row = {CommonColumns.MATERIAL: precursor}
        for process in PROCESSES:
            row[process] = float(records[process].get(precursor, 0.0))
        rows.append(row)
    return pd.DataFrame(rows)


def cathode_material_energy_demand() -> pd.DataFrame:
    data = get_cathode_material_energy_demand_data()
    records = []
    for row_data in data:
        item = row_data[CommonColumns.ITEM]
        row = row_data["row"]
        if not _valid_label(item) or str(item).endswith("(kg)") or str(item).endswith("(MJ)") or str(item).endswith("(g)"):
            continue
        if row <= 42:
            category = "material_input_kg_per_kg_cathode"
        elif row == 43:
            category = "process_water_gal_per_kg_cathode"
        elif row <= 46:
            category = "energy_input_mj_per_kg_cathode"
        else:
            category = "process_emission_g_per_kg_cathode"
        record = {CommonColumns.CATEGORY: category, CommonColumns.ITEM: _clean_label(item)}
        for chemistry in CHEMISTRY_COLUMNS:
            record[chemistry] = row_data[chemistry]
        records.append(record)
    return pd.DataFrame(records)


def cathode_chemical_prices() -> pd.DataFrame:
    data = get_cathode_chemical_prices_data()
    records = []
    for row_data in data:
        chemical = row_data["chemical"]
        if not _valid_label(chemical):
            continue
        record = {"chemical": _clean_label(chemical)}
        for label in PRICE_COLUMNS:
            record[label] = row_data[label]
        records.append(record)
    return pd.DataFrame(records)


def cathode_utility_prices() -> pd.DataFrame:
    data = get_cathode_utility_prices_data()
    records = []
    for row_data in data:
        utility = row_data["utility"]
        if not _valid_label(utility):
            continue
        record = {"utility": _clean_label(utility)}
        for label in PRICE_COLUMNS:
            record[label] = row_data[label]
        records.append(record)
    return pd.DataFrame(records)


def cathode_material_conversion_costs() -> pd.DataFrame:
    data = get_cathode_material_conversion_costs_data()
    records = []
    for row_data in data:
        precursor = row_data[CommonColumns.MATERIAL]
        if not _valid_label(precursor):
            continue
        records.append(
            {
                CommonColumns.MATERIAL: _clean_label(precursor),
                "cost_per_kg_precursor": row_data["cost_per_kg_precursor"],
            }
        )
    return pd.DataFrame(records)


def cathode_required_precursors(chemistry: str | None = None) -> pd.DataFrame:
    ws = _cathode_ws()
    records = []
    for chem in _chemistries(chemistry):
        start_col = PRODUCTION_BLOCKS[chem]
        for row in range(9, 16):
            precursor = ws.cell(row, start_col).value
            if not _valid_label(precursor):
                continue
            record = {CommonColumns.CHEMISTRY: chem, CommonColumns.MATERIAL: _clean_label(precursor)}
            for label, offset in REQUIRED_PRECURSOR_COLUMNS.items():
                record[label] = _num(ws.cell(row, start_col + offset).value)
            records.append(record)
    return pd.DataFrame(records)


def cathode_recycled_virgin_split(chemistry: str | None = None) -> pd.DataFrame:
    ws = _cathode_ws()
    records = []
    for chem in _chemistries(chemistry):
        start_col = PRODUCTION_BLOCKS[chem]
        for row in range(21, 28):
            material = ws.cell(row, start_col).value
            if not _valid_label(material):
                continue
            record = {CommonColumns.CHEMISTRY: chem, CommonColumns.MATERIAL: _clean_label(material)}
            for process, offsets in SPLIT_OFFSETS.items():
                record[f"{process.lower()}_recycled"] = _num(ws.cell(row, start_col + offsets[0]).value)
                record[f"{process.lower()}_virgin"] = _num(ws.cell(row, start_col + offsets[1]).value)
                record[f"{process.lower()}_surplus"] = _num(ws.cell(row, start_col + offsets[2]).value)
            records.append(record)
    return pd.DataFrame(records)


def cathode_recycled_virgin_split_calculated(chemistry: str | None = None) -> pd.DataFrame:
    ws = _cathode_ws()
    workbook = cathode_recycled_virgin_split(chemistry).set_index([CommonColumns.CHEMISTRY, CommonColumns.MATERIAL])
    records = []
    throughput = _num(ws["D8"].value)
    source_rows = {
        "Pyro": {21: ("C", 15), 22: ("C", 16), 23: ("C", 17)},
        "Hydro": {21: ("D", 15), 22: ("D", 16), 23: ("D", 17), 24: ("D", 19)},
        "Custom": {21: ("E", 15), 22: ("E", 16), 23: ("E", 17)},
    }

    for chem in _chemistries(chemistry):
        start_col = PRODUCTION_BLOCKS[chem]
        for row in range(21, 28):
            material = ws.cell(row, start_col).value
            if not _valid_label(material):
                continue
            material_label = _clean_label(material)
            required = _num(ws.cell(row - 12, start_col + 1).value)
            record: dict[str, float | str] = {CommonColumns.CHEMISTRY: chem, CommonColumns.MATERIAL: material_label}
            for process in ("Pyro", "Hydro", "Custom"):
                source = source_rows[process].get(row)
                invalid_recycled_formula = False
                if source is None:
                    recycled = 0.0
                elif throughput == 0:
                    recycled = 0.0
                    invalid_recycled_formula = True
                else:
                    recycled = _num(ws[f"{source[0]}{source[1]}"].value) / throughput

                if invalid_recycled_formula:
                    virgin = 0.0
                    surplus = 0.0
                else:
                    virgin = 0.0 if recycled > required else required - recycled
                    surplus = recycled - required if recycled > required else 0.0

                for field, calculated in (
                    ("recycled", recycled),
                    ("virgin", virgin),
                    ("surplus", surplus),
                ):
                    prefix = f"{process.lower()}_{field}"
                    workbook_value = workbook.loc[(chem, material_label), prefix]
                    record[AuditColumns.calculated(prefix)] = calculated
                    record[AuditColumns.workbook(prefix)] = workbook_value
                    record[f"{prefix}_delta"] = calculated - workbook_value
            records.append(record)
    return pd.DataFrame(records)


def cathode_recycled_virgin_split_for_scenario(
    scenario: Scenario,
    chemistry: str | None = None,
) -> pd.DataFrame:
    chemistry = chemistry or cathode_chemistry_for_scenario(scenario)
    throughput = cathode_throughput_tonnes_per_year(scenario)
    required = cathode_required_precursors(chemistry).set_index(CommonColumns.MATERIAL)["selected"]
    available = cathode_available_precursors_for_scenario(scenario).set_index(CommonColumns.MATERIAL)

    records = []
    for precursor, required_kg_per_kg in required.items():
        record = {
            CommonColumns.CHEMISTRY: chemistry,
            CommonColumns.MATERIAL: precursor,
            "required_kg_per_kg_cathode": required_kg_per_kg,
        }
        for process, available_col in SCENARIO_PROCESS_COLUMNS.items():
            available_tpy = available.loc[precursor, process] if precursor in available.index else 0.0
            recycled = available_tpy / throughput if throughput > 0 else 0.0
            virgin = max(required_kg_per_kg - recycled, 0.0)
            surplus = max(recycled - required_kg_per_kg, 0.0)
            record[f"{process.lower()}_available_tonnes_per_year"] = available_tpy
            record[f"{process.lower()}_recycled"] = recycled
            record[f"{process.lower()}_virgin"] = virgin
            record[f"{process.lower()}_surplus"] = surplus
        records.append(record)
    return pd.DataFrame(records)


def cathode_environment_summary(chemistry: str | None = None) -> pd.DataFrame:
    ws = _cathode_ws()
    records = []
    for chem in _chemistries(chemistry):
        start_col = PRODUCTION_BLOCKS[chem]
        for row in range(44, 64):
            metric = ws.cell(row, start_col).value
            if not _valid_label(metric) or str(metric).startswith("Total Emissions"):
                continue
            record = {CommonColumns.CHEMISTRY: chem, CommonColumns.METRIC: _clean_label(metric)}
            for label, offset in ENVIRONMENT_COLUMNS.items():
                record[label] = _num(ws.cell(row, start_col + offset).value)
            for process in ("pyro", "hydro", "custom"):
                total_key = f"total_{process}"
                if record.get(total_key, 0.0) == 0.0:
                    record[total_key] = (
                        record.get(f"material_{process}", 0.0)
                        + record.get("energy_input", 0.0)
                        + record.get("process", 0.0)
                    )
            records.append(record)
    return pd.DataFrame(records)


def cathode_virgin_environment_summary(chemistry: str | None = None) -> pd.DataFrame:
    environment = cathode_environment_summary(chemistry).copy()
    environment["virgin_total"] = environment["energy_input"] + environment["process"]
    return environment[[CommonColumns.CHEMISTRY, CommonColumns.METRIC, "energy_input", "process", "virgin_total"]]


def cathode_direct_regeneration_environment_summary(chemistry: str | None = None) -> pd.DataFrame:
    data = get_cathode_direct_regeneration_data()
    direct_quantities = data["direct_quantities"]
    recovered_prices = data["recovered_prices"]
    mat_conv = data["raw_data"]
    greet = load_everbatt_workbook(data_only=True)["GREET IO"]

    direct_value = sum(
        direct_quantities.get(material, 0.0) * recovered_prices.get(material, 0.0)
        for material in recovered_prices
    )
    greet_columns = {
        str(greet.cell(77, col).value): col
        for col in range(2, 53)
        if greet.cell(77, col).value is not None
    }

    records = []
    for chem in _chemistries(chemistry):
        direct_quantity = direct_quantities.get(chem, 0.0)
        recovered_price = recovered_prices.get(chem, 0.0)
        greet_col = greet_columns.get(chem)
        for row in range(114, 134):
            metric = mat_conv.cell(row, 2).value
            if not _valid_label(metric) or str(metric).startswith("Total Emissions"):
                continue
            if direct_quantity > 0 and direct_value > 0:
                value = _num(mat_conv.cell(row, 5).value) * recovered_price / direct_value
            elif greet_col is not None:
                value = _num(greet.cell(row - 35, greet_col).value) / 907.2
            else:
                value = 0.0
            records.append(
                {
                    CommonColumns.CHEMISTRY: chem,
                    CommonColumns.METRIC: _clean_label(metric),
                    "direct_regeneration": value,
                }
            )
    return pd.DataFrame(records)


def cathode_raw_material_cost_summary(
    scenario: Scenario,
    chemistry: str | None = None,
) -> pd.DataFrame:
    chemistry = chemistry or cathode_chemistry_for_scenario(scenario)
    prices = cathode_chemical_prices().set_index("chemical")["selected"]
    split = cathode_recycled_virgin_split_for_scenario(scenario, chemistry)
    conversion_costs = cathode_material_conversion_costs().set_index(CommonColumns.MATERIAL)["cost_per_kg_precursor"]

    records = []
    for process in PROCESSES:
        material_cost = 0.0
        conversion_cost = 0.0
        virgin_cost = 0.0
        for row in split.to_dict("records"):
            material = row[CommonColumns.MATERIAL]
            virgin_amount = row[f"{process.lower()}_virgin"]
            recycled_amount = row[f"{process.lower()}_recycled"]
            virgin_cost += virgin_amount * float(prices.get(material, 0.0))
            conversion_cost += recycled_amount * float(conversion_costs.get(material, 0.0))
            material_cost += virgin_amount * float(prices.get(material, 0.0))
        records.append(
            {
                CommonColumns.CHEMISTRY: chemistry,
                CommonColumns.PROCESS: process,
                "virgin_material_cost_per_kg": virgin_cost,
                "recycled_conversion_cost_per_kg": conversion_cost,
                "raw_material_cost_per_kg": material_cost + conversion_cost,
            }
        )
    virgin_recipe_cost = sum(
        row["required_kg_per_kg_cathode"] * float(prices.get(row[CommonColumns.MATERIAL], 0.0))
        for row in split.to_dict("records")
    )
    records.append(
        {
            CommonColumns.CHEMISTRY: chemistry,
            CommonColumns.PROCESS: "Virgin",
            "virgin_material_cost_per_kg": virgin_recipe_cost,
            "recycled_conversion_cost_per_kg": 0.0,
            "raw_material_cost_per_kg": virgin_recipe_cost,
        }
    )
    return pd.DataFrame(records)


def cathode_raw_material_cost_calculated(chemistry: str | None = None) -> pd.DataFrame:
    ws = _cathode_ws()
    input_ws = load_everbatt_workbook(data_only=True)["Input"]
    mat_conv_ws = load_everbatt_workbook(data_only=True)["Mat. Conv Par."]
    prices = cathode_chemical_prices().set_index("chemical")["selected"]
    conversion_costs = cathode_material_conversion_costs().set_index(CommonColumns.MATERIAL)["cost_per_kg_precursor"]
    split = cathode_recycled_virgin_split_calculated(chemistry)
    workbook = cathode_detailed_cost_summary(chemistry).set_index([CommonColumns.CHEMISTRY, CommonColumns.ITEM])
    records = []

    conversion_cost_cells = {"Pyro": "C64", "Hydro": "D64", "Custom": "F64"}
    feedstock_tonnes = sum(_num(input_ws.cell(row, 6).value) for row in range(28, 33))
    plant_count = 0.0
    throughput = _num(ws["D8"].value)
    if throughput > 0:
        plant_count = float(math.ceil(throughput / 2000.0))

    for chem in _chemistries(chemistry):
        start_col = PRODUCTION_BLOCKS[chem]
        product_kg_per_year = _num(ws.cell(111, start_col + 2).value)
        if product_kg_per_year == 0:
            product_kg_per_year = _num(ws.cell(110, start_col + 2).value) * _num(ws.cell(103, start_col + 2).value)

        chem_split = split[split[CommonColumns.CHEMISTRY] == chem].set_index(CommonColumns.MATERIAL)
        for process in ("Pyro", "Hydro", "Custom", "Virgin"):
            if product_kg_per_year == 0:
                annual = 0.0
            elif process == "Virgin":
                annual = sum(
                    _num(ws.cell(row, start_col + 1).value) * float(prices.get(str(ws.cell(row, start_col).value), 0.0))
                    for row in range(9, 16)
                    if _valid_label(ws.cell(row, start_col).value)
                ) * product_kg_per_year
            else:
                material_cost_per_kg = 0.0
                for material, row in chem_split.iterrows():
                    price = float(prices.get(material, 0.0))
                    material_cost_per_kg += row[AuditColumns.calculated(f"{process.lower()}_virgin")] * price
                for material in list(chem_split.index)[:3]:
                    conversion = float(conversion_costs.get(material, 0.0))
                    price = float(prices.get(material, 0.0))
                    material_cost_per_kg += chem_split.loc[material, AuditColumns.calculated(f"{process.lower()}_recycled")] * conversion
                    material_cost_per_kg -= chem_split.loc[material, AuditColumns.calculated(f"{process.lower()}_surplus")] * price

                material_conversion_allocation = 0.0
                if plant_count > 0:
                    material_conversion_allocation = (
                        _num(mat_conv_ws[conversion_cost_cells[process]].value) * feedstock_tonnes / plant_count * 1000.0
                    )
                annual = material_cost_per_kg * product_kg_per_year + material_conversion_allocation

            per_kg = annual / product_kg_per_year if product_kg_per_year else 0.0
            workbook_annual = workbook.loc[(chem, "Raw materials"), CathodeColumns.annual_col(process)]
            workbook_per_kg = workbook.loc[(chem, "Raw materials"), CathodeColumns.per_kg_col(process)]
            records.append(
                {
                    CommonColumns.CHEMISTRY: chem,
                    CommonColumns.PROCESS: process,
                    AuditColumns.calculated(CathodeColumns.ANNUAL): annual,
                    AuditColumns.workbook(CathodeColumns.ANNUAL): workbook_annual,
                    "annual_delta": annual - workbook_annual,
                    AuditColumns.calculated(CathodeColumns.PER_KG): per_kg,
                    AuditColumns.workbook(CathodeColumns.PER_KG): workbook_per_kg,
                    "per_kg_delta": per_kg - workbook_per_kg,
                }
            )
    return pd.DataFrame(records)


def cathode_utility_cost_calculated(chemistry: str | None = None) -> pd.DataFrame:
    ws = _cathode_ws()
    workbook = cathode_detailed_cost_summary(chemistry).set_index([CommonColumns.CHEMISTRY, CommonColumns.ITEM])
    records = []

    for chem in _chemistries(chemistry):
        start_col = PRODUCTION_BLOCKS[chem]
        value_col = start_col + 2
        natural_gas = _num(ws.cell(365, value_col).value) * 1_000_000.0 * _num(ws.cell(369, value_col).value)
        electricity = _num(ws.cell(372, value_col).value) * _num(ws.cell(373, value_col).value)
        process_water = _num(ws.cell(379, value_col).value) * _num(ws.cell(382, value_col).value)
        cooling_water = _num(ws.cell(384, value_col).value) * _num(ws.cell(385, value_col).value)
        total = natural_gas + electricity + process_water + cooling_water

        for process in ("Pyro", "Hydro", "Custom", "Virgin"):
            workbook_annual = workbook.loc[(chem, "Utilities"), CathodeColumns.annual_col(process)]
            records.append(
                {
                    CommonColumns.CHEMISTRY: chem,
                    CommonColumns.PROCESS: process,
                    "calculated_natural_gas": natural_gas,
                    "calculated_electricity": electricity,
                    "calculated_process_water": process_water,
                    "calculated_cooling_water": cooling_water,
                    AuditColumns.calculated(CathodeColumns.ANNUAL): total,
                    AuditColumns.workbook(CathodeColumns.ANNUAL): workbook_annual,
                    "annual_delta": total - workbook_annual,
                }
            )
    return pd.DataFrame(records)


def cathode_labor_cost_calculated(chemistry: str | None = None) -> pd.DataFrame:
    ws = _cathode_ws()
    workbook = cathode_detailed_cost_summary(chemistry).set_index([CommonColumns.CHEMISTRY, CommonColumns.ITEM])
    records = []

    for chem in _chemistries(chemistry):
        start_col = PRODUCTION_BLOCKS[chem]
        value_col = start_col + 2
        base_labor_per_day = _num(ws.cell(446, value_col).value) * 24.0 * _num(ws.cell(447, value_col).value)
        base_labor_per_year = base_labor_per_day * _num(ws.cell(103, value_col).value)
        product_required = _num(ws.cell(110, value_col).value)
        reference_capacity = _num(ws.cell(434, value_col).value)
        p_factor = _num(ws.cell(450, value_col).value)
        if product_required > 0 and reference_capacity > 0:
            operating_labor = base_labor_per_year * (product_required / reference_capacity) ** p_factor
        else:
            operating_labor = 0.0

        reset_with_zero = _num(ws.cell(531, value_col).value)
        for process, offset in COST_PER_LINE_COLUMNS.items():
            supervision_rate = _num(ws.cell(491, start_col + offset + 1).value)
            supervisory_labor = 0.0 if reset_with_zero == 0 else supervision_rate * operating_labor
            for item, calculated in (
                ("Operating labor", operating_labor),
                ("Direct supervisory and clerical labor", supervisory_labor),
            ):
                workbook_annual = workbook.loc[(chem, item), CathodeColumns.annual_col(process)]
                records.append(
                    {
                        CommonColumns.CHEMISTRY: chem,
                        CommonColumns.PROCESS: process,
                        CommonColumns.ITEM: item,
                        "base_labor_per_day": base_labor_per_day,
                        "base_labor_per_year": base_labor_per_year,
                        AuditColumns.calculated(CathodeColumns.ANNUAL): calculated,
                        AuditColumns.workbook(CathodeColumns.ANNUAL): workbook_annual,
                        "annual_delta": calculated - workbook_annual,
                    }
                )
    return pd.DataFrame(records)


def cathode_capital_cost_calculated(chemistry: str | None = None) -> pd.DataFrame:
    ws = _cathode_ws()
    workbook = cathode_cost_per_line_summary(chemistry).set_index([CommonColumns.CHEMISTRY, CommonColumns.ITEM])
    records = []

    for chem in _chemistries(chemistry):
        start_col = PRODUCTION_BLOCKS[chem]
        value_col = start_col + 2
        reset_with_zero = _num(ws.cell(531, value_col).value)
        purchased_equipment = _num(ws.cell(390, value_col).value) * (1.0 + _num(ws.cell(391, value_col).value)) * _num(
            workbook_sheet("Geographic Par.")["C42"].value
        )

        if reset_with_zero == 0:
            direct_costs = indirect_costs = fixed_capital = working_capital = total_capital = 0.0
        else:
            direct_multiplier = sum(_num(ws.cell(row, value_col).value) for row in (455, 457, 459, 461, 463, 465, 467, 469))
            direct_costs = direct_multiplier * purchased_equipment
            non_contingency_indirect = (_num(ws.cell(472, value_col).value) + _num(ws.cell(474, value_col).value)) * direct_costs
            contingency_rate = _num(ws.cell(476, value_col).value)
            fixed_capital = (
                (direct_costs + non_contingency_indirect) / (1.0 - contingency_rate)
                if contingency_rate < 1.0
                else 0.0
            )
            indirect_costs = fixed_capital - direct_costs
            working_capital_rate = _num(ws.cell(480, value_col).value)
            total_capital = fixed_capital / (1.0 - working_capital_rate) if working_capital_rate < 1.0 else 0.0
            working_capital = total_capital - fixed_capital

        values = {
            "Direct costs ($)": direct_costs,
            "Indirect costs ($)": indirect_costs,
            "Fixed capital investment ($)": fixed_capital,
            "Working capital ($)": working_capital,
            "Total capital investment ($)": total_capital,
        }
        for process in COST_PER_LINE_COLUMNS:
            for item, calculated in values.items():
                workbook_value = workbook.loc[(chem, item), process]
                records.append(
                    {
                        CommonColumns.CHEMISTRY: chem,
                        CommonColumns.PROCESS: process,
                        CommonColumns.ITEM: item,
                        "purchased_equipment": purchased_equipment,
                        AuditColumns.calculated(CommonColumns.VALUE): calculated,
                        AuditColumns.workbook(CommonColumns.VALUE): workbook_value,
                        "delta": calculated - workbook_value,
                    }
                )
    return pd.DataFrame(records)


def cathode_maintenance_cost_calculated(chemistry: str | None = None) -> pd.DataFrame:
    ws = _cathode_ws()
    workbook = cathode_detailed_cost_summary(chemistry).set_index([CommonColumns.CHEMISTRY, CommonColumns.ITEM])
    capital = cathode_capital_cost_calculated(chemistry)
    records = []

    for chem in _chemistries(chemistry):
        start_col = PRODUCTION_BLOCKS[chem]
        value_col = start_col + 2
        reset_with_zero = _num(ws.cell(531, value_col).value)
        fixed_capital = capital[
            (capital[CommonColumns.CHEMISTRY] == chem)
            & (capital[CommonColumns.PROCESS] == "Pyro")
            & (capital[CommonColumns.ITEM] == "Fixed capital investment ($)")
        ][AuditColumns.calculated(CommonColumns.VALUE)].iloc[0]

        for process, offset in COST_PER_LINE_COLUMNS.items():
            process_col = start_col + offset + 1
            if reset_with_zero == 0:
                maintenance = 0.0
            else:
                maintenance = _num(ws.cell(495, process_col).value) * fixed_capital
            operating_supplies = _num(ws.cell(497, process_col).value) * maintenance

            for item, calculated in (
                ("Maintenance and repairs", maintenance),
                ("Operating supplies", operating_supplies),
            ):
                workbook_annual = workbook.loc[(chem, item), CathodeColumns.annual_col(process)]
                records.append(
                    {
                        CommonColumns.CHEMISTRY: chem,
                        CommonColumns.PROCESS: process,
                        CommonColumns.ITEM: item,
                        "fixed_capital": fixed_capital,
                        AuditColumns.calculated(CathodeColumns.ANNUAL): calculated,
                        AuditColumns.workbook(CathodeColumns.ANNUAL): workbook_annual,
                        "annual_delta": calculated - workbook_annual,
                    }
                )
    return pd.DataFrame(records)


def cathode_total_cost_calculated(chemistry: str | None = None) -> pd.DataFrame:
    ws = _cathode_ws()
    workbook = cathode_detailed_cost_summary(chemistry).set_index([CommonColumns.CHEMISTRY, CommonColumns.ITEM])
    raw_materials = cathode_raw_material_cost_calculated(chemistry).set_index([CommonColumns.CHEMISTRY, CommonColumns.PROCESS])
    labor = cathode_labor_cost_calculated(chemistry).set_index([CommonColumns.CHEMISTRY, CommonColumns.PROCESS, CommonColumns.ITEM])
    utilities = cathode_utility_cost_calculated(chemistry).set_index([CommonColumns.CHEMISTRY, CommonColumns.PROCESS])
    maintenance = cathode_maintenance_cost_calculated(chemistry).set_index([CommonColumns.CHEMISTRY, CommonColumns.PROCESS, CommonColumns.ITEM])
    capital = cathode_capital_cost_calculated(chemistry).set_index([CommonColumns.CHEMISTRY, CommonColumns.PROCESS, CommonColumns.ITEM])
    records = []

    for chem in _chemistries(chemistry):
        start_col = PRODUCTION_BLOCKS[chem]
        value_col = start_col + 2
        reset_with_zero = _num(ws.cell(531, value_col).value)
        product_basis = _num(ws.cell(312, value_col).value) * _num(ws.cell(103, value_col).value)

        purchased_equipment = capital.loc[(chem, "Pyro", "Direct costs ($)"), "purchased_equipment"]
        land = _num(ws.cell(469, value_col).value) * purchased_equipment
        buildings = _num(ws.cell(465, value_col).value) * purchased_equipment
        plant_life = _num(ws.cell(104, value_col).value)

        for process, offset in COST_PER_LINE_COLUMNS.items():
            process_col = start_col + offset + 1
            raw = raw_materials.loc[(chem, process), AuditColumns.calculated(CathodeColumns.ANNUAL)]
            operating_labor = labor.loc[(chem, process, "Operating labor"), AuditColumns.calculated(CathodeColumns.ANNUAL)]
            supervisory_labor = labor.loc[
                (chem, process, "Direct supervisory and clerical labor"), AuditColumns.calculated(CathodeColumns.ANNUAL)
            ]
            utility = utilities.loc[(chem, process), AuditColumns.calculated(CathodeColumns.ANNUAL)]
            maintenance_cost = maintenance.loc[(chem, process, "Maintenance and repairs"), AuditColumns.calculated(CathodeColumns.ANNUAL)]
            operating_supplies = maintenance.loc[(chem, process, "Operating supplies"), AuditColumns.calculated(CathodeColumns.ANNUAL)]
            fixed_capital = capital.loc[(chem, process, "Fixed capital investment ($)"), AuditColumns.calculated(CommonColumns.VALUE)]
            total_capital = capital.loc[(chem, process, "Total capital investment ($)"), AuditColumns.calculated(CommonColumns.VALUE)]

            if reset_with_zero == 0:
                values = {
                    "Laboratory charges": 0.0,
                    "Patents and royalties": 0.0,
                    "Fixed charges": 0.0,
                    "Depreciation": 0.0,
                    "Local taxes": 0.0,
                    "Insurance": 0.0,
                    "Rent": 0.0,
                    "Financing": 0.0,
                    "Plant overhead costs": 0.0,
                    "General expenses": 0.0,
                    "Administrative costs": 0.0,
                    "Distribution and selling costs": 0.0,
                    "R&D costs": 0.0,
                    "Direct product costs": 0.0,
                    "Manufacturing cost": 0.0,
                    "Total product cost": 0.0,
                    "Profit": 0.0,
                    "Total product cost w/profit": 0.0,
                    "Total product cost to recipient": 0.0,
                }
            else:
                laboratory = _num(ws.cell(499, process_col).value) * operating_labor
                depreciation = (fixed_capital - land) / plant_life if plant_life else 0.0
                local_taxes = _num(ws.cell(506, process_col).value) * fixed_capital
                insurance = _num(ws.cell(508, process_col).value) * fixed_capital
                rent = _num(ws.cell(510, process_col).value) * (land + buildings)
                financing = _num(ws.cell(512, process_col).value) * total_capital
                fixed_charges = depreciation + local_taxes + insurance + rent + financing
                plant_overhead = _num(ws.cell(514, process_col).value) * (
                    operating_labor + supervisory_labor + maintenance_cost
                )
                administrative = _num(ws.cell(517, process_col).value) * (
                    operating_labor + supervisory_labor + maintenance_cost
                )
                base_without_total_product = (
                    raw
                    + operating_labor
                    + supervisory_labor
                    + utility
                    + maintenance_cost
                    + operating_supplies
                    + laboratory
                    + fixed_charges
                    + plant_overhead
                    + administrative
                )
                total_product_rate = (
                    _num(ws.cell(501, process_col).value)
                    + _num(ws.cell(519, process_col).value)
                    + _num(ws.cell(521, process_col).value)
                )
                total_product = (
                    base_without_total_product / (1.0 - total_product_rate)
                    if total_product_rate < 1.0
                    else 0.0
                )
                patents = _num(ws.cell(501, process_col).value) * total_product
                distribution = _num(ws.cell(519, process_col).value) * total_product
                rnd = _num(ws.cell(521, process_col).value) * total_product
                direct_product = (
                    raw
                    + operating_labor
                    + supervisory_labor
                    + utility
                    + maintenance_cost
                    + operating_supplies
                    + laboratory
                    + patents
                )
                manufacturing = direct_product + fixed_charges + plant_overhead
                general = administrative + distribution + rnd
                profit = total_capital * _num(ws.cell(525, process_col).value)
                total_with_profit = total_product + profit
                recipient = total_with_profit / product_basis if product_basis else 0.0
                values = {
                    "Laboratory charges": laboratory,
                    "Patents and royalties": patents,
                    "Fixed charges": fixed_charges,
                    "Depreciation": depreciation,
                    "Local taxes": local_taxes,
                    "Insurance": insurance,
                    "Rent": rent,
                    "Financing": financing,
                    "Plant overhead costs": plant_overhead,
                    "General expenses": general,
                    "Administrative costs": administrative,
                    "Distribution and selling costs": distribution,
                    "R&D costs": rnd,
                    "Direct product costs": direct_product,
                    "Manufacturing cost": manufacturing,
                    "Total product cost": total_product,
                    "Profit": profit,
                    "Total product cost w/profit": total_with_profit,
                    "Total product cost to recipient": recipient,
                }

            for item, calculated in values.items():
                workbook_value = workbook.loc[(chem, item), CathodeColumns.annual_col(process)]
                records.append(
                    {
                        CommonColumns.CHEMISTRY: chem,
                        CommonColumns.PROCESS: process,
                        CommonColumns.ITEM: item,
                        AuditColumns.calculated(CommonColumns.VALUE): calculated,
                        AuditColumns.workbook(CommonColumns.VALUE): workbook_value,
                        "delta": calculated - workbook_value,
                    }
                )
    return pd.DataFrame(records)


def cathode_cost_per_line_summary_calculated(chemistry: str | None = None) -> pd.DataFrame:
    workbook = cathode_cost_per_line_summary(chemistry).set_index([CommonColumns.CHEMISTRY, CommonColumns.ITEM])
    capital = cathode_capital_cost_calculated(chemistry).set_index([CommonColumns.CHEMISTRY, CommonColumns.PROCESS, CommonColumns.ITEM])
    total_cost = cathode_total_cost_calculated(chemistry).set_index([CommonColumns.CHEMISTRY, CommonColumns.PROCESS, CommonColumns.ITEM])
    records = []

    item_sources = {
        "Fixed capital investment ($)": ("capital", "Fixed capital investment ($)"),
        "Direct costs ($)": ("capital", "Direct costs ($)"),
        "Indirect costs ($)": ("capital", "Indirect costs ($)"),
        "Working capital ($)": ("capital", "Working capital ($)"),
        "Total capital investment ($)": ("capital", "Total capital investment ($)"),
        "Manufacturing cost ($/yr)": ("total", "Manufacturing cost"),
        "General expenses ($/yr)": ("total", "General expenses"),
        "Total product cost ($/yr)": ("total", "Total product cost"),
        "Total product cost w/profit ($/yr)": ("total", "Total product cost w/profit"),
        "Total cost to recipient ($/kg cathode)": ("total", "Total product cost to recipient"),
    }

    for chem in _chemistries(chemistry):
        for output_item, (source, source_item) in item_sources.items():
            record: dict[str, float | str] = {CommonColumns.CHEMISTRY: chem, CommonColumns.ITEM: output_item}
            for process in COST_PER_LINE_COLUMNS:
                if source == "capital":
                    calculated = capital.loc[(chem, process, source_item), AuditColumns.calculated(CommonColumns.VALUE)]
                else:
                    calculated = total_cost.loc[(chem, process, source_item), AuditColumns.calculated(CommonColumns.VALUE)]
                workbook_value = workbook.loc[(chem, output_item), process]
                record[AuditColumns.calculated(process)] = calculated
                record[AuditColumns.workbook(process)] = workbook_value
                record[f"{process}_delta"] = calculated - workbook_value
            records.append(record)
    return pd.DataFrame(records)


def cathode_cost_per_line_summary(chemistry: str | None = None) -> pd.DataFrame:
    ws = _cathode_ws()
    records = []
    for chem in _chemistries(chemistry):
        start_col = PRODUCTION_BLOCKS[chem]
        for row in range(67, 77):
            item = ws.cell(row, start_col).value
            if not _valid_label(item):
                continue
            record = {CommonColumns.CHEMISTRY: chem, CommonColumns.ITEM: _clean_label(item)}
            for process, offset in COST_PER_LINE_COLUMNS.items():
                record[process] = _num(ws.cell(row, start_col + offset).value)
            records.append(record)
    return pd.DataFrame(records)


def cathode_detailed_cost_summary(chemistry: str | None = None) -> pd.DataFrame:
    ws = _cathode_ws()
    records = []
    for chem in _chemistries(chemistry):
        start_col = PRODUCTION_BLOCKS[chem]
        for row, item in DETAILED_COST_ROWS.items():
            record = {CommonColumns.CHEMISTRY: chem, CommonColumns.ITEM: item}
            for process in COST_PER_LINE_COLUMNS:
                offset = COST_PER_LINE_COLUMNS[process]
                record[CathodeColumns.annual_col(process)] = _num(ws.cell(row, start_col + offset + 1).value)
                record[CathodeColumns.per_kg_col(process)] = _num(ws.cell(row, start_col + offset + 5).value)
            records.append(record)
    return pd.DataFrame(records)
