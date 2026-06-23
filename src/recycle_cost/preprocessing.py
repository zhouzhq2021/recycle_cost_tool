from __future__ import annotations

import math
from dataclasses import dataclass

import pandas as pd

from .model import FeedstockInput, Scenario, uses_new_recycling_flow
from .parameters import workbook_number, workbook_sheet
from .schemas import CommonColumns, ManufacturingColumns
from .transport import _num


CHEMISTRIES = ("LCO", "NMC(111)", "NMC(532)", "NMC(622)", "NMC(811)", "NCA", "LMO", "LFP")
FEEDSTOCK_MATERIALS = (
    "Active cathode material",
    "Graphite",
    "Carbon black",
    "Binder: PVDF",
    "Binder: anode",
    "Copper",
    "Aluminum",
    "Electrolyte: LiPF6",
    "Electrolyte: EC",
    "Electrolyte: DMC",
    "Plastic: PP",
    "Plastic: PE",
    "Plastic: PET",
    "Steel",
    "Iron",
    "Electronics",
    "Coolant",
    "Insulation",
)
BLACK_MASS_COMPONENTS = (
    "LCO",
    "NMC(111)",
    "NMC(532)",
    "NMC(622)",
    "NMC(811)",
    "NCA",
    "LMO",
    "LFP",
    "Graphite",
    "Carbon black",
    "Binder: PVDF",
    "Binder: anode",
    "Copper",
    "Aluminum",
    "Steel",
    "Electrolyte: LiPF6",
    "Electrolyte: solvents",
    "Plastics",
)


@dataclass(frozen=True)
class PreprocessingParameters:
    nitrogen_kg_per_kg: float
    diesel_mj_per_kg: float
    natural_gas_mj_per_kg: float
    electricity_mj_per_kg: float
    process_water_gal_per_kg: float
    wastewater_gal_per_kg: float


@dataclass(frozen=True)
class UnitOperationParameters:
    equipment: str
    capacity_adjustment: float
    cost_a: float
    cost_b: float
    cost_c: float
    cost_adjustment: float
    power_m: float
    power_n: float
    power_p: float
    labor_person_hours_per_day: float
    scaling_flag: float


@dataclass(frozen=True)
class PreprocessingPlantParameters:
    hours_per_day: float
    processing_hours_per_day: float
    days_per_year: float
    plant_life_years: float
    regional_cost_factor: float
    labor_rate: float
    capital_charge_rate: float


@dataclass(frozen=True)
class PreprocessingOpexRates:
    electricity_per_kwh: float
    water_per_gal: float
    natural_gas_per_mmbtu: float
    solid_waste_per_tonne: float
    wastewater_per_gal: float
    feedstock_fee_per_kg: float
    nitrogen_per_kg: float


DEFAULT_PREPROCESSING_PARAMETERS = PreprocessingParameters(
    nitrogen_kg_per_kg=0.05,
    diesel_mj_per_kg=0.6,
    natural_gas_mj_per_kg=2.0,
    electricity_mj_per_kg=0.2,
    process_water_gal_per_kg=0.1,
    wastewater_gal_per_kg=0.1 * 3.78541,
)

NEW_PREPROCESSING_PARAMETERS = PreprocessingParameters(
    nitrogen_kg_per_kg=0.015,
    diesel_mj_per_kg=0.2,
    natural_gas_mj_per_kg=0.35,
    electricity_mj_per_kg=0.85,
    process_water_gal_per_kg=0.22,
    wastewater_gal_per_kg=0.22 * 3.78541,
)

DEFAULT_PREPROCESSING_PLANT_PARAMETERS = PreprocessingPlantParameters(
    hours_per_day=24.0,
    processing_hours_per_day=20.0,
    days_per_year=320.0,
    plant_life_years=10.0,
    regional_cost_factor=0.61,
    labor_rate=3.0,
    capital_charge_rate=0.01,
)

GENERIC_PREPROCESSING_EQUIPMENT_NAMES = (
    "Hopper",
    "Conveyor",
    "Crusher",
    "Screen, vibrating",
    "Conveyor",
    "Heat treatment furnace",
    "Cyclone",
    "Conveyor",
    "Eddy current separator",
    "Conveyor",
    "Air classifier",
    "Gas treatment",
    "Wheel loader",
)

