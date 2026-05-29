from __future__ import annotations

import pandas as pd

from .parameters import (
    MAN_PAR_SHEET,
    MAN_REC_PAR_SHEET,
    MANUFACTURING_CHEMISTRY_HEADERS,
    MANUFACTURING_RECYCLING_PROCESSES,
    get_manufacturing_cathode_chemistry,
    get_manufacturing_cathode_conversion_factor,
    get_manufacturing_cost_summary_rows,
    get_manufacturing_energy_factors,
    get_manufacturing_environment_summary_rows,
    get_manufacturing_general_inputs_addresses,
    get_manufacturing_locations,
    get_manufacturing_material_cost_specs,
    get_manufacturing_material_inputs_specs,
    get_manufacturing_recycled_cathode_material_costs_blocks,
    get_manufacturing_recycled_cathode_material_environment_blocks,
    get_manufacturing_recycled_share,
    get_manufacturing_solvent_use_specs,
    get_manufacturing_wide_table_specs,
    get_manufacturing_yields_specs,
    get_pack_basic_inputs_addresses,
    load_everbatt_workbook,
    workbook_sheet,
)
from .schemas import AuditColumns, CommonColumns, ManufacturingColumns
from .transport import _num


CHEMISTRY_HEADERS = MANUFACTURING_CHEMISTRY_HEADERS
RECYCLING_PROCESSES = MANUFACTURING_RECYCLING_PROCESSES


def _ws(kind: str = "virgin"):
    if kind == "virgin":
        return workbook_sheet(MAN_PAR_SHEET)
    if kind == "recycled":
        return workbook_sheet(MAN_REC_PAR_SHEET)
    raise ValueError(f"Unsupported manufacturing kind: {kind}")


def _valid(value) -> bool:
    return value is not None and str(value).strip() not in {"", "0"}


def _label(value) -> str:
    return str(value).strip()


def _wide_table(ws, label_col: int, value_cols: range, rows: range, key: str) -> pd.DataFrame:
    records = []
    headers = [_label(ws.cell(rows.start - 1, col).value) for col in value_cols]
    for row in rows:
        item = ws.cell(row, label_col).value
        if not _valid(item):
            continue
        record = {key: _label(item)}
        for header, col in zip(headers, value_cols, strict=True):
            if _valid(header):
                record[header] = _num(ws.cell(row, col).value)
        records.append(record)
    return pd.DataFrame(records)


def manufacturing_general_inputs(kind: str = "virgin") -> pd.DataFrame:
    ws = _ws(kind)
    rows = get_manufacturing_general_inputs_addresses(kind)
    return pd.DataFrame(
        {CommonColumns.ITEM: item, CommonColumns.UNIT: unit, CommonColumns.VALUE: ws[address].value}
        for item, unit, address in rows
    )


def manufacturing_cell_size(kind: str = "virgin") -> pd.DataFrame:
    ws = _ws(kind)
    specs = get_manufacturing_wide_table_specs(kind, "cell_size")
    return _wide_table(ws, *specs)


def manufacturing_cell_material_composition(kind: str = "virgin") -> pd.DataFrame:
    ws = _ws(kind)
    specs = get_manufacturing_wide_table_specs(kind, "cell_material_composition")
    return _wide_table(ws, *specs)


def manufacturing_cell_energy_consumption(kind: str = "virgin") -> pd.DataFrame:
    ws = _ws(kind)
    specs = get_manufacturing_wide_table_specs(kind, "cell_energy_consumption")
    return _wide_table(ws, *specs)


def manufacturing_cell_yields(kind: str = "virgin") -> pd.DataFrame:
    ws = _ws(kind)
    specs = get_manufacturing_yields_specs(kind)
    label_col = specs["label_col"]
    value_cols = specs["value_cols"]
    rows = specs["rows"]
    records = []
    for row in rows:
        item = ws.cell(row, label_col).value
        if not _valid(item):
            continue
        records.append(
            {
                CommonColumns.ITEM: _label(item),
                "selected": _num(ws.cell(row, value_cols[0]).value),
                "default": _num(ws.cell(row, value_cols[1]).value),
                "user_defined": _num(ws.cell(row, value_cols[2]).value),
            }
        )
    return pd.DataFrame(records)


