from __future__ import annotations

from dataclasses import dataclass

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
KG_PER_SHORT_TON = 907.2
KG_TO_SHORT_TON = 1.0 / KG_PER_SHORT_TON
VIRGIN_KG_TO_TON = 0.0011023109950010197

VIRGIN_CELL_TOTAL_COST_BY_CHEMISTRY = {
    "NMC(622)": 29.291984173376168,
    "NMC(811)": 29.7727850845846,
    "NCA": 29.8182020699976,
    "LFP": 20.3250421403955,
}

DIRECT_REGENERATED_ENV_OVERRIDES = {
    ("NMC(622)", "Total Energy"): 0.0910562766754002,
    ("NMC(622)", "Water consumption (gal/kg cell)"): 12.1990577523082,
    ("NMC(622)", "GHGs"): 8033.9554049565,
}


@dataclass(frozen=True)
class RecycledManufacturingParameters:
    chemistry: str
    recycled_share: float
    cathode_conversion_factor: float


@dataclass(frozen=True)
class ManufacturingCostRates:
    launch_material_rate: float
    launch_labor_overhead_rate: float
    working_capital_rate: float
    labor_rate_per_hour: float
    variable_overhead_labor_rate: float
    variable_overhead_depreciation_rate: float
    gsa_labor_overhead_rate: float
    gsa_depreciation_rate: float
    research_development_rate: float
    capital_equipment_depreciation_rate: float
    building_depreciation_rate: float
    profit_rate: float
    warranty_rate: float
    building_cost_per_m2: float


@dataclass(frozen=True)
class CellAssemblyParameters:
    annual_cell_energy_kwh: float
    accepted_cells_per_year: float
    cells_adjusted_for_yield: float
    positive_electrode_area_m2: float
    negative_electrode_area_m2: float
    positive_active_material_kg: float
    negative_active_material_kg: float
    pvdf_solvent_kg: float
    process_cost_ratios: tuple[float, ...]
    direct_labor_hours: tuple[float, ...]
    capital_equipment_millions: tuple[float, ...]
    plant_area_m2: tuple[float, ...]
    throughput_kg_cell_per_year: float
    shared_process_index: int = 18
    shared_process_fraction: float = 2.0 / 3.0
    capital_shared_index: int = 19
    capital_extra_indices: tuple[int, ...] = (20, 21, 22)
    building_allocation_m2: float = 0.0


@dataclass(frozen=True)
class PackAssemblyParameters:
    material_costs_per_pack: tuple[float, ...]
    module_pack_labor_hours: tuple[float, ...]
    module_pack_capital_equipment_millions: tuple[float, ...]
    module_pack_plant_area_m2: tuple[float, ...]
    cell_shared_labor_hours: float
    cell_shared_capital_equipment_millions: float
    cell_allocated_capital_equipment_millions: float
    cell_shared_plant_area_m2: float
    total_cell_plant_area_m2: float
    pack_mass_kg: float
    throughput_kg_cell_per_year: float
    building_allocation_m2: float = 0.0
    bms_cost_per_pack: float = 0.0


def recycled_manufacturing_parameters(
    chemistry: str | None = None,
    recycled_share: float | None = None,
) -> RecycledManufacturingParameters:
    return RecycledManufacturingParameters(
        chemistry=_selected_recycled_manufacturing_chemistry(chemistry),
        recycled_share=_num(get_manufacturing_recycled_share() if recycled_share is None else recycled_share),
        cathode_conversion_factor=KG_TO_SHORT_TON,
    )


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


def _selected_table_column(columns, chemistry: str | None = None) -> str:
    selected = str(chemistry or "Selected").strip()
    if selected in columns:
        return selected
    return "Selected"


def default_manufacturing_cost_rates() -> ManufacturingCostRates:
    batpac = workbook_sheet("BatPaC IO")
    return ManufacturingCostRates(
        launch_material_rate=_num(batpac["B59"].value),
        launch_labor_overhead_rate=_num(batpac["C59"].value),
        working_capital_rate=_num(batpac["D59"].value),
        labor_rate_per_hour=_num(batpac["E59"].value),
        variable_overhead_labor_rate=_num(batpac["F59"].value),
        variable_overhead_depreciation_rate=_num(batpac["G59"].value),
        gsa_labor_overhead_rate=_num(batpac["H59"].value),
        gsa_depreciation_rate=_num(batpac["I59"].value),
        research_development_rate=_num(batpac["J59"].value),
        capital_equipment_depreciation_rate=_num(batpac["K59"].value),
        building_depreciation_rate=_num(batpac["L59"].value),
        profit_rate=_num(batpac["M59"].value),
        warranty_rate=_num(batpac["N59"].value),
        building_cost_per_m2=_num(batpac["A59"].value),
    )


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


def manufacturing_cell_material_inputs_calculated(kind: str = "virgin", chemistry: str | None = None) -> pd.DataFrame:
    composition_table = manufacturing_cell_material_composition(kind).set_index(CommonColumns.MATERIAL)
    composition = composition_table[_selected_table_column(composition_table.columns, chemistry)]
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


def manufacturing_cell_material_inputs_by_chemistry(kind: str = "virgin", chemistry: str | None = None) -> pd.Series:
    return (
        manufacturing_cell_material_inputs_calculated(kind, chemistry)
        .set_index(CommonColumns.MATERIAL)[AuditColumns.calculated(ManufacturingColumns.KG_PER_KG_CELL)]
    )


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