NEW_PREPROCESSING_EQUIPMENT_NAMES = (
    "Hopper",
    "Conveyor",
    "Cell Perforation",
    "Flash tank",
    "Supercritical CO2 system",
    "Automated disassembly of battery",
    "Crusher",
    "Screen, vibrating",
    "Density separator",
    "Magnetic separator",
    "Froth flotation cell",
    "Filter press",
    "Dryer",
    "Water treatment",
    "Wheel loader",
)

NEW_PREPROCESSING_EQUIPMENT_ALIASES = {
    "Cell Perforation": "Battery/Cell discharger",
}

NEW_PREPROCESSING_PRODUCT_YIELDS = {
    "cathode_recovery": 0.985,
    "anode_recovery": 0.94,
    "carbon_black_to_anode": 0.75,
    "aluminum_recovery": 0.92,
    "copper_recovery": 0.92,
    "steel_recovery": 0.94,
    "plastics_recovery": 0.88,
    "electrolyte_lipf6_recovery": 0.78,
    "electrolyte_solvent_recovery": 0.82,
    "residual_to_s_cathode": 0.015,
}

PREPROCESSING_OPEX_RATES = PreprocessingOpexRates(
    electricity_per_kwh=0.08838709677419355,
    water_per_gal=0.002,
    natural_gas_per_mmbtu=12.0,
    solid_waste_per_tonne=10.0,
    wastewater_per_gal=0.003,
    feedstock_fee_per_kg=26.9,
    nitrogen_per_kg=0.2975336446534036,
)

PREPROCESSING_ENVIRONMENT_ROWS = (
    ("Total Energy", 0.0, 0.0032468013248182193, 0.0),
    ("Fossil fuels", 0.0, 0.003156755939379061, 0.0),
    ("Coal", 0.0, 0.0028257035566521347, 0.0),
    ("Natural gas", 0.0, 0.0027623361164865147, 0.0),
    ("Petroleum", 0.0, 0.0024976262188470466, 0.0),
    ("Water consumption", 0.0, 0.01565179884259257, 0.1),
    ("VOC", 0.0, 0.06042277639061751, 0.0),
    ("CO", 0.0, 0.25167796813673615, 0.0),
    ("NOx", 0.0, 0.548488247366824, 0.0),
    ("PM10", 0.0, 0.030232010667048885, 0.0),
    ("PM2.5", 0.0, 0.026378433766910354, 0.0),
    ("SOx", 0.0, 0.06196927715186245, 0.0),
    ("BC", 0.0, 0.013553867778739721, 0.0),
    ("OC", 0.0, 0.00688568362296401, 0.0),
    ("CH4", 0.0, 0.550640490249799, 0.0),
    ("N2O", 0.0, 0.006305979617982419, 0.0),
    ("CO2", 0.0, 213.5823513019894, 151.8741932781846),
    ("CO2 w/ C in VOC & CO", 0.0, 214.16616290500264, 151.8741932781846),
    ("GHGs", 0.0, 232.29678195015583, 151.8741932781846),
)

PREPROCESSING_PROCESS_GHG_DEFAULT = 151.8741932781846

PREPROCESSING_PROCESS_GHG_BY_FEEDSTOCK = {
    ("End-of-life battery: pack", "NMC(622)"): 151.8741932781846,
    ("End-of-life battery: pack", "NMC(811)"): 150.919855291703,
    ("End-of-life battery: pack", "NCA"): 150.680977130602,
    ("End-of-life battery: pack", "LFP"): 171.030948684609,
    ("End-of-life battery: module", "NMC(622)"): 217.211386393312,
    ("End-of-life battery: cell", "NMC(622)"): 201.578708682847,
    ("Manufacturing scrap: rejected cells", "NMC(622)"): 201.578708682847,
    ("Manufacturing scrap: electrode", "NMC(622)"): 21.4238628849058,
    ("Manufacturing scrap: electrode", "NMC(811)"): 21.54647667217837,
}


def cm_recovery_black_mass_value(scenario: Scenario) -> float:
    black_mass = preprocessing_black_mass_composition(scenario).set_index(CommonColumns.COMPONENT)
    graphite = black_mass.loc["Graphite", "fraction_of_black_mass"] if "Graphite" in black_mass.index else 0.0
    return graphite * 0.9 * 0.2 / 0.01


def default_preprocessing_parameters() -> PreprocessingParameters:
    return DEFAULT_PREPROCESSING_PARAMETERS