def manufacturing_solvent_use(kind: str = "virgin") -> pd.DataFrame:
    ws = _ws(kind)
    specs = get_manufacturing_solvent_use_specs(kind)
    label_col = specs["label_col"]
    solvent_col = specs["solvent_col"]
    ratio_col = specs["ratio_col"]
    recovery_col = specs["recovery_col"]
    rows = specs["rows"]
    records = []
    for row in rows:
        item = ws.cell(row, label_col).value
        if not _valid(item):
            continue
        records.append(
            {
                CommonColumns.ITEM: _label(item),
                "solvent": ws.cell(row, solvent_col).value,
                "solvent_binder_mass_ratio": _num(ws.cell(row, ratio_col).value),
                "nmp_recovery_rate": _num(ws.cell(row, recovery_col).value),
            }
        )
    return pd.DataFrame(records)


def manufacturing_cell_material_inputs(kind: str = "virgin") -> pd.DataFrame:
    ws = _ws(kind)
    specs = get_manufacturing_material_inputs_specs(kind)
    header_row = specs["header_row"]
    value_row = specs["value_row"]
    first_col = specs["first_col"]
    last_col = specs["last_col"]
    records = []
    for col in range(first_col, last_col + 1):
        material = ws.cell(header_row, col).value
        if not _valid(material):
            continue
        records.append(
            {
                CommonColumns.MATERIAL: _label(material),
                ManufacturingColumns.KG_PER_KG_CELL: _num(ws.cell(value_row, col).value),
            }
        )
    return pd.DataFrame(records)


def manufacturing_cell_material_inputs_calculated(kind: str = "virgin") -> pd.DataFrame:
    composition = manufacturing_cell_material_composition(kind).set_index(CommonColumns.MATERIAL)["Selected"]
    yields = manufacturing_cell_yields(kind).set_index(CommonColumns.ITEM)["selected"]
    solvent = manufacturing_solvent_use(kind).set_index(CommonColumns.ITEM)
    workbook = manufacturing_cell_material_inputs(kind).set_index(CommonColumns.MATERIAL)

    cell_yield = yields.loc["Cell accepted after testing (%)"]
    cathode_yield = yields.loc["Active cathode material"]
    anode_yield = yields.loc["Active anode material"]
    aluminum_yield = yields.loc["Aluminum foil"]
    copper_yield = yields.loc["Copper foil"]
    separator_yield = yields.loc["Separator"]
    electrolyte_yield = yields.loc["Electrolyte"]

    cathode_solvent = solvent.loc["Cathode solvent"]
    anode_solvent = solvent.loc["Anode solvent"]
    cathode_binder = composition.loc["Binder: PVDF"]
    anode_binder = composition.loc["Binder: anode"]

    values = {
        "Active cathode material": composition.loc["Active cathode material"] / cathode_yield / cell_yield,
        "Graphite": composition.loc["Graphite"] / anode_yield / cell_yield,
        "Carbon black": composition.loc["Carbon black"] / cathode_yield / cell_yield,
        "Binder (PVDF)": cathode_binder / cathode_yield / cell_yield,
        "Copper": composition.loc["Copper"] / copper_yield / cell_yield,
        "Aluminum": composition.loc["Aluminum"] / aluminum_yield / cell_yield,
        "Electrolyte: LiPF6": composition.loc["Electrolyte: LiPF6"] / electrolyte_yield / cell_yield,
        "Electrolyte: EC": composition.loc["Electrolyte: EC"] / electrolyte_yield / cell_yield,
        "Electrolyte: DMC": composition.loc["Electrolyte: DMC"] / electrolyte_yield / cell_yield,
        "Plastic: PP": composition.loc["Plastic: PP"] / separator_yield / cell_yield,
        "Plastic: PE": composition.loc["Plastic: PE"] / separator_yield / cell_yield,
        "Plastic: PET": composition.loc["Plastic: PET"] / cell_yield,
        "Steel": composition.loc["Steel"] / cell_yield,
        "NMP": (
            cathode_binder
            / cathode_yield
            * cathode_solvent["solvent_binder_mass_ratio"]
            * (1.0 if cathode_solvent["solvent"] == "NMP" else 0.0)
            + anode_binder
            / anode_yield
            * anode_solvent["solvent_binder_mass_ratio"]
            * (1.0 if anode_solvent["solvent"] == "NMP" else 0.0)
        )
        / cell_yield,
        "Binder (anode)": anode_binder / anode_yield / cell_yield,
    }

    records = []
    for material, calculated in values.items():
        workbook_value = workbook.loc[material, ManufacturingColumns.KG_PER_KG_CELL]
        records.append(
            {
                CommonColumns.MATERIAL: material,
                AuditColumns.calculated(ManufacturingColumns.KG_PER_KG_CELL): calculated,
                AuditColumns.workbook(ManufacturingColumns.KG_PER_KG_CELL): workbook_value,
                "delta": calculated - workbook_value,
            }
        )
    return pd.DataFrame(records)