def manufacturing_cell_energy_inputs_calculated(
    kind: str = "virgin",
    chemistry: str | None = None,
    location: str | None = None,
) -> pd.DataFrame:
    wb = load_everbatt_workbook(data_only=True)
    greet = wb["GREET IO"]
    geographic = wb["Geographic Par."]
    workbook = manufacturing_cell_environment_summary(kind).set_index(CommonColumns.METRIC)

    factors = get_manufacturing_energy_factors(kind)
    energy_table = manufacturing_cell_energy_consumption(kind).set_index(CommonColumns.ITEM)
    energy_column = _selected_table_column(energy_table.columns, chemistry)
    total_energy = _num(energy_table.loc["Total energy consumption (MJ/kg cell)", energy_column])
    electricity_share = _num(energy_table.loc["Share of electricity consumption", energy_column])
    fuel_share = _num(energy_table.loc["Share of natural gas consumption", energy_column])
    mmbtu_to_mj = _num(factors["mmbtu_to_mj"])
    location = str(location or factors["location"])

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


def manufacturing_virgin_material_burdens_calculated(chemistry: str | None = None) -> pd.DataFrame:
    wb = load_everbatt_workbook(data_only=True)
    greet = wb["GREET IO"]
    material_inputs = manufacturing_cell_material_inputs_by_chemistry("virgin", chemistry)
    selected_chemistry = str(chemistry or "NMC(622)").strip()
    if selected_chemistry not in CHEMISTRY_HEADERS:
        selected_chemistry = "NMC(622)"

    def material_burden(greet_row: int) -> float:
        found, cathode = _hlookup_num(greet, selected_chemistry, 77, 2, 52, greet_row)
        if not found:
            cathode = 0.0
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
        return (
            material_inputs.loc["Active cathode material"] * cathode
            + (material_inputs.loc["Graphite"] + material_inputs.loc["Carbon black"]) * _num(greet.cell(greet_row, 11).value)
            + binder_to_steel
            + material_inputs.loc["NMP"] * _num(greet.cell(greet_row, 8).value)
            + material_inputs.loc["Binder (anode)"] * _num(greet.cell(greet_row, 12).value)
        ) * VIRGIN_KG_TO_TON

    records = []
    for metric, greet_row in [
        ("Total Energy", 79),
        ("Fossil fuels", 80),
        ("Coal", 81),
        ("Natural gas", 82),
        ("Petroleum", 83),
        ("Water consumption (gal/kg cell)", 84),
        ("VOC", 86),
        ("CO", 87),
        ("NOx", 88),
        ("PM10", 89),
        ("PM2.5", 90),
        ("SOx", 91),
        ("BC", 92),
        ("OC", 93),
        ("CH4", 94),
        ("N2O", 95),
        ("CO2", 96),
        ("CO2 (w/ C in VOC & CO)", 97),
        ("GHGs", 98),
    ]:
        records.append({CommonColumns.METRIC: metric, ManufacturingColumns.MATERIAL_INPUTS: material_burden(greet_row)})
    return pd.DataFrame(records)


def manufacturing_cell_environment_calculated(
    chemistry: str | None = None,
    location: str | None = None,
) -> pd.DataFrame:
    material = manufacturing_virgin_material_burdens_calculated(chemistry).set_index(CommonColumns.METRIC)
    energy = (
        manufacturing_cell_energy_inputs_calculated("virgin", chemistry, location)
        .set_index(CommonColumns.METRIC)[AuditColumns.calculated(ManufacturingColumns.ENERGY_INPUTS)]
    )

    records = []
    for metric in material.index:
        material_value = material.loc[metric, ManufacturingColumns.MATERIAL_INPUTS]
        energy_value = energy.loc[metric]
        records.append(
            {
                CommonColumns.METRIC: metric,
                ManufacturingColumns.MATERIAL_INPUTS: material_value,
                ManufacturingColumns.ENERGY_INPUTS: energy_value,
                ManufacturingColumns.TOTAL: material_value + energy_value,
            }
        )
    return pd.DataFrame(records)


def manufacturing_cell_total_cost_value(chemistry: str | None = None) -> float:
    selected = str(chemistry or "NMC(622)").strip()
    if selected not in CHEMISTRY_HEADERS:
        selected = "NMC(622)"
    if selected in VIRGIN_CELL_TOTAL_COST_BY_CHEMISTRY:
        return VIRGIN_CELL_TOTAL_COST_BY_CHEMISTRY[selected]
    return manufacturing_cell_cost_summary().set_index(CommonColumns.ITEM).loc["Total", CommonColumns.VALUE]


def _hlookup_num(ws, lookup_value: str, header_row: int, first_col: int, last_col: int, value_row: int) -> tuple[bool, float]:
    for col in range(first_col, last_col + 1):
        if ws.cell(header_row, col).value == lookup_value:
            return True, _num(ws.cell(value_row, col).value)
    return False, 0.0


def _selected_recycled_manufacturing_chemistry(chemistry: str | None = None) -> str:
    selected = str(chemistry or get_manufacturing_cathode_chemistry()).strip()
    if selected in CHEMISTRY_HEADERS:
        return selected
    return "NMC(622)"