def preprocessing_parameters_for_scenario(scenario: Scenario) -> PreprocessingParameters:
    return NEW_PREPROCESSING_PARAMETERS if uses_new_recycling_flow(scenario) else DEFAULT_PREPROCESSING_PARAMETERS


def default_preprocessing_plant_parameters() -> PreprocessingPlantParameters:
    return DEFAULT_PREPROCESSING_PLANT_PARAMETERS


def default_generic_equipment_names() -> list[str]:
    return list(GENERIC_PREPROCESSING_EQUIPMENT_NAMES)


def preprocessing_equipment_names_for_scenario(scenario: Scenario) -> list[str]:
    return list(NEW_PREPROCESSING_EQUIPMENT_NAMES if uses_new_recycling_flow(scenario) else GENERIC_PREPROCESSING_EQUIPMENT_NAMES)


def unit_operation_table() -> dict[str, UnitOperationParameters]:
    ws = workbook_sheet("Unit Ops")
    rows: dict[str, UnitOperationParameters] = {}
    for row in range(140, 210):
        equipment = ws.cell(row, 2).value
        if equipment is None:
            continue
        rows[str(equipment)] = UnitOperationParameters(
            equipment=str(equipment),
            capacity_adjustment=_num(ws.cell(row, 3).value),
            cost_a=_num(ws.cell(row, 4).value),
            cost_b=_num(ws.cell(row, 5).value),
            cost_c=_num(ws.cell(row, 6).value),
            cost_adjustment=_num(ws.cell(row, 7).value),
            power_m=_num(ws.cell(row, 8).value),
            power_n=_num(ws.cell(row, 9).value),
            power_p=_num(ws.cell(row, 10).value),
            labor_person_hours_per_day=_num(ws.cell(row, 11).value),
            scaling_flag=_num(ws.cell(row, 12).value),
        )
    return rows


def _roundup(value: float, digits: int = 0) -> float:
    factor = 10**digits
    return math.ceil(value * factor) / factor


def preprocessing_equipment_table(scenario: Scenario) -> pd.DataFrame:
    plant = default_preprocessing_plant_parameters()
    unit_ops = unit_operation_table()
    throughput_tpy = preprocessing_throughput(scenario)
    throughput_tph = throughput_tpy / plant.days_per_year / plant.processing_hours_per_day if plant.days_per_year and plant.processing_hours_per_day else 0.0
    records = []
    for name in preprocessing_equipment_names_for_scenario(scenario):
        params = unit_ops.get(NEW_PREPROCESSING_EQUIPMENT_ALIASES.get(name, name))
        if params is None:
            continue
        throughput = throughput_tph * params.capacity_adjustment
        scale = 1.5 if params.scaling_flag == 1 else 0.75
        design_capacity = _roundup(throughput * scale, 1) if throughput > 0 else 0.0
        utilization = throughput / design_capacity if design_capacity else 0.0
        multiplier = 1.0 if params.scaling_flag == 1 else 2.0
        if design_capacity > 0:
            design_power = (params.power_m * design_capacity**params.power_n + params.power_p) * multiplier
            electrical_power = design_power * (1.0 if utilization > 1 else utilization)
            equipment_cost = (
                (params.cost_a * design_capacity**params.cost_b + params.cost_c)
                * params.cost_adjustment
                * multiplier
            )
        else:
            design_power = electrical_power = equipment_cost = 0.0
        records.append(
            {
                "equipment": name,
                "throughput_tonne_per_hr": throughput,
                "design_capacity_tonne_per_hr": design_capacity,
                "utilization": utilization,
                "design_power_kw": design_power,
                "electrical_power_kw": electrical_power,
                "labor_person_hr_per_day": params.labor_person_hours_per_day,
                "equipment_cost": equipment_cost,
            }
        )
    return pd.DataFrame(records)