def manufacturing_cell_environment_summary(kind: str = "virgin") -> pd.DataFrame:
    ws = _ws(kind)
    records = []
    rows = get_manufacturing_environment_summary_rows(kind)
    if kind == "virgin":
        for row in rows:
            metric = ws.cell(row, 2).value
            if not _valid(metric) or str(metric).startswith("Total Emissions"):
                continue
            records.append(
                {
                    CommonColumns.METRIC: _label(metric),
                    ManufacturingColumns.MATERIAL_INPUTS: _num(ws.cell(row, 3).value),
                    ManufacturingColumns.ENERGY_INPUTS: _num(ws.cell(row, 4).value),
                    ManufacturingColumns.TOTAL: _num(ws.cell(row, 5).value),
                }
            )
    else:
        for row in rows:
            metric = ws.cell(row, 28).value
            if not _valid(metric) or str(metric).startswith("Total Emissions"):
                continue
            records.append(
                {
                    CommonColumns.METRIC: _label(metric),
                    "material_pyro": _num(ws.cell(row, 29).value),
                    "material_hydro": _num(ws.cell(row, 30).value),
                    "material_direct": _num(ws.cell(row, 31).value),
                    "material_custom": _num(ws.cell(row, 32).value),
                    ManufacturingColumns.ENERGY_INPUTS: _num(ws.cell(row, 33).value),
                    "total_pyro": _num(ws.cell(row, 34).value),
                    "total_hydro": _num(ws.cell(row, 35).value),
                    "total_direct": _num(ws.cell(row, 36).value),
                    "total_custom": _num(ws.cell(row, 37).value),
                }
            )
    return pd.DataFrame(records)


def _geographic_parameter_column(location: str, fallback_col: int) -> int:
    locs = get_manufacturing_locations()
    if location == locs["us"]:
        return 5
    if location == locs["china"]:
        return 6
    if location == locs["korea"]:
        return 8
    if location == locs["europe"]:
        return 7
    return fallback_col