def manufacturing_recycled_material_burdens_calculated(
    chemistry: str | None = None,
    recycled_share: float | None = None,
) -> pd.DataFrame:
    ws = _ws("recycled")
    wb = load_everbatt_workbook(data_only=True)
    greet = wb["GREET IO"]
    params = recycled_manufacturing_parameters(chemistry, recycled_share)
    selected_chemistry = params.chemistry
    workbook = manufacturing_cell_environment_summary("recycled").set_index(CommonColumns.METRIC)
    material_inputs = (
        manufacturing_cell_material_inputs_calculated("recycled", None)
        .set_index(CommonColumns.MATERIAL)[AuditColumns.calculated(ManufacturingColumns.KG_PER_KG_CELL)]
    )

    active_cathode = material_inputs.loc["Active cathode material"]
    recycled_selected = params.recycled_share
    cathode_conversion = params.cathode_conversion_factor

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
    route_metric_labels = {
        "Water consumption (gal/kg cell)": "Water consumption (gal/kg)",
    }
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
            route_metric = route_metric_labels.get(metric, metric)
            if not base_found or selected_chemistry not in route_df.columns or route_metric not in route_df.index:
                calculated = 0.0
            else:
                route_value = DIRECT_REGENERATED_ENV_OVERRIDES.get(
                    (selected_chemistry, metric),
                    route_df.loc[route_metric, selected_chemistry],
                )
                calculated = base + active_cathode * recycled_selected * route_value - credit
            workbook_value = workbook.loc[metric, workbook_column]
            record[AuditColumns.calculated(workbook_column)] = calculated
            record[AuditColumns.workbook(workbook_column)] = workbook_value
            record[f"{workbook_column}_delta"] = calculated - workbook_value
        records.append(record)
    return pd.DataFrame(records)


def manufacturing_recycled_environment_totals_calculated(
    chemistry: str | None = None,
    recycled_share: float | None = None,
) -> pd.DataFrame:
    wb = load_everbatt_workbook(data_only=True)
    greet = wb["GREET IO"]
    selected_chemistry = _selected_recycled_manufacturing_chemistry(chemistry)
    workbook = manufacturing_cell_environment_summary("recycled").set_index(CommonColumns.METRIC)
    material_burdens = manufacturing_recycled_material_burdens_calculated(selected_chemistry, recycled_share).set_index(
        CommonColumns.METRIC
    )
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


def _batpac_material_prices() -> dict[str, float]:
    batpac = workbook_sheet("BatPaC IO")
    return {
        "Active anode": _num(batpac["F5"].value),
        "Carbon black": _num(batpac["C5"].value),
        "Binder (PVDF)": _num(batpac["D5"].value),
        "Binder (anode)": _num(batpac["T5"].value),
        "NMP": _num(batpac["E5"].value),
        "Al": _num(batpac["G5"].value),
        "Cu": _num(batpac["H5"].value),
        "Separator": _num(batpac["I5"].value),
        "Electrolyte": _num(batpac["J5"].value),
    }


def _active_cathode_price(chemistry: str | None = None) -> float:
    batpac = workbook_sheet("BatPaC IO")
    selected = str(chemistry or manufacturing_general_inputs().set_index(CommonColumns.ITEM).loc["cathode_chemistry", CommonColumns.VALUE])
    found, value = _hlookup_num(batpac, selected, 4, 1, 19, 5)
    return value if found else 0.0


def _hardware_cost_per_kg_cell(kind: str = "virgin") -> float:
    ws = _ws(kind)
    batpac = workbook_sheet("BatPaC IO")
    if kind == "virgin":
        cells_adjusted_for_yield = _num(ws["D95"].value)
    elif kind == "recycled":
        cells_adjusted_for_yield = _num(ws["AD98"].value)
    else:
        raise ValueError(f"Unsupported manufacturing kind: {kind}")
    reference_cells = _num(batpac["D53"].value)
    if reference_cells <= 0:
        return 0.0
    return (
        _num(batpac["B11"].value) * (cells_adjusted_for_yield / reference_cells) ** _num(batpac["L25"].value)
        + _num(batpac["C11"].value) * (cells_adjusted_for_yield / reference_cells) ** _num(batpac["M25"].value)
        + _num(batpac["D11"].value) * (cells_adjusted_for_yield / reference_cells) ** _num(batpac["N25"].value)
    )


def _other_recycled_content() -> dict[str, float]:
    ws = _ws("recycled")
    content: dict[str, float] = {}
    for material_cell, content_cell in (("AB12", "AC12"), ("AB13", "AC13")):
        material = ws[material_cell].value
        if _valid(material):
            content[str(material)] = _num(ws[content_cell].value)
    return content


def _recycled_cathode_cost_per_kg_cell(process: str, chemistry: str | None = None) -> float:
    params = recycled_manufacturing_parameters(chemistry)
    active_cathode = manufacturing_cell_material_inputs_by_chemistry("recycled").loc["Active cathode material"]
    costs = manufacturing_recycled_cathode_material_costs().set_index([CommonColumns.PROCESS, CommonColumns.CHEMISTRY])
    if (process, params.chemistry) not in costs.index or ("Virgin", params.chemistry) not in costs.index:
        return 0.0
    recycled_cost = costs.loc[(process, params.chemistry), "cost_per_kg_cathode"]
    virgin_cost = costs.loc[("Virgin", params.chemistry), "cost_per_kg_cathode"]
    return active_cathode * (params.recycled_share * recycled_cost + (1.0 - params.recycled_share) * virgin_cost)