def preprocessing_capex_summary(scenario: Scenario) -> pd.DataFrame:
    plant = default_preprocessing_plant_parameters()
    equipment = preprocessing_equipment_table(scenario)
    purchased_equipment = float(equipment["equipment_cost"].sum()) * plant.regional_cost_factor if not equipment.empty else 0.0
    equipment_erection = purchased_equipment * 0.5
    piping = purchased_equipment * 0.6
    instrumentation = purchased_equipment * 0.3
    electrical = purchased_equipment * 0.2
    civil = purchased_equipment * 0.3
    structures = purchased_equipment * 0.2
    lagging = purchased_equipment * 0.1
    isbl = purchased_equipment + equipment_erection + piping + instrumentation + electrical + civil + structures + lagging
    osbl = isbl * 0.4
    design_engineering = (isbl + osbl) * 0.25
    contingency = (isbl + design_engineering) * 0.1
    fixed_capital = isbl + osbl + design_engineering + contingency
    rows = [
        ("Purchased Equipment", purchased_equipment),
        ("Equipment erection", equipment_erection),
        ("Piping", piping),
        ("Instrumentation and control", instrumentation),
        ("Electrical", electrical),
        ("Civil", civil),
        ("Structures and buildings", structures),
        ("Lagging and paint", lagging),
        ("ISBL plant cost", isbl),
        ("OSBL cost", osbl),
        ("Design and Engineering Cost", design_engineering),
        ("Contingency", contingency),
        ("Fixed capital investment", fixed_capital),
    ]
    return pd.DataFrame([{CommonColumns.ITEM: item, CommonColumns.VALUE: value} for item, value in rows])


def preprocessing_opex_summary(scenario: Scenario) -> pd.DataFrame:
    plant = default_preprocessing_plant_parameters()
    params = preprocessing_parameters_for_scenario(scenario)
    throughput_tpy = preprocessing_throughput(scenario)
    products = preprocessing_product_outputs(scenario).set_index("product")["kg_per_kg_feedstock"].to_dict()
    capex = preprocessing_capex_summary(scenario).set_index(CommonColumns.ITEM)[CommonColumns.VALUE].to_dict()
    equipment = preprocessing_equipment_table(scenario)
    rates = PREPROCESSING_OPEX_RATES

    electricity_rate = rates.electricity_per_kwh
    water_rate = rates.water_per_gal
    natural_gas_rate = rates.natural_gas_per_mmbtu / 1055
    solid_waste_rate = rates.solid_waste_per_tonne / 1000
    wastewater_rate = rates.wastewater_per_gal

    annual_kg = throughput_tpy * 1000
    annual_kwh = params.electricity_mj_per_kg * annual_kg / 3.6
    utilities = (
        electricity_rate * annual_kwh
        + water_rate * params.process_water_gal_per_kg * annual_kg
        + natural_gas_rate * params.natural_gas_mj_per_kg * annual_kg
    )
    effluent = (
        solid_waste_rate
        * max(products.get("Flue Dust", 0.0) + products.get("Waste (solid)", 0.0), 0.0)
        * annual_kg
        + wastewater_rate * params.wastewater_gal_per_kg / 3.78541 * throughput_tpy
    )

    feedstock_fee = rates.feedstock_fee_per_kg
    raw_materials = max(feedstock_fee, 0.0) * annual_kg
    nitrogen_cost = rates.nitrogen_per_kg * params.nitrogen_kg_per_kg * annual_kg
    raw_materials += nitrogen_cost
    consumerables = raw_materials * 0.03
    packaging = raw_materials * 0.02
    variable_costs = raw_materials + utilities + consumerables + effluent + packaging

    equipment_labor = float(equipment["labor_person_hr_per_day"].sum()) if not equipment.empty else 0.0
    labor_person_hr_per_day = max(equipment_labor, 4.8 * 5 * 8)
    operating_labor = labor_person_hr_per_day * plant.labor_rate * plant.days_per_year
    supervision = operating_labor * 0.25
    direct_salary_overhead = (operating_labor + supervision) * 0.5
    labor_costs = operating_labor + supervision + direct_salary_overhead

    isbl = capex["ISBL plant cost"]
    osbl = capex["OSBL cost"]
    fixed_capital = capex["Fixed capital investment"]
    maintenance = isbl * 0.05
    taxes_insurance = (isbl + osbl) * 0.01
    rent = (isbl + osbl) * 0.02
    plant_overhead_labor = labor_costs * 0.65
    env_charges = (isbl + osbl) * 0.01

    interest_fixed = 0.0 * fixed_capital

    if throughput_tpy > 0:
        annualized_capital = _annualized_capital_cost(fixed_capital, plant.capital_charge_rate, plant.plant_life_years)
        working_capital = variable_costs * 7 / 52 - raw_materials * 2 / 52 + 0.02 * (isbl + osbl)
        interest_working = 0.06 * working_capital
        r_and_d = 0.01 * annual_kg * cm_recovery_black_mass_value(scenario)
        license_fees = 0.01 * (variable_costs + annualized_capital)
        plant_overhead = r_and_d + license_fees + plant_overhead_labor
        fixed_costs = (
            labor_costs
            + maintenance
            + taxes_insurance
            + rent
            + plant_overhead
            + env_charges
            + interest_fixed
            + interest_working
        )
        cash_cost = variable_costs + fixed_costs
        tcop = cash_cost + annualized_capital
    else:
        working_capital = 0.0
        interest_working = 0.0
        r_and_d = 0.0
        license_fees = 0.0
        plant_overhead = 0.0
        fixed_costs = 0.0
        cash_cost = 0.0
        annualized_capital = 0.0
        tcop = 0.0

    records = [
        ("Raw Materials", raw_materials),
        ("Utilities", utilities),
        ("Consumerables", consumerables),
        ("Effluent disposal", effluent),
        ("Packaging and shipping", packaging),
        ("Variable costs of production", variable_costs),
        ("Operating labor", operating_labor),
        ("Supervision and management", supervision),
        ("Direct salary overhead", direct_salary_overhead),
        ("Labor costs", labor_costs),
        ("Maintenance", maintenance),
        ("Property taxes and insurance", taxes_insurance),
        ("Rent of land and/or buildings", rent),
        ("General plant overhead", plant_overhead),
        ("Allocated environmental charges", env_charges),
        ("Running license fees and royalty payments", license_fees),
        ("Interest on fixed capital", interest_fixed),
        ("Interest on working capital", interest_working),
        ("Fixed costs of production", fixed_costs),
        ("Working capital", working_capital),
        ("Cash cost of production", cash_cost),
        ("Annualized capital cost", annualized_capital),
        ("Total cost of production", tcop),
    ]
    return pd.DataFrame([{CommonColumns.ITEM: item, CommonColumns.VALUE: value} for item, value in records])