def manufacturing_cell_energy_inputs_calculated(kind: str = "virgin") -> pd.DataFrame:
    wb = load_everbatt_workbook(data_only=True)
    greet = wb["GREET IO"]
    geographic = wb["Geographic Par."]
    workbook = manufacturing_cell_environment_summary(kind).set_index(CommonColumns.METRIC)

    factors = get_manufacturing_energy_factors(kind)
    total_energy = _num(factors["total_energy"])
    electricity_share = _num(factors["electricity_share"])
    fuel_share = _num(factors["fuel_share"])
    mmbtu_to_mj = _num(factors["mmbtu_to_mj"])
    location = str(factors["location"])

    if kind == "virgin":
        fallback_geo_col = 9
    elif kind == "recycled":
        fallback_geo_col = 12
    else:
        raise ValueError(f"Unsupported manufacturing kind: {kind}")

    geo_col = _geographic_parameter_column(str(location), fallback_geo_col)

    def process_energy(greet_row: int, geo_row: int, *, direct_fuel: float = 0.0, per_mmbtu: bool = False) -> float:
        electricity_factor = _num(geographic.cell(geo_row, geo_col).value)
        if per_mmbtu:
            fuel_factor = _num(greet.cell(greet_row, 2).value) / 1_000_000 + direct_fuel
            electricity_factor /= 1_000_000
        else:
            fuel_factor = _num(greet.cell(greet_row, 2).value) + direct_fuel
        return (
            total_energy / mmbtu_to_mj * fuel_share * fuel_factor
            + total_energy / mmbtu_to_mj * electricity_share * electricity_factor
        )

    values = {
        "Total Energy": process_energy(22, 70, direct_fuel=1.0, per_mmbtu=True),
        "Fossil fuels": process_energy(23, 71, direct_fuel=1.0, per_mmbtu=True),
        "Coal": process_energy(24, 72, per_mmbtu=True),
        "Natural gas": process_energy(25, 73, direct_fuel=1.0, per_mmbtu=True),
        "Petroleum": process_energy(26, 74, per_mmbtu=True),
        "Water consumption (gal/kg cell)": process_energy(27, 75),
        "VOC": process_energy(28, 76, direct_fuel=_num(greet["B4"].value)),
        "CO": process_energy(29, 77, direct_fuel=_num(greet["B5"].value)),
        "NOx": process_energy(30, 78, direct_fuel=_num(greet["B6"].value)),
        "PM10": process_energy(31, 79, direct_fuel=_num(greet["B7"].value)),
        "PM2.5": process_energy(32, 80, direct_fuel=_num(greet["B8"].value)),
        "SOx": process_energy(33, 81, direct_fuel=_num(greet["B9"].value)),
        "BC": process_energy(34, 82, direct_fuel=_num(greet["B10"].value)),
        "OC": process_energy(35, 83, direct_fuel=_num(greet["B11"].value)),
        "CH4": process_energy(36, 84, direct_fuel=_num(greet["B12"].value)),
        "N2O": process_energy(37, 85, direct_fuel=_num(greet["B13"].value)),
        "CO2": process_energy(38, 86, direct_fuel=_num(greet["B14"].value)),
    }
    values["CO2 (w/ C in VOC & CO)"] = (
        values["CO2"]
        + values["VOC"] * _num(greet["B118"].value) / _num(greet["B120"].value)
        + values["CO"] * _num(greet["B119"].value) / _num(greet["B120"].value)
    )
    values["GHGs"] = (
        values["CO2 (w/ C in VOC & CO)"]
        + values["CH4"] * _num(greet["B114"].value)
        + values["N2O"] * _num(greet["B115"].value)
    )

    records = []
    for metric, calculated in values.items():
        workbook_value = workbook.loc[metric, ManufacturingColumns.ENERGY_INPUTS]
        records.append(
            {
                CommonColumns.METRIC: metric,
                AuditColumns.calculated(ManufacturingColumns.ENERGY_INPUTS): calculated,
                AuditColumns.workbook(ManufacturingColumns.ENERGY_INPUTS): workbook_value,
                "delta": calculated - workbook_value,
            }
        )
    return pd.DataFrame(records)


def _hlookup_num(ws, lookup_value: str, header_row: int, first_col: int, last_col: int, value_row: int) -> tuple[bool, float]:
    for col in range(first_col, last_col + 1):
        if ws.cell(header_row, col).value == lookup_value:
            return True, _num(ws.cell(value_row, col).value)
    return False, 0.0