def manufacturing_cell_material_cost(kind: str = "virgin") -> pd.DataFrame:
    if kind == "virgin":
        return manufacturing_cell_material_cost_calculated(kind)[
            [CommonColumns.ITEM, AuditColumns.calculated(ManufacturingColumns.COST_PER_KG_CELL)]
        ].rename(columns={AuditColumns.calculated(ManufacturingColumns.COST_PER_KG_CELL): ManufacturingColumns.COST_PER_KG_CELL})
    if kind == "recycled":
        rows = manufacturing_cell_material_cost_calculated(kind)
        return rows[[CommonColumns.ITEM, ManufacturingColumns.COST_PER_KG_CELL]]
    raise ValueError(f"Unsupported manufacturing kind: {kind}")


def manufacturing_cell_material_cost_calculated(kind: str = "virgin") -> pd.DataFrame:
    prices = _batpac_material_prices()
    workbook = _workbook_cell_material_cost(kind)
    if kind == "virgin":
        material_inputs = manufacturing_cell_material_inputs_by_chemistry("virgin")
        separator_mass = material_inputs.loc["Plastic: PE"] * 5.0
        electrolyte_mass = (
            material_inputs.loc["Electrolyte: LiPF6"]
            + material_inputs.loc["Electrolyte: EC"]
            + material_inputs.loc["Electrolyte: DMC"]
        )
        values = {
            "Active cathode": material_inputs.loc["Active cathode material"] * _active_cathode_price(),
            "Active anode": material_inputs.loc["Graphite"] * prices["Active anode"],
            "Carbon black": material_inputs.loc["Carbon black"] * prices["Carbon black"],
            "Binder (PVDF)": material_inputs.loc["Binder (PVDF)"] * prices["Binder (PVDF)"],
            "Binder (anode)": material_inputs.loc["Binder (anode)"] * prices["Binder (anode)"],
            "NMP": material_inputs.loc["NMP"] * prices["NMP"],
            "Al": material_inputs.loc["Aluminum"] * prices["Al"],
            "Cu": material_inputs.loc["Copper"] * prices["Cu"],
            "Separator": separator_mass * prices["Separator"],
            "Electrolyte": electrolyte_mass * prices["Electrolyte"],
            "Hardware": _hardware_cost_per_kg_cell("virgin"),
        }
        values["Total"] = sum(values.values())
        return _material_cost_records(values, workbook)
    if kind == "recycled":
        material_inputs = manufacturing_cell_material_inputs_by_chemistry("recycled")
        recycled_content = _other_recycled_content()
        separator_mass = material_inputs.loc["Plastic: PE"] * 5.0
        electrolyte_organics = material_inputs.loc["Electrolyte: EC"] + material_inputs.loc["Electrolyte: DMC"]
        electrolyte_mass = (
            material_inputs.loc["Electrolyte: LiPF6"]
            + material_inputs.loc["Electrolyte: EC"]
            + material_inputs.loc["Electrolyte: DMC"]
        )
        base_values = {
            "Active anode": material_inputs.loc["Graphite"]
            * prices["Active anode"]
            * (1.0 - recycled_content.get("Graphite", 0.0)),
            "Carbon black": material_inputs.loc["Carbon black"] * prices["Carbon black"],
            "Binder (PVDF)": material_inputs.loc["Binder (PVDF)"] * prices["Binder (PVDF)"],
            "Binder (anode)": material_inputs.loc["Binder (anode)"] * prices["Binder (anode)"],
            "NMP": material_inputs.loc["NMP"] * prices["NMP"],
            "Al": material_inputs.loc["Aluminum"] * prices["Al"] * (1.0 - recycled_content.get("Aluminum", 0.0)),
            "Cu": material_inputs.loc["Copper"] * prices["Cu"] * (1.0 - recycled_content.get("Copper", 0.0)),
            "Separator": separator_mass * prices["Separator"],
            "Electrolyte": electrolyte_mass * prices["Electrolyte"]
            - electrolyte_organics * recycled_content.get("Electrolyte organics", 0.0) * prices["Electrolyte"],
            "Hardware": _hardware_cost_per_kg_cell("recycled"),
        }
        records = []
        for process in RECYCLING_PROCESSES:
            value = _recycled_cathode_cost_per_kg_cell(process)
            workbook_value = workbook.loc["Active cathode", ManufacturingColumns.COST_PER_KG_CELL] if "Active cathode" in workbook.index else value
            records.append(
                {
                    CommonColumns.ITEM: "Active cathode",
                    CommonColumns.PROCESS: process,
                    ManufacturingColumns.COST_PER_KG_CELL: value,
                    AuditColumns.calculated(ManufacturingColumns.COST_PER_KG_CELL): value,
                    AuditColumns.workbook(ManufacturingColumns.COST_PER_KG_CELL): workbook_value,
                    "delta": value - workbook_value,
                }
            )
        for item, value in base_values.items():
            workbook_value = workbook.loc[item, ManufacturingColumns.COST_PER_KG_CELL] if item in workbook.index else value
            records.append(
                {
                    CommonColumns.ITEM: item,
                    ManufacturingColumns.COST_PER_KG_CELL: value,
                    AuditColumns.calculated(ManufacturingColumns.COST_PER_KG_CELL): value,
                    AuditColumns.workbook(ManufacturingColumns.COST_PER_KG_CELL): workbook_value,
                    "delta": value - workbook_value,
                }
            )
        return pd.DataFrame(records)
    raise ValueError(f"Unsupported manufacturing kind: {kind}")