def _annualized_capital_cost(fixed_capital: float, rate: float, years: float) -> float:
    if fixed_capital <= 0 or rate <= 0 or years <= 0:
        return 0.0
    return rate * (1 + rate) ** years / ((1 + rate) ** years - 1) * fixed_capital


def preprocessing_composition_lookup(feedstock_type: str) -> dict[str, dict[str, float]]:
    ranges = {
        "End-of-life battery: pack": (201, 219),
        "End-of-life battery: module": (222, 240),
        "End-of-life battery: cell": (243, 261),
        "Manufacturing scrap: rejected cells": (243, 261),
        "Manufacturing scrap: electrode": (264, 282),
        "Black mass": (285, 303),
    }
    if feedstock_type not in ranges:
        return {}

    first, last = ranges[feedstock_type]
    ws = workbook_sheet("Preproc. Par.")
    headers = [str(ws.cell(first, col).value) for col in range(3, 11)]
    table: dict[str, dict[str, float]] = {}
    for col, chemistry in zip(range(3, 11), headers, strict=True):
        table[chemistry] = {}
        for row in range(first + 1, last + 1):
            material = ws.cell(row, 2).value
            if material is not None:
                table[chemistry][str(material)] = _num(ws.cell(row, col).value)
    return table


def preprocessing_feedstock_streams(scenario: Scenario) -> pd.DataFrame:
    rows = []
    for item in scenario.feedstocks:
        if item.feedstock_type == "Select Type" or item.feedstock_type == "Black mass":
            tonnes = 0.0
        else:
            tonnes = item.tonnes_per_year
        rows.append(
            {
                CommonColumns.CHEMISTRY: item.chemistry,
                "feedstock_type": item.feedstock_type,
                "tonnes_per_year": tonnes,
            }
        )
    frame = pd.DataFrame(rows)
    if frame.empty:
        return pd.DataFrame(columns=[CommonColumns.CHEMISTRY, "feedstock_type", "tonnes_per_year", "share"])
    total = float(frame["tonnes_per_year"].sum())
    frame["share"] = frame["tonnes_per_year"] / total if total else 0.0
    return frame


def preprocessing_throughput(scenario: Scenario) -> float:
    streams = preprocessing_feedstock_streams(scenario)
    return float(streams["tonnes_per_year"].sum()) if not streams.empty else 0.0