def manufacturing_recycled_material_burdens_calculated() -> pd.DataFrame:
    ws = _ws("recycled")
    wb = load_everbatt_workbook(data_only=True)
    greet = wb["GREET IO"]
    selected_chemistry = get_manufacturing_cathode_chemistry()
    workbook = manufacturing_cell_environment_summary("recycled").set_index(CommonColumns.METRIC)
    material_inputs = (
        manufacturing_cell_material_inputs_calculated("recycled")
        .set_index(CommonColumns.MATERIAL)[AuditColumns.calculated(ManufacturingColumns.KG_PER_KG_CELL)]
    )

    active_cathode = material_inputs.loc["Active cathode material"]
    recycled_selected = get_manufacturing_recycled_share()
    cathode_conversion = get_manufacturing_cathode_conversion_factor()

    route_tables = {
        "pyro": ("Pyro", "material_pyro"),
        "hydro": ("Hydro", "material_hydro"),
        "direct": ("Direct", "material_direct"),
        "custom": ("Custom", "material_custom"),
    }
    route_environment = {
        key: manufacturing_recycled_cathode_material_environment(process).set_index(CommonColumns.METRIC)
        for key, (process, _) in route_tables.items()
    }

    def other_recycled_material_mass(material: str) -> float:
        if material == "Electrolyte organics":
            return material_inputs.loc["Electrolyte: EC"] + material_inputs.loc["Electrolyte: DMC"]
        if material in material_inputs.index:
            return material_inputs.loc[material]
        return 0.0

    def other_recycled_material_burden(material: str, greet_row: int) -> float:
        found, value = _hlookup_num(greet, material, 77, 2, 52, greet_row)
        return value if found else 0.0

    def base_material_burden(greet_row: int) -> tuple[bool, float]:
        found, virgin_cathode = _hlookup_num(greet, selected_chemistry, 77, 2, 52, greet_row)
        if not found:
            return False, 0.0

        binder_to_steel = (
            material_inputs.loc["Binder (PVDF)"] * _num(greet.cell(greet_row, 12).value)
            + material_inputs.loc["Copper"] * _num(greet.cell(greet_row, 13).value)
            + material_inputs.loc["Aluminum"] * _num(greet.cell(greet_row, 14).value)
            + material_inputs.loc["Electrolyte: LiPF6"] * _num(greet.cell(greet_row, 15).value)
            + material_inputs.loc["Electrolyte: EC"] * _num(greet.cell(greet_row, 16).value)
            + material_inputs.loc["Electrolyte: DMC"] * _num(greet.cell(greet_row, 17).value)
            + material_inputs.loc["Plastic: PP"] * _num(greet.cell(greet_row, 18).value)
            + material_inputs.loc["Plastic: PE"] * _num(greet.cell(greet_row, 19).value)
            + material_inputs.loc["Plastic: PET"] * _num(greet.cell(greet_row, 20).value)
            + material_inputs.loc["Steel"] * _num(greet.cell(greet_row, 21).value)
        )
        value = (
            active_cathode * (1.0 - recycled_selected) * virgin_cathode
            + (material_inputs.loc["Graphite"] + material_inputs.loc["Carbon black"])
            * _num(greet.cell(greet_row, 11).value)
            + binder_to_steel
            + material_inputs.loc["NMP"] * _num(greet.cell(greet_row, 8).value)
            + material_inputs.loc["Binder (anode)"] * _num(greet.cell(greet_row, 12).value)
        ) * cathode_conversion
        return True, value

    def credit_for_other_recycled_materials(greet_row: int) -> float:
        credit = 0.0
        for material_cell, content_cell in (("AB12", "AC12"), ("AB13", "AC13")):
            material = ws[material_cell].value
            content = _num(ws[content_cell].value)
            credit += (
                content
                * other_recycled_material_mass(str(material))
                * other_recycled_material_burden(str(material), greet_row)
                * cathode_conversion
            )
        return credit

    records = []
    for metric, env_row in [
        ("Total Energy", 70),
        ("Fossil fuels", 71),
        ("Coal", 72),
        ("Natural gas", 73),
        ("Petroleum", 74),
        ("Water consumption (gal/kg cell)", 75),
        ("VOC", 77),
        ("CO", 78),
        ("NOx", 79),
        ("PM10", 80),
        ("PM2.5", 81),
        ("SOx", 82),
        ("BC", 83),
        ("OC", 84),
        ("CH4", 85),
        ("N2O", 86),
        ("CO2", 87),
        ("CO2 (w/ C in VOC & CO)", 88),
        ("GHGs", 89),
    ]:
        greet_row = env_row + 9
        base_found, base = base_material_burden(greet_row)
        credit = credit_for_other_recycled_materials(greet_row)
        record: dict[str, float | str] = {CommonColumns.METRIC: metric}
        for key, (_, workbook_column) in route_tables.items():
            route_df = route_environment[key]
            if not base_found or selected_chemistry not in route_df.columns:
                calculated = 0.0
            else:
                calculated = base + active_cathode * recycled_selected * route_df.loc[metric, selected_chemistry] - credit
            workbook_value = workbook.loc[metric, workbook_column]
            record[AuditColumns.calculated(workbook_column)] = calculated
            record[AuditColumns.workbook(workbook_column)] = workbook_value
            record[f"{workbook_column}_delta"] = calculated - workbook_value
        records.append(record)
    return pd.DataFrame(records)