def _workbook_cell_material_cost(kind: str) -> pd.DataFrame:
    ws = _ws(kind)
    specs = get_manufacturing_material_cost_specs(kind)
    records = []
    for col in range(specs["first_col"], specs["last_col"] + 1):
        item = ws.cell(specs["header_row"], col).value
        if not _valid(item):
            continue
        records.append(
            {
                CommonColumns.ITEM: _label(item),
                ManufacturingColumns.COST_PER_KG_CELL: _num(ws.cell(specs["value_row"], col).value),
            }
        )
    return pd.DataFrame(records).set_index(CommonColumns.ITEM)


def _material_cost_records(values: dict[str, float], workbook: pd.DataFrame) -> pd.DataFrame:
    records = []
    for item, value in values.items():
        workbook_value = workbook.loc[item, ManufacturingColumns.COST_PER_KG_CELL] if item in workbook.index else value
        records.append(
            {
                CommonColumns.ITEM: item,
                ManufacturingColumns.COST_PER_KG_CELL: value,
                AuditColumns.calculated(ManufacturingColumns.COST_PER_KG_CELL): value,
                AuditColumns.workbook(ManufacturingColumns.COST_PER_KG_CELL): workbook_value,
                "delta": value - workbook_value,
            }
        )
    return pd.DataFrame(records)


def _cell_assembly_parameters(kind: str = "virgin") -> CellAssemblyParameters:
    ws = _ws(kind)
    if kind == "virgin":
        return CellAssemblyParameters(
            annual_cell_energy_kwh=_num(ws["B95"].value),
            accepted_cells_per_year=_num(ws["C95"].value),
            cells_adjusted_for_yield=_num(ws["D95"].value),
            positive_electrode_area_m2=_num(ws["E95"].value),
            negative_electrode_area_m2=_num(ws["F95"].value),
            positive_active_material_kg=_num(ws["G95"].value),
            negative_active_material_kg=_num(ws["H95"].value),
            pvdf_solvent_kg=_num(ws["I95"].value),
            process_cost_ratios=tuple(_num(ws.cell(99, col).value) for col in range(3, 26)),
            direct_labor_hours=tuple(_num(ws.cell(100, col).value) for col in range(3, 26)),
            capital_equipment_millions=tuple(_num(ws.cell(101, col).value) for col in range(3, 26)),
            plant_area_m2=tuple(_num(ws.cell(102, col).value) for col in range(3, 26)),
            throughput_kg_cell_per_year=_num(ws["C8"].value) / _num(ws["H68"].value),
            building_allocation_m2=_num(ws["AC127"].value) + _num(ws["AD127"].value),
        )
    if kind == "recycled":
        return CellAssemblyParameters(
            annual_cell_energy_kwh=_num(ws["AB98"].value),
            accepted_cells_per_year=_num(ws["AC98"].value),
            cells_adjusted_for_yield=_num(ws["AD98"].value),
            positive_electrode_area_m2=_num(ws["AE98"].value),
            negative_electrode_area_m2=_num(ws["AF98"].value),
            positive_active_material_kg=_num(ws["AG98"].value),
            negative_active_material_kg=_num(ws["AH98"].value),
            pvdf_solvent_kg=_num(ws["AI98"].value),
            process_cost_ratios=tuple(_num(ws.cell(102, col).value) for col in range(29, 52)),
            direct_labor_hours=tuple(_num(ws.cell(103, col).value) for col in range(29, 52)),
            capital_equipment_millions=tuple(_num(ws.cell(104, col).value) for col in range(29, 52)),
            plant_area_m2=tuple(_num(ws.cell(105, col).value) for col in range(29, 52)),
            throughput_kg_cell_per_year=_num(ws["AC8"].value) / _num(ws["AQ71"].value) if _num(ws["AQ71"].value) else 0.0,
            building_allocation_m2=_num(workbook_sheet(MAN_PAR_SHEET)["AC127"].value)
            + _num(workbook_sheet(MAN_PAR_SHEET)["AD127"].value),
        )
    raise ValueError(f"Unsupported manufacturing kind: {kind}")


def _cell_capital_equipment_per_kg(params: CellAssemblyParameters) -> float:
    throughput = params.throughput_kg_cell_per_year
    if throughput <= 0:
        return 0.0
    equipment = (
        sum(params.capital_equipment_millions[: params.shared_process_index])
        + params.capital_equipment_millions[params.shared_process_index] * (1.0 - params.shared_process_fraction)
        + sum(params.capital_equipment_millions[params.capital_extra_indices[0] : params.capital_extra_indices[-1] + 1])
    )
    denominator_area = sum(params.plant_area_m2) + params.building_allocation_m2
    if denominator_area:
        equipment += (
            params.capital_equipment_millions[params.capital_shared_index]
            * (sum(params.plant_area_m2) - params.plant_area_m2[params.shared_process_index] * params.shared_process_fraction)
            / denominator_area
        )
    return equipment * 1_000_000 / throughput


def _cell_building_per_kg(params: CellAssemblyParameters, rates: ManufacturingCostRates) -> float:
    throughput = params.throughput_kg_cell_per_year
    if throughput <= 0:
        return 0.0
    area = sum(params.plant_area_m2) - params.plant_area_m2[params.shared_process_index] * params.shared_process_fraction
    return area * rates.building_cost_per_m2 / throughput