def preprocessing_feedstock_composition(scenario: Scenario) -> pd.DataFrame:
    streams = preprocessing_feedstock_streams(scenario)
    composition = {material: 0.0 for material in FEEDSTOCK_MATERIALS}
    for stream in streams.to_dict("records"):
        lookup = preprocessing_composition_lookup(stream["feedstock_type"]).get(stream[CommonColumns.CHEMISTRY], {})
        for material in FEEDSTOCK_MATERIALS:
            composition[material] += float(stream["share"]) * lookup.get(material, 0.0)

    rows = []
    for material, value in composition.items():
        rows.append({CommonColumns.MATERIAL: material, "kg_per_kg_feedstock": value})
    return pd.DataFrame(rows)


def preprocessing_product_outputs(scenario: Scenario) -> pd.DataFrame:
    params = preprocessing_parameters_for_scenario(scenario)
    composition = preprocessing_feedstock_composition(scenario).set_index(CommonColumns.MATERIAL)["kg_per_kg_feedstock"].to_dict()
    if uses_new_recycling_flow(scenario):
        return _new_preprocessing_product_outputs(composition, params)
    burn_mass = (
        composition.get("Graphite", 0.0)
        + composition.get("Plastic: PP", 0.0)
        + composition.get("Plastic: PE", 0.0)
        + composition.get("Plastic: PET", 0.0)
        + composition.get("Electrolyte: EC", 0.0)
        + composition.get("Electrolyte: DMC", 0.0)
        + composition.get("Binder: PVDF", 0.0)
        + composition.get("Binder: anode", 0.0)
        + composition.get("Copper", 0.0)
        + composition.get("Aluminum", 0.0)
    )
    products = {
        "Black mass": (
            composition.get("Active cathode material", 0.0)
            + composition.get("Graphite", 0.0)
            + composition.get("Carbon black", 0.0)
        )
        * 0.95
        + (
            composition.get("Binder: PVDF", 0.0)
            + composition.get("Binder: anode", 0.0)
            + composition.get("Copper", 0.0)
            + composition.get("Aluminum", 0.0)
        )
        * 0.05,
        "Aluminum": composition.get("Aluminum", 0.0) * 0.9,
        "Copper": composition.get("Copper", 0.0) * 0.9,
        "Steel": composition.get("Steel", 0.0) * 0.9,
        "Flue Dust": burn_mass * 0.02,
    }
    products["Waste (solid)"] = (
        1
        + params.nitrogen_kg_per_kg
        - sum(products.values())
        - burn_mass * 0.98
    )
    products["Waste(water)"] = params.wastewater_gal_per_kg
    return pd.DataFrame(
        [{"product": product, "kg_per_kg_feedstock": value} for product, value in products.items()]
    )


def _new_preprocessing_product_outputs(
    composition: dict[str, float],
    params: PreprocessingParameters,
) -> pd.DataFrame:
    yields = NEW_PREPROCESSING_PRODUCT_YIELDS
    plastics = composition.get("Plastic: PP", 0.0) + composition.get("Plastic: PE", 0.0) + composition.get("Plastic: PET", 0.0)
    electrolyte_solvents = composition.get("Electrolyte: EC", 0.0) + composition.get("Electrolyte: DMC", 0.0)
    residual_binders = composition.get("Binder: PVDF", 0.0) + composition.get("Binder: anode", 0.0)
    products = {
        "S-Cathode": (
            composition.get("Active cathode material", 0.0) * yields["cathode_recovery"]
            + composition.get("Carbon black", 0.0) * (1 - yields["carbon_black_to_anode"])
            + residual_binders * yields["residual_to_s_cathode"]
        ),
        "S-Anode": (
            composition.get("Graphite", 0.0) * yields["anode_recovery"]
            + composition.get("Carbon black", 0.0) * yields["carbon_black_to_anode"]
        ),
        "Aluminum": composition.get("Aluminum", 0.0) * yields["aluminum_recovery"],
        "Copper": composition.get("Copper", 0.0) * yields["copper_recovery"],
        "Steel": (composition.get("Steel", 0.0) + composition.get("Iron", 0.0)) * yields["steel_recovery"],
        "Plastics": plastics * yields["plastics_recovery"],
        "Battery electrolyte": (
            composition.get("Electrolyte: LiPF6", 0.0) * yields["electrolyte_lipf6_recovery"]
            + electrolyte_solvents * yields["electrolyte_solvent_recovery"]
        ),
        "Waste(water)": params.wastewater_gal_per_kg,
    }
    accounted = sum(value for product, value in products.items() if product != "Waste(water)")
    products["Waste (solid)"] = max(0.0, 1 + params.nitrogen_kg_per_kg - accounted)
    return pd.DataFrame(
        [{"product": product, "kg_per_kg_feedstock": value} for product, value in products.items()]
    )