def manufacturing_recycled_environment_totals_calculated() -> pd.DataFrame:
    ws = _ws("recycled")
    wb = load_everbatt_workbook(data_only=True)
    greet = wb["GREET IO"]
    selected_chemistry = get_manufacturing_cathode_chemistry()
    workbook = manufacturing_cell_environment_summary("recycled").set_index(CommonColumns.METRIC)
    material_burdens = manufacturing_recycled_material_burdens_calculated().set_index(CommonColumns.METRIC)
    energy_inputs = (
        manufacturing_cell_energy_inputs_calculated("recycled")
        .set_index(CommonColumns.METRIC)[AuditColumns.calculated(ManufacturingColumns.ENERGY_INPUTS)]
    )
    has_valid_cathode_lookup, _ = _hlookup_num(greet, selected_chemistry, 77, 2, 52, 79)

    route_tables = {
        "pyro": ("material_pyro", "total_pyro"),
        "hydro": ("material_hydro", "total_hydro"),
        "direct": ("material_direct", "total_direct"),
        "custom": ("material_custom", "total_custom"),
    }

    records = []
    for metric in material_burdens.index:
        record: dict[str, float | str] = {CommonColumns.METRIC: metric}
        energy = energy_inputs.loc[metric]
        for key, (material_column, total_column) in route_tables.items():
            if has_valid_cathode_lookup:
                calculated = material_burdens.loc[metric, AuditColumns.calculated(material_column)] + energy
            else:
                calculated = 0.0
            workbook_value = workbook.loc[metric, total_column]
            record[AuditColumns.calculated(total_column)] = calculated
            record[AuditColumns.workbook(total_column)] = workbook_value
            record[f"{total_column}_delta"] = calculated - workbook_value
        records.append(record)
    return pd.DataFrame(records)


def manufacturing_cell_material_cost(kind: str = "virgin") -> pd.DataFrame:
    ws = _ws(kind)
    specs = get_manufacturing_material_cost_specs(kind)
    header_row = specs["header_row"]
    value_row = specs["value_row"]
    first_col = specs["first_col"]
    last_col = specs["last_col"]
    records = []
    for col in range(first_col, last_col + 1):
        item = ws.cell(header_row, col).value
        if not _valid(item):
            continue
        records.append(
            {
                CommonColumns.ITEM: _label(item),
                ManufacturingColumns.COST_PER_KG_CELL: _num(ws.cell(value_row, col).value),
            }
        )
    return pd.DataFrame(records)


def manufacturing_cell_cost_summary(kind: str = "virgin") -> pd.DataFrame:
    ws = _ws(kind)
    records = []
    rows = get_manufacturing_cost_summary_rows(kind)
    if kind == "virgin":
        for row in rows:
            item = ws.cell(row, 2).value
            if _valid(item):
                records.append({CommonColumns.ITEM: _label(item), CommonColumns.VALUE: _num(ws.cell(row, 3).value)})
    else:
        for row in rows:
            item = ws.cell(row, 28).value
            if not _valid(item):
                continue
            records.append(
                {
                    CommonColumns.ITEM: _label(item),
                    "Pyro": _num(ws.cell(row, 29).value),
                    "Hydro": _num(ws.cell(row, 30).value),
                    "Direct": _num(ws.cell(row, 31).value),
                    "Custom": _num(ws.cell(row, 32).value),
                }
            )
    return pd.DataFrame(records)


def manufacturing_pack_basic_inputs() -> pd.DataFrame:
    ws = _ws("virgin")
    rows = get_pack_basic_inputs_addresses()
    return pd.DataFrame(
        {CommonColumns.ITEM: item, CommonColumns.UNIT: unit, CommonColumns.VALUE: ws[address].value}
        for item, unit, address in rows
    )


def manufacturing_pack_configuration() -> pd.DataFrame:
    ws = _ws("virgin")
    rows = (13, 14, 15)
    records = []
    for row in rows:
        item = ws.cell(row, 28).value
        if _valid(item):
            records.append(
                {
                    CommonColumns.ITEM: _label(item),
                    "selected": _num(ws.cell(row, 29).value),
                    "default": _num(ws.cell(row, 30).value),
                    "user_defined": _num(ws.cell(row, 31).value),
                }
            )
        item = ws.cell(row, 32).value
        if _valid(item):
            records.append(
                {
                    CommonColumns.ITEM: _label(item),
                    "selected": _num(ws.cell(row, 33).value),
                    "default": _num(ws.cell(row, 34).value),
                    "user_defined": _num(ws.cell(row, 35).value),
                }
            )
    return pd.DataFrame(records)