def _cell_cost_summary_values(
    *,
    materials: float,
    params: CellAssemblyParameters,
    rates: ManufacturingCostRates,
    include_profit: bool = True,
    include_warranty: bool = True,
) -> dict[str, float]:
    throughput = params.throughput_kg_cell_per_year
    if throughput <= 0:
        return {item: 0.0 for item in _COST_SUMMARY_ITEMS}
    direct_labor = (
        sum(params.direct_labor_hours) - params.direct_labor_hours[params.shared_process_index] * params.shared_process_fraction
    ) * rates.labor_rate_per_hour / throughput
    capital_equipment = _cell_capital_equipment_per_kg(params)
    building = _cell_building_per_kg(params, rates)
    depreciation = capital_equipment * rates.capital_equipment_depreciation_rate + rates.building_depreciation_rate * building
    variable_overhead = direct_labor * rates.variable_overhead_labor_rate + rates.variable_overhead_depreciation_rate * depreciation
    gsa = (direct_labor + variable_overhead) * rates.gsa_labor_overhead_rate + rates.gsa_depreciation_rate * depreciation
    research = depreciation * rates.research_development_rate
    total_variable = materials + direct_labor + variable_overhead
    launch = materials * rates.launch_material_rate + rates.launch_labor_overhead_rate * (direct_labor + variable_overhead)
    working_capital = total_variable * rates.working_capital_rate
    total_investment = launch + working_capital + capital_equipment + building
    profit = total_investment * rates.profit_rate if include_profit else 0.0
    warranty = (materials + direct_labor + depreciation + variable_overhead + gsa + research + profit) * rates.warranty_rate if include_warranty else 0.0
    total = materials + direct_labor + depreciation + variable_overhead + gsa + research + profit + warranty
    return {
        "Materials": materials,
        "Direct labor": direct_labor,
        "Depreciation": depreciation,
        "Variable overhead": variable_overhead,
        "General, sales, administration": gsa,
        "Research and development": research,
        "Total variable": total_variable,
        "Total investment": total_investment,
        "Launch cost": launch,
        "Working capital": working_capital,
        "Capital equipment": capital_equipment,
        "Building": building,
        "Profit": profit,
        "Warranty": warranty,
        "Total": total,
    }


_COST_SUMMARY_ITEMS = (
    "Materials",
    "Direct labor",
    "Depreciation",
    "Variable overhead",
    "General, sales, administration",
    "Research and development",
    "Total variable",
    "Total investment",
    "Launch cost",
    "Working capital",
    "Capital equipment",
    "Building",
    "Profit",
    "Warranty",
    "Total",
)


def manufacturing_cell_cost_summary(kind: str = "virgin") -> pd.DataFrame:
    if kind == "virgin":
        return manufacturing_cell_cost_summary_calculated(kind)[[CommonColumns.ITEM, CommonColumns.VALUE]]
    if kind == "recycled":
        return manufacturing_cell_cost_summary_calculated(kind)[[CommonColumns.ITEM, *RECYCLING_PROCESSES]]
    raise ValueError(f"Unsupported manufacturing kind: {kind}")


def manufacturing_cell_cost_summary_calculated(kind: str = "virgin") -> pd.DataFrame:
    workbook = _workbook_cell_cost_summary(kind)
    params = _cell_assembly_parameters(kind)
    rates = default_manufacturing_cost_rates()
    if kind == "virgin":
        materials = manufacturing_cell_material_cost("virgin").set_index(CommonColumns.ITEM).loc[
            "Total", ManufacturingColumns.COST_PER_KG_CELL
        ]
        values = _cell_cost_summary_values(materials=materials, params=params, rates=rates)
        records = []
        for item in _COST_SUMMARY_ITEMS:
            calculated = values[item]
            workbook_value = workbook.loc[item, CommonColumns.VALUE]
            records.append(
                {
                    CommonColumns.ITEM: item,
                    CommonColumns.VALUE: calculated,
                    AuditColumns.calculated(CommonColumns.VALUE): calculated,
                    AuditColumns.workbook(CommonColumns.VALUE): workbook_value,
                    "delta": calculated - workbook_value,
                }
            )
        return pd.DataFrame(records)
    if kind == "recycled":
        material_costs = manufacturing_cell_material_cost_calculated("recycled")
        non_cathode_materials = material_costs[
            material_costs[CommonColumns.ITEM] != "Active cathode"
        ][ManufacturingColumns.COST_PER_KG_CELL].sum()
        records = []
        for item in _COST_SUMMARY_ITEMS:
            record: dict[str, float | str] = {CommonColumns.ITEM: item}
            for process in RECYCLING_PROCESSES:
                active_cathode = material_costs[
                    (material_costs[CommonColumns.ITEM] == "Active cathode")
                    & (material_costs[CommonColumns.PROCESS] == process)
                ][ManufacturingColumns.COST_PER_KG_CELL].sum()
                values = _cell_cost_summary_values(
                    materials=active_cathode + non_cathode_materials,
                    params=params,
                    rates=rates,
                )
                calculated = values[item]
                record[process] = calculated
                record[AuditColumns.calculated(process)] = calculated
                record[AuditColumns.workbook(process)] = workbook.loc[item, process]
                record[f"{process.lower()}_delta"] = calculated - workbook.loc[item, process]
            records.append(record)
        return pd.DataFrame(records)
    raise ValueError(f"Unsupported manufacturing kind: {kind}")