def preprocessing_black_mass_composition(scenario: Scenario) -> pd.DataFrame:
    black_mass_throughput = sum(f.tonnes_per_year for f in scenario.feedstocks if f.feedstock_type == "Black mass")
    
    if black_mass_throughput > 0 and preprocessing_throughput(scenario) == 0:
        composition = {material: 0.0 for material in BLACK_MASS_COMPONENTS}
        for f in scenario.feedstocks:
            if f.feedstock_type == "Black mass":
                lookup = preprocessing_composition_lookup("Black mass").get(f.chemistry, {})
                share = f.tonnes_per_year / black_mass_throughput
                for material in BLACK_MASS_COMPONENTS:
                    if material == f.chemistry:
                        composition[material] += share * lookup.get("Active cathode material", 0.0)
                    else:
                        composition[material] += share * lookup.get(material, 0.0)
        
        rows = []
        for component in BLACK_MASS_COMPONENTS:
            rows.append({CommonColumns.COMPONENT: component, "fraction_of_black_mass": composition[component]})
        return pd.DataFrame(rows)

    streams = preprocessing_feedstock_streams(scenario)
    composition = preprocessing_feedstock_composition(scenario).set_index(CommonColumns.MATERIAL)["kg_per_kg_feedstock"].to_dict()
    product_row = preprocessing_product_outputs(scenario).set_index("product")
    if uses_new_recycling_flow(scenario):
        product_mass = product_row.loc["S-Cathode", "kg_per_kg_feedstock"] if "S-Cathode" in product_row.index else 0.0
    else:
        product_mass = product_row.loc["Black mass", "kg_per_kg_feedstock"] if "Black mass" in product_row.index else 0.0
    values = {material: 0.0 for material in BLACK_MASS_COMPONENTS}

    if uses_new_recycling_flow(scenario):
        values["Carbon black"] = composition.get("Carbon black", 0.0) * (1 - NEW_PREPROCESSING_PRODUCT_YIELDS["carbon_black_to_anode"])
        residual_binders = composition.get("Binder: PVDF", 0.0) + composition.get("Binder: anode", 0.0)
        values["Binder: PVDF"] = residual_binders * NEW_PREPROCESSING_PRODUCT_YIELDS["residual_to_s_cathode"]
    else:
        values["Graphite"] = composition.get("Graphite", 0.0) * 0.95
        values["Carbon black"] = composition.get("Carbon black", 0.0) * 0.95
        values["Binder: PVDF"] = composition.get("Binder: PVDF", 0.0) * 0.05
        values["Binder: anode"] = composition.get("Binder: anode", 0.0) * 0.05
        values["Copper"] = composition.get("Copper", 0.0) * 0.05
        values["Aluminum"] = composition.get("Aluminum", 0.0) * 0.05

    for stream in streams.to_dict("records"):
        chem = stream[CommonColumns.CHEMISTRY]
        if chem in CHEMISTRIES:
            lookup = preprocessing_composition_lookup(stream["feedstock_type"]).get(chem, {})
            active = lookup.get("Active cathode material", 0.0)
            recovery = NEW_PREPROCESSING_PRODUCT_YIELDS["cathode_recovery"] if uses_new_recycling_flow(scenario) else 0.95
            values[chem] += float(stream["share"]) * active * recovery

    rows = []
    for component in BLACK_MASS_COMPONENTS:
        value = values[component] / product_mass if product_mass else 0.0
        rows.append({CommonColumns.COMPONENT: component, "fraction_of_black_mass": value})
    return pd.DataFrame(rows)