def manufacturing_module_component_masses() -> pd.DataFrame:
    specs = get_manufacturing_wide_table_specs("virgin", "module_component_masses")
    return _wide_table(_ws("virgin"), *specs)


def manufacturing_pack_component_masses() -> pd.DataFrame:
    specs = get_manufacturing_wide_table_specs("virgin", "pack_component_masses")
    return _wide_table(_ws("virgin"), *specs)


def manufacturing_pack_component_prices() -> pd.DataFrame:
    ws = _ws("virgin")
    records = []
    for row in range(45, 58):
        item = ws.cell(row, 28).value
        if _valid(item):
            records.append(
                {
                    CommonColumns.COMPONENT: _label(item),
                    "selected": _num(ws.cell(row, 29).value),
                    "default": _num(ws.cell(row, 30).value),
                    "user_defined": _num(ws.cell(row, 31).value),
                }
            )
    return pd.DataFrame(records)


def manufacturing_pack_energy_consumption() -> pd.DataFrame:
    specs = get_manufacturing_wide_table_specs("virgin", "pack_energy_consumption")
    return _wide_table(_ws("virgin"), *specs)


def manufacturing_pack_mass_summary() -> pd.DataFrame:
    ws = _ws("virgin")
    records = []
    for col in range(29, 32):
        item = ws.cell(87, col).value
        if _valid(item):
            records.append({CommonColumns.ITEM: _label(item), "kg": _num(ws.cell(88, col).value)})
    return pd.DataFrame(records)


def manufacturing_pack_environment_summary() -> pd.DataFrame:
    ws = _ws("virgin")
    records = []
    for row in range(97, 117):
        metric = ws.cell(row, 28).value
        if not _valid(metric) or str(metric).startswith("Total Emissions"):
            continue
        records.append(
            {
                CommonColumns.METRIC: _label(metric),
                ManufacturingColumns.MATERIAL_INPUTS: _num(ws.cell(row, 29).value),
                ManufacturingColumns.ENERGY_INPUTS: _num(ws.cell(row, 30).value),
                ManufacturingColumns.TOTAL: _num(ws.cell(row, 31).value),
            }
        )
    return pd.DataFrame(records)


def manufacturing_pack_material_cost() -> pd.DataFrame:
    ws = _ws("virgin")
    records = []
    for col in range(29, 47):
        item = ws.cell(120, col).value
        if _valid(item):
            records.append({CommonColumns.COMPONENT: _label(item), "cost_per_pack": _num(ws.cell(121, col).value)})
    return pd.DataFrame(records)


def manufacturing_pack_cost_summary() -> pd.DataFrame:
    ws = _ws("virgin")
    records = []
    for row in range(130, 146):
        item = ws.cell(row, 28).value
        if _valid(item):
            records.append({CommonColumns.ITEM: _label(item), CommonColumns.VALUE: _num(ws.cell(row, 29).value)})
    return pd.DataFrame(records)


def manufacturing_recycled_cathode_material_environment(process: str) -> pd.DataFrame:
    ws = _ws("recycled")
    blocks = get_manufacturing_recycled_cathode_material_environment_blocks()
    if process not in blocks:
        raise ValueError(f"Unsupported recycled manufacturing process: {process}")
    header_row, rows, cols = blocks[process]
    records = []
    headers = [_label(ws.cell(header_row, col).value) for col in cols]
    for row in rows:
        metric = ws.cell(row, 2).value
        if not _valid(metric) or str(metric).startswith("Total Emissions"):
            continue
        record = {CommonColumns.PROCESS: process, CommonColumns.METRIC: _label(metric)}
        for header, col in zip(headers, cols, strict=True):
            record[header] = _num(ws.cell(row, col).value)
        records.append(record)
    return pd.DataFrame(records)


def manufacturing_recycled_cathode_material_costs() -> pd.DataFrame:
    ws = _ws("recycled")
    blocks = get_manufacturing_recycled_cathode_material_costs_blocks()
    records = []
    for process, (header_row, value_row, cols) in blocks.items():
        for col in cols:
            chemistry = ws.cell(header_row, col).value
            if _valid(chemistry):
                records.append(
                    {
                        CommonColumns.PROCESS: process,
                        CommonColumns.CHEMISTRY: _label(chemistry),
                        "cost_per_kg_cathode": _num(ws.cell(value_row, col).value),
                    }
                )
    return pd.DataFrame(records)