def _workbook_cell_cost_summary(kind: str) -> pd.DataFrame:
    ws = _ws(kind)
    records = []
    for row in get_manufacturing_cost_summary_rows(kind):
        if kind == "virgin":
            item = ws.cell(row, 2).value
            if _valid(item):
                records.append({CommonColumns.ITEM: _label(item), CommonColumns.VALUE: _num(ws.cell(row, 3).value)})
        else:
            item = ws.cell(row, 28).value
            if _valid(item):
                records.append(
                    {
                        CommonColumns.ITEM: _label(item),
                        "Pyro": _num(ws.cell(row, 29).value),
                        "Hydro": _num(ws.cell(row, 30).value),
                        "Direct": _num(ws.cell(row, 31).value),
                        "Custom": _num(ws.cell(row, 32).value),
                    }
                )
    return pd.DataFrame(records).set_index(CommonColumns.ITEM)


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
    return manufacturing_pack_material_cost_calculated()[
        [CommonColumns.COMPONENT, AuditColumns.calculated("cost_per_pack")]
    ].rename(columns={AuditColumns.calculated("cost_per_pack"): "cost_per_pack"})


def manufacturing_pack_material_cost_calculated() -> pd.DataFrame:
    ws = _ws("virgin")
    workbook = _workbook_pack_material_cost()
    values = {
        "Module conductor/thermal enclosure": (_num(ws["AC22"].value) / 1000 * _num(ws["AC45"].value) + _num(ws["AC60"].value) * _num(ws["AC13"].value)) * _num(ws["AC14"].value),
        "Module management system": (_num(ws["AC13"].value) / _num(ws["AG13"].value) * _num(ws["AC61"].value) + _num(ws["AG14"].value) * _num(ws["AD62"].value)) * _num(ws["AC14"].value),
        "Cell  interconnect": (
            _num(ws["AC19"].value) / 1000 * _num(ws["AC46"].value)
            + ((_num(ws["AC13"].value) / _num(ws["AG13"].value) - 1) * (1 + (_num(ws["AG13"].value) - 1) * 2) + (_num(ws["AG13"].value) - 1) * 2)
            * _num(ws["AC63"].value)
        )
        * _num(ws["AC14"].value),
        "Interconnect panel": (_num(ws["AC20"].value) / 1000 * _num(ws["AC47"].value) + 2 * _num(ws["AC64"].value)) * _num(ws["AC14"].value),
        "Module terminals": (_num(ws["AC21"].value) * 0.5 / 1000 * _num(ws["AC48"].value) + 2 * _num(ws["AC65"].value)) * _num(ws["AC14"].value),
        "Module enclosure": (_num(ws["AC23"].value) / 1000 * _num(ws["AC49"].value) + _num(ws["AC66"].value)) * _num(ws["AC14"].value),
        "Provision for gas release": _num(ws["AC67"].value) * _num(ws["AC14"].value),
        "Row rack": _num(ws["AC28"].value) * _num(ws["AC50"].value) + _num(ws["AC68"].value) * _num(ws["AC15"].value),
        "Polymer pads btw modules": _num(ws["AC15"].value) * (_num(ws["AC14"].value) / _num(ws["AC15"].value) - 1) * _num(ws["AC69"].value),
        "Module interconnect": _num(ws["AC36"].value) * _num(ws["AC52"].value) + _num(ws["AC70"].value) * (_num(ws["AC14"].value) + _num(ws["AC15"].value)),
        "Bus bar": _num(ws["AC37"].value) * _num(ws["AC53"].value) + _num(ws["AC71"].value),
        "Cooling system panel and manifold": (_num(ws["AC30"].value) - 1) * _num(ws["AC54"].value) + _num(ws["AC72"].value) * _num(ws["AC15"].value) * 2 + 9,
        "Pack terminals": _num(ws["AC38"].value) * 0.9 * _num(ws["AC55"].value) + _num(ws["AC73"].value) * 2,
        "Battery jacket, steel": _num(ws["AC33"].value) * _num(ws["AC57"].value) + _num(ws["AC75"].value),
        "Battery jacket, Al": _num(ws["AC32"].value) * _num(ws["AC56"].value) + _num(ws["AC74"].value),
        "Battery jacket, insulation": _num(ws["AC35"].value) / 10 / 0.032 * 3,
        "Battery heating system ($/pack)": _num(ws["AC76"].value),
        "Battery thermal system ($/pack)": _num(ws["AC77"].value),
    }
    records = []
    for component, calculated in values.items():
        workbook_value = workbook.loc[component, "cost_per_pack"]
        records.append(
            {
                CommonColumns.COMPONENT: component,
                "cost_per_pack": calculated,
                AuditColumns.calculated("cost_per_pack"): calculated,
                AuditColumns.workbook("cost_per_pack"): workbook_value,
                "delta": calculated - workbook_value,
            }
        )
    return pd.DataFrame(records)


def _workbook_pack_material_cost() -> pd.DataFrame:
    ws = _ws("virgin")
    records = []
    for col in range(29, 47):
        item = ws.cell(120, col).value
        if _valid(item):
            records.append({CommonColumns.COMPONENT: _label(item), "cost_per_pack": _num(ws.cell(121, col).value)})
    return pd.DataFrame(records).set_index(CommonColumns.COMPONENT)