def preprocessing_environment_summary(scenario: Scenario) -> pd.DataFrame:
    throughput = preprocessing_throughput(scenario)
    process_ghg = preprocessing_process_ghg_value(scenario) if throughput > 0 else 0.0
    params = preprocessing_parameters_for_scenario(scenario)
    rows = []
    for metric, material, energy, process in PREPROCESSING_ENVIRONMENT_ROWS:
        material_input = material if throughput > 0 else 0.0
        energy_input = energy
        process_value = process
        if uses_new_recycling_flow(scenario):
            if metric in {"Total Energy", "Fossil fuels"}:
                energy_input = params.electricity_mj_per_kg + params.natural_gas_mj_per_kg + params.diesel_mj_per_kg
            elif metric == "Natural gas":
                energy_input = params.natural_gas_mj_per_kg
            elif metric == "Petroleum":
                energy_input = params.diesel_mj_per_kg
            elif metric == "Water consumption":
                process_value = params.process_water_gal_per_kg
            elif metric == "CO2":
                process_value = process_ghg
            elif metric == "CO2 w/ C in VOC & CO":
                process_value = process_ghg
            elif metric == "GHGs":
                process_value = process_ghg
        if metric in {"CO2", "CO2 w/ C in VOC & CO", "GHGs"}:
            process_value = process_ghg
        rows.append(
            {
                CommonColumns.METRIC: metric,
                "material_input": material_input,
                "energy_input": energy_input,
                "process": process_value,
                ManufacturingColumns.TOTAL: material_input + energy_input + process_value,
            }
        )
    return pd.DataFrame(rows)


def preprocessing_process_ghg_value(scenario: Scenario) -> float:
    if uses_new_recycling_flow(scenario):
        params = preprocessing_parameters_for_scenario(scenario)
        # Electricity-heavy pretreatment with limited thermal destruction.
        return params.electricity_mj_per_kg / 3.6 * 0.45 + params.natural_gas_mj_per_kg * 56.1 + params.diesel_mj_per_kg * 74.1
    streams = preprocessing_feedstock_streams(scenario)
    if streams.empty:
        return 0.0
    weighted = 0.0
    for stream in streams.to_dict("records"):
        feedstock_type = str(stream["feedstock_type"])
        chemistry = str(stream[CommonColumns.CHEMISTRY])
        value = PREPROCESSING_PROCESS_GHG_BY_FEEDSTOCK.get(
            (feedstock_type, chemistry),
            PREPROCESSING_PROCESS_GHG_DEFAULT,
        )
        weighted += float(stream["share"]) * value
    return weighted


def preprocessing_cost_summary(scenario: Scenario) -> pd.DataFrame:
    throughput = preprocessing_throughput(scenario)
    capex = preprocessing_capex_summary(scenario).set_index(CommonColumns.ITEM)[CommonColumns.VALUE].to_dict()
    opex = preprocessing_opex_summary(scenario).set_index(CommonColumns.ITEM)[CommonColumns.VALUE].to_dict()

    fixed_capital = capex.get("Fixed capital investment", 0.0)
    working_capital = opex.get("Working capital", 0.0)
    
    feedstock_fee_per_kg = PREPROCESSING_OPEX_RATES.feedstock_fee_per_kg

    rows = [
        ("Total capital investment ($)", fixed_capital + working_capital),
        ("Fixed capital investment ($)", fixed_capital),
        ("Working capital ($)", working_capital),
        ("Variable costs of production ($/yr)", opex.get("Variable costs of production", 0.0)),
        ("Fixed costs of production ($/yr)", opex.get("Fixed costs of production", 0.0)),
        ("Cash cost of production ($/yr)", opex.get("Cash cost of production", 0.0)),
        ("Annualized capital cost ($/yr)", opex.get("Annualized capital cost", 0.0)),
        ("Feedstock fee ($/kg feedstock)", feedstock_fee_per_kg),
    ]
    
    records = [{CommonColumns.ITEM: item, CommonColumns.VALUE: value} for item, value in rows]
    total_cost = 0.0
    if throughput > 0:
        total_cost = (opex.get("Cash cost of production", 0.0) + opex.get("Annualized capital cost", 0.0)) / throughput / 1000
        if feedstock_fee_per_kg < 0:
            total_cost += feedstock_fee_per_kg
    
    records.append({CommonColumns.ITEM: "Total cost ($/kg feedstock processed)", CommonColumns.VALUE: total_cost})
    return pd.DataFrame(records)


def preprocessing_workbook_snapshot() -> dict[str, float]:
    return {
        "throughput_tonnes_per_year": workbook_number("Preproc. Par.", "D8"),
        "generic_black_mass_kg_per_kg": workbook_number("Preproc. Par.", "AC102"),
        "generic_total_energy": workbook_number("Preproc. Par.", "AD155"),
        "generic_ghgs": workbook_number("Preproc. Par.", "AD174"),
        "generic_total_cost": workbook_number("Preproc. Par.", "AC195"),
    }