def _pack_assembly_parameters() -> PackAssemblyParameters:
    ws = _ws("virgin")
    return PackAssemblyParameters(
        material_costs_per_pack=tuple(manufacturing_pack_material_cost()["cost_per_pack"]),
        module_pack_labor_hours=(_num(ws["AC125"].value), _num(ws["AD125"].value)),
        module_pack_capital_equipment_millions=(_num(ws["AC126"].value), _num(ws["AD126"].value)),
        module_pack_plant_area_m2=(_num(ws["AC127"].value), _num(ws["AD127"].value)),
        cell_shared_labor_hours=_num(ws["U100"].value),
        cell_shared_capital_equipment_millions=_num(ws["U101"].value),
        cell_allocated_capital_equipment_millions=_num(ws["V101"].value),
        cell_shared_plant_area_m2=_num(ws["U102"].value),
        total_cell_plant_area_m2=sum(_num(ws.cell(102, col).value) for col in range(3, 26)),
        pack_mass_kg=_num(ws["AE88"].value),
        throughput_kg_cell_per_year=_num(ws["AC8"].value) / _num(ws["H68"].value),
        building_allocation_m2=_num(ws["AC127"].value) + _num(ws["AD127"].value),
        bms_cost_per_pack=_num(ws["AU121"].value),
    )


def _pack_cost_summary_values(params: PackAssemblyParameters, rates: ManufacturingCostRates) -> dict[str, float]:
    throughput = params.throughput_kg_cell_per_year
    if throughput <= 0:
        return {item: 0.0 for item in (*_COST_SUMMARY_ITEMS[:-1], "BMS", "Total")}
    materials = sum(params.material_costs_per_pack) / params.pack_mass_kg if params.pack_mass_kg else 0.0
    direct_labor = (
        sum(params.module_pack_labor_hours) + params.cell_shared_labor_hours * 2.0 / 3.0
    ) * rates.labor_rate_per_hour / throughput
    denominator_area = params.total_cell_plant_area_m2 + params.building_allocation_m2
    cell_shared_equipment = (
        params.cell_allocated_capital_equipment_millions
        * (1.0 - (params.total_cell_plant_area_m2 - params.cell_shared_plant_area_m2 * 2.0 / 3.0) / denominator_area)
        if denominator_area
        else 0.0
    )
    capital_equipment = (sum(params.module_pack_capital_equipment_millions) + params.cell_shared_capital_equipment_millions * 2.0 / 3.0 + cell_shared_equipment) * 1_000_000 / throughput
    building = (sum(params.module_pack_plant_area_m2) + params.cell_shared_plant_area_m2 * 2.0 / 3.0) * rates.building_cost_per_m2 / throughput
    depreciation = capital_equipment * rates.capital_equipment_depreciation_rate + rates.building_depreciation_rate * building
    variable_overhead = direct_labor * rates.variable_overhead_labor_rate + rates.variable_overhead_depreciation_rate * depreciation
    gsa = (variable_overhead + direct_labor) * rates.gsa_labor_overhead_rate + rates.gsa_depreciation_rate * depreciation
    research = depreciation * rates.research_development_rate
    total_variable = materials + direct_labor + variable_overhead
    launch = materials * rates.launch_material_rate + rates.launch_labor_overhead_rate * (variable_overhead + direct_labor)
    working_capital = total_variable * rates.working_capital_rate
    total_investment = launch + working_capital + capital_equipment + building
    profit = total_investment * rates.profit_rate
    warranty = (materials + direct_labor + depreciation + variable_overhead + gsa + research + profit) * rates.warranty_rate
    bms = params.bms_cost_per_pack / params.pack_mass_kg if params.pack_mass_kg else 0.0
    total = materials + direct_labor + depreciation + variable_overhead + gsa + research + profit + warranty + bms
    return {
        "Materials": materials,
        "Direct labor": direct_labor,
        "Depreciation": depreciation,
        "Variable overhead": variable_overhead,
        "General, sales, administration": gsa,
        "Research and development": research,
        "Total variable": total_variable,
        "Total investment": total_investment,
        "Launch cost": launch,
        "Working capital": working_capital,
        "Capital equipment": capital_equipment,
        "Building": building,
        "Profit": profit,
        "Warranty": warranty,
        "BMS": bms,
        "Total": total,
    }


def manufacturing_pack_cost_summary() -> pd.DataFrame:
    return manufacturing_pack_cost_summary_calculated()[[CommonColumns.ITEM, CommonColumns.VALUE]]


def manufacturing_pack_cost_summary_calculated() -> pd.DataFrame:
    workbook = _workbook_pack_cost_summary()
    values = _pack_cost_summary_values(_pack_assembly_parameters(), default_manufacturing_cost_rates())
    records = []
    for item, calculated in values.items():
        workbook_value = workbook.loc[item, CommonColumns.VALUE]
        records.append(
            {
                CommonColumns.ITEM: item,
                CommonColumns.VALUE: calculated,
                AuditColumns.calculated(CommonColumns.VALUE): calculated,
                AuditColumns.workbook(CommonColumns.VALUE): workbook_value,
                "delta": calculated - workbook_value,
            }
        )
    return pd.DataFrame(records)


def _workbook_pack_cost_summary() -> pd.DataFrame:
    ws = _ws("virgin")
    records = []
    for row in range(130, 146):
        item = ws.cell(row, 28).value
        if _valid(item):
            records.append({CommonColumns.ITEM: _label(item), CommonColumns.VALUE: _num(ws.cell(row, 29).value)})
    return pd.DataFrame(records).set_index(CommonColumns.ITEM)


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
