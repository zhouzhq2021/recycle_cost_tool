from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .custom_chemistry import CUSTOM_NMC_LABEL, NMC_CATHODE_MATERIALS, custom_nmc_elemental_mass, is_custom_nmc
from .model import Scenario, default_scenario, uses_new_recycling_flow
from .new_flow_parameters import new_flow_parameter_value
from .preprocessing import (
    unit_operation_table,
    _roundup,
    _annualized_capital_cost,
    preprocessing_black_mass_composition,
    preprocessing_throughput,
    preprocessing_product_outputs
)
from .parameters import regional_cost_factor
from .schemas import CommonColumns

ELEMENTAL_MASS = {
    "LCO": {"Li": 6.94, "Co": 58.933, "Ni": 0, "Mn": 0, "O": 31.998, "P": 0, "F": 0, "Al": 0, "Fe": 0, "Total": 97.871},
    "NMC(111)": {"Li": 6.94, "Co": 19.644333333333332, "Ni": 19.56433333333333, "Mn": 18.312666666666665, "O": 31.998, "P": 0, "F": 0, "Al": 0, "Fe": 0, "Total": 96.45933333333333},
    "NMC(532)": {"Li": 6.94, "Co": 11.7866, "Ni": 29.3465, "Mn": 16.4814, "O": 31.998, "P": 0, "F": 0, "Al": 0, "Fe": 0, "Total": 96.5525},
    "NMC(622)": {"Li": 6.94, "Co": 11.7866, "Ni": 35.215799999999994, "Mn": 10.9876, "O": 31.998, "P": 0, "F": 0, "Al": 0, "Fe": 0, "Total": 96.928},
    "NMC(811)": {"Li": 6.94, "Co": 5.8933, "Ni": 46.9544, "Mn": 5.4938, "O": 31.998, "P": 0, "F": 0, "Al": 0, "Fe": 0, "Total": 97.2795},
    CUSTOM_NMC_LABEL: {"Li": 6.94, "Co": 11.7866, "Ni": 35.215799999999994, "Mn": 10.9876, "O": 31.998, "P": 0, "F": 0, "Al": 0, "Fe": 0, "Total": 96.928},
    "NCA": {"Li": 6.94, "Co": 8.83995, "Ni": 46.9544, "Mn": 0, "O": 31.998, "P": 0, "F": 0, "Al": 1.3491, "Fe": 0, "Total": 96.08144999999999},
    "LMO": {"Li": 6.94, "Co": 0, "Ni": 0, "Mn": 109.876, "O": 63.996, "P": 0, "F": 0, "Al": 0, "Fe": 0, "Total": 180.812},
    "LFP": {"Li": 6.94, "Co": 0, "Ni": 0, "Mn": 0, "O": 63.996, "P": 30.974, "F": 0, "Al": 0, "Fe": 55.845, "Total": 157.755},
    "LiPF6": {"Li": 6.94, "Co": 0, "Ni": 0, "Mn": 0, "O": 0, "P": 30.974, "F": 113.988, "Al": 0, "Fe": 0, "Total": 151.902},
}

@dataclass(frozen=True)
class CMRecoveryPlantParameters:
    days_per_year: float
    processing_hours_per_day: float
    plant_life_years: float
    regional_cost_factor: float
    labor_rate: float
    capital_charge_rate: float


@dataclass(frozen=True)
class CMRecoveryOpexBaselineCosts:
    utilities: float
    effluent: float
    raw_materials: float


@dataclass(frozen=True)
class CMRecoveryThroughputParameters:
    material_flow_tpy: float
    routed_tpy: float
    cost_design_tpy: float


CM_RECOVERY_BASELINE_THROUGHPUT_TPY = 10000.0
CM_RECOVERY_LABOR_RATE = 3.0
CM_RECOVERY_CAPITAL_CHARGE_RATE = 0.01

CM_RECOVERY_PROCESS_PARAMETERS = {
    "Pyro": {"days_per_year": 360.0, "processing_hours_per_day": 30.0, "plant_life_years": 10.0},
    "Hydro": {"days_per_year": 365.0, "processing_hours_per_day": 30.0, "plant_life_years": 10.0},
    "Direct": {"days_per_year": 360.0, "processing_hours_per_day": 30.0, "plant_life_years": 10.0},
    "Custom": {"days_per_year": 24.0, "processing_hours_per_day": 24.0, "plant_life_years": 320.0},
}

NEW_CM_RECOVERY_PROCESS_PARAMETERS = {
    "Hydro": {"days_per_year": 365.0, "processing_hours_per_day": 30.0, "plant_life_years": 10.0},
    "Direct": {"days_per_year": 360.0, "processing_hours_per_day": 30.0, "plant_life_years": 10.0},
}

CM_RECOVERY_OPEX_BASELINE_COSTS = {
    "Pyro": CMRecoveryOpexBaselineCosts(
        utilities=5020028.436018958,
        effluent=83920.72768141015,
        raw_materials=25955975.73829582,
    ),
    "Hydro": CMRecoveryOpexBaselineCosts(
        utilities=4186847.709320695,
        effluent=110803.950386937,
        raw_materials=35463116.38281767,
    ),
    "Direct": CMRecoveryOpexBaselineCosts(
        utilities=853333.3333333333,
        effluent=43021.90496317933,
        raw_materials=49502460.679558605,
    ),
    "Custom": CMRecoveryOpexBaselineCosts(
        utilities=797777.7777777778,
        effluent=12125.220458553791,
        raw_materials=43285565.535645,
    ),
}

CM_RECOVERY_FEED_COSTS = {
    "Pyro": 2.3,
    "Hydro": 2.56,
    "Direct": 3.14,
    "Custom": 3.0,
}

CM_RECOVERY_PRODUCT_PRICES = {
    "Aluminum": 1.1174777856,
    "Copper": 7.111619103599999,
    "Steel": 0.3272,
    "Plastics": 0.2,
    "LCO": 50.0,
    "NMC(111)": 25.5,
    "NMC(532)": 24.0,
    "NMC(622)": 25.0,
    "NMC(811)": 26.0,
    "Lithium carbonate (crude)": 8.57,
    "Ni2+ in product": 16.853,
    "Co2+ in product": 50.3535208,
    "Mn2+ in product": 3.1492555776,
    "LMO": 9.0,
    "NCA": 26.0,
    "LFP": 10.0,
    "Rejuvenated LCO": 50.0,
    "Rejuvenated NMC(111)": 25.5,
    "Rejuvenated NMC(532)": 24.0,
    "Rejuvenated NMC(622)": 25.0,
    "Rejuvenated NMC(811)": 26.0,
    "Rejuvenated NCA": 26.0,
    "Rejuvenated LMO": 9.0,
    "Rejuvenated LFP": 10.0,
    f"Rejuvenated {CUSTOM_NMC_LABEL}": 25.0,
    CUSTOM_NMC_LABEL: 25.0,
    "Electrolyte: solvents": 0.15,
    "Graphite": 0.2,
    "Copper metal": 7.366517267999999,
}

CM_RECOVERY_EQUIPMENT_ROWS = {
    "Pyro": (
        (399, "Hopper"),
        (400, "Conveyor"),
        (401, "Smelter"),
        (402, "Gas treatment"),
        (403, "Conveyor"),
        (404, "Granulator"),
        (405, "Leaching tank"),
        (406, "Solvent extraction unit"),
        (407, "Electrowinning cell"),
        (408, "Solvent extraction unit"),
        (409, "Solvent extraction unit"),
        (410, "Wheel loader"),
        (411, "Water treatment"),
    ),
    "Hydro": (
        (399, "Conveyor"),
        (400, "Leaching tank"),
        (401, "Mixing tank"),
        (402, "Filter press"),
        (403, "Solvent extraction unit"),
        (404, "Solvent extraction unit"),
        (405, "Solvent extraction unit"),
        (406, "Evaporator"),
        (407, "Precipitation tank"),
        (408, "Centrifuge"),
        (409, "Dryer"),
        (410, "Water treatment"),
        (411, "Wheel loader"),
    ),
    "Direct": (
        (399, "Conveyor"),
        (400, "Froth flotation cell"),
        (401, "Filter press"),
        (402, "Froth flotation cell"),
        (403, "Filter press"),
        (404, "Dryer"),
        (405, "Ball mill"),
        (406, "Furnace+saggar handling system"),
        (407, "Water treatment"),
        (408, "Wheel loader"),
    ),
    "Custom": (
        (399, "Conveyor"),
        (400, "Leaching tank"),
        (401, "Mixing tank"),
        (402, "Filter press"),
        (403, "Solvent extraction unit"),
        (404, "Solvent extraction unit"),
        (405, "Solvent extraction unit"),
        (406, "Evaporator"),
        (407, "Precipitation tank"),
        (408, "Centrifuge"),
        (409, "Dryer"),
        (410, "Water treatment"),
        (411, "Wheel loader"),
    ),
}

NEW_CM_RECOVERY_EQUIPMENT_ROWS = {
    "Hydro": (
        (399, "Conveyor"),
        (400, "Leaching tank"),
        (401, "Mixing tank"),
        (402, "Filter press"),
        (403, "Membrane separator"),
        (404, "Solvent extraction unit"),
        (405, "Precipitation tank"),
        (406, "Crystallizer"),
        (407, "Centrifuge"),
        (408, "Dryer"),
        (409, "Calciner"),
        (410, "Water treatment"),
        (411, "Wheel loader"),
    ),
    "Direct": (
        (399, "Conveyor"),
        (400, "Ball mill"),
        (401, "Furnace+saggar handling system"),
        (402, "Ultrasonic bath"),
        (403, "Filter press"),
        (404, "Hydrocyclone"),
        (405, "Calciner"),
        (406, "Dryer"),
        (407, "Water treatment"),
        (408, "Wheel loader"),
    ),
}

CM_RECOVERY_PRODUCT_SOURCE_ROWS = {
    "Pyro": {
        "copper metal": 127,
        "co2+ in product": 128,
        "ni2+ in product": 129,
    },
    "Hydro": {
        "lithium carbonate (crude)": 126,
        "co2+ in product": 127,
        "ni2+ in product": 128,
        "mn2+ in product": 129,
        "graphite": 130,
    },
    "Direct": {
        "copper": 126,
        "aluminum": 128,
        "nmc(622)": 129,
        "graphite": 131,
    },
    "Custom": {
        "nmc(622)": 128,
        "co2+ in product": 129,
        "ni2+ in product": 130,
        "mn2+ in product": 131,
        "graphite": 132,
        "aluminum": 133,
        "copper": 134,
    },
}

CM_RECOVERY_NMC622_PRODUCT_OVERRIDES = {
    "Pyro": {
        "Copper metal": 0.005,
        "Co2+ in product": 0.122,
        "Ni2+ in product": 0.122,
    },
    "Hydro": {
        "Co2+ in product": 0.126,
        "Ni2+ in product": 0.126,
        "Mn2+ in product": 0.118,
        "Graphite": 0.309,
    },
    "Direct": {
        "Copper": 0.005,
        "Aluminum": 0.003,
        "NMC(622)": 0.57,
        "Graphite": 0.309,
    },
}


def default_cm_recovery_plant_parameters(scenario: Scenario, process: str) -> CMRecoveryPlantParameters:
    params = (
        NEW_CM_RECOVERY_PROCESS_PARAMETERS.get(process)
        if uses_new_recycling_flow(scenario)
        else None
    ) or CM_RECOVERY_PROCESS_PARAMETERS.get(process, CM_RECOVERY_PROCESS_PARAMETERS["Pyro"])
    return CMRecoveryPlantParameters(
        days_per_year=params["days_per_year"],
        processing_hours_per_day=params["processing_hours_per_day"],
        plant_life_years=params["plant_life_years"],
        regional_cost_factor=regional_cost_factor(scenario.manufacturing_location),
        labor_rate=CM_RECOVERY_LABOR_RATE,
        capital_charge_rate=CM_RECOVERY_CAPITAL_CHARGE_RATE,
    )

def cm_recovery_throughput(scenario: Scenario) -> float:
    return cm_recovery_throughput_parameters(scenario).routed_tpy


def cm_recovery_throughput_parameters(scenario: Scenario) -> CMRecoveryThroughputParameters:
    if scenario.feedstocks and all(s.feedstock_type == "Black mass" for s in scenario.feedstocks):
        routed_tpy = sum(s.tonnes_per_year for s in scenario.feedstocks)
        return CMRecoveryThroughputParameters(
            material_flow_tpy=routed_tpy,
            routed_tpy=routed_tpy,
            cost_design_tpy=routed_tpy,
        )
    
    preproc_throughput = preprocessing_throughput(scenario)
    if preproc_throughput == 0:
        return CMRecoveryThroughputParameters(material_flow_tpy=0.0, routed_tpy=0.0, cost_design_tpy=0.0)
    
    products = preprocessing_product_outputs(scenario).set_index("product")
    if uses_new_recycling_flow(scenario) and "S-Cathode" in products.index:
        material_flow_tpy = preproc_throughput * products.loc["S-Cathode", "kg_per_kg_feedstock"]
        return CMRecoveryThroughputParameters(
            material_flow_tpy=material_flow_tpy,
            routed_tpy=preproc_throughput,
            cost_design_tpy=max(preproc_throughput, CM_RECOVERY_BASELINE_THROUGHPUT_TPY),
        )
    if "Black mass" in products.index:
        material_flow_tpy = preproc_throughput * products.loc["Black mass", "kg_per_kg_feedstock"]
        cost_design_tpy = max(preproc_throughput, CM_RECOVERY_BASELINE_THROUGHPUT_TPY)
        return CMRecoveryThroughputParameters(
            material_flow_tpy=material_flow_tpy,
            routed_tpy=preproc_throughput,
            cost_design_tpy=cost_design_tpy,
        )
    return CMRecoveryThroughputParameters(
        material_flow_tpy=0.0,
        routed_tpy=preproc_throughput,
        cost_design_tpy=max(preproc_throughput, CM_RECOVERY_BASELINE_THROUGHPUT_TPY),
    )

def cm_recovery_equipment_table(scenario: Scenario, process: str) -> pd.DataFrame:
    plant = default_cm_recovery_plant_parameters(scenario, process)
    unit_ops = unit_operation_table()
    throughput_tpy = cm_recovery_throughput_parameters(scenario).routed_tpy
    throughput_tph_base = throughput_tpy / plant.days_per_year / plant.processing_hours_per_day if plant.days_per_year and plant.processing_hours_per_day else 0.0
    
    # Get composition for fractional scaling
    bm = preprocessing_black_mass_composition(scenario).set_index(CommonColumns.COMPONENT)["fraction_of_black_mass"]
    cu = bm.get("Copper", 0.0)
    al = bm.get("Aluminum", 0.0)
    element_mass = _elemental_mass_for_scenario(scenario)
    co = sum(bm.get(chem, 0.0) * element_mass[chem]["Co"] / element_mass[chem]["Total"] for chem in element_mass if chem != "LiPF6")
    ni = sum(bm.get(chem, 0.0) * element_mass[chem]["Ni"] / element_mass[chem]["Total"] for chem in element_mass if chem != "LiPF6")
    cathode_sum = sum(bm.get(chem, 0.0) for chem in NMC_CATHODE_MATERIALS)
    graphite_sum = bm.get("Graphite", 0.0)
    carbon_black = bm.get("Carbon black", 0.0)
    
    records = []
    equipment_rows = (
        NEW_CM_RECOVERY_EQUIPMENT_ROWS.get(process)
        if uses_new_recycling_flow(scenario)
        else None
    ) or CM_RECOVERY_EQUIPMENT_ROWS.get(process, CM_RECOVERY_EQUIPMENT_ROWS["Pyro"])
    for row, name in equipment_rows:
        params = unit_ops.get(name)
        if params is None:
            continue
            
        throughput_multiplier = 1.0
        if process == "Pyro":
            # Row-specific scaling based on workbook formulas
            if row == 405: # Leaching: Cu+Ni+Co
                throughput_multiplier = cu + ni + co
            elif row == 406: # SEU: Cu+Ni+Co
                throughput_multiplier = cu + ni + co
            elif row == 407: # EW: Cu
                throughput_multiplier = cu
            elif row == 408: # SEU: Ni+Co
                throughput_multiplier = ni + co
            elif row == 409: # SEU: Ni
                throughput_multiplier = ni
        elif process == "Direct":
            active_outputs = sum(
                1
                for chem in NMC_CATHODE_MATERIALS
                if bm.get(chem, 0.0) > 0
            )
            output_count = max(
                1,
                int(cu > 0) + int(al > 0) + active_outputs,
            )
            active_sum = cathode_sum
            if row == 400:
                throughput_multiplier = (active_sum + graphite_sum) / 0.05
            elif row == 401:
                throughput_multiplier = graphite_sum + carbon_black
            elif row == 402:
                throughput_multiplier = active_sum / 0.15
            elif row in (403, 404, 405):
                throughput_multiplier = active_sum / output_count
            elif row == 406:
                throughput_multiplier = active_sum
                
        throughput = throughput_tph_base * params.capacity_adjustment * throughput_multiplier
        
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
            if process == "Direct":
                if row == 402:
                    equipment_cost *= max(output_count - 1, 0)
                elif row in (403, 404, 405):
                    equipment_cost *= output_count
                elif row == 406:
                    annual_design_tonnes = (
                        design_capacity * plant.processing_hours_per_day * plant.days_per_year
                    )
                    equipment_cost *= _roundup(annual_design_tonnes / 4000.0, 0)
        else:
            design_power = electrical_power = equipment_cost = 0.0
            
        records.append(
            {
                "equipment": str(name),
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

def cm_recovery_capex_summary(scenario: Scenario, process: str) -> pd.DataFrame:
    plant = default_cm_recovery_plant_parameters(scenario, process)
    equipment = cm_recovery_equipment_table(scenario, process)
    purchased_equipment = float(equipment["equipment_cost"].sum()) * plant.regional_cost_factor if not equipment.empty else 0.0
    
    # Standard multipliers
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

def cm_recovery_opex_summary(scenario: Scenario, process: str) -> pd.DataFrame:
    plant = default_cm_recovery_plant_parameters(scenario, process)
    throughput_tpy = cm_recovery_throughput_parameters(scenario).routed_tpy
    capex = cm_recovery_capex_summary(scenario, process).set_index(CommonColumns.ITEM)[CommonColumns.VALUE].to_dict()
    equipment = cm_recovery_equipment_table(scenario, process)
    annual_kg = throughput_tpy * 1000

    baseline_costs = (
        CMRecoveryOpexBaselineCosts(
            utilities=new_flow_parameter_value(scenario, "cm_utilities_usd_per_year", CM_RECOVERY_OPEX_BASELINE_COSTS[process].utilities),
            effluent=new_flow_parameter_value(scenario, "cm_effluent_usd_per_year", CM_RECOVERY_OPEX_BASELINE_COSTS[process].effluent),
            raw_materials=new_flow_parameter_value(scenario, "cm_raw_materials_usd_per_year", CM_RECOVERY_OPEX_BASELINE_COSTS[process].raw_materials),
        )
        if uses_new_recycling_flow(scenario) and process in {"Hydro", "Direct"}
        else CM_RECOVERY_OPEX_BASELINE_COSTS.get(process, CM_RECOVERY_OPEX_BASELINE_COSTS["Pyro"])
    )
    throughput_scale = throughput_tpy / CM_RECOVERY_BASELINE_THROUGHPUT_TPY if throughput_tpy > 0 else 0.0
    utility_effluent_scale = 1.0 if process == "Direct" and throughput_tpy > 0 else throughput_scale
    utilities = baseline_costs.utilities * utility_effluent_scale
    effluent = baseline_costs.effluent * utility_effluent_scale
    raw_materials = baseline_costs.raw_materials * throughput_scale
    
    consumerables = raw_materials * 0.03
    packaging = raw_materials * 0.02
    variable_costs = raw_materials + utilities + consumerables + effluent + packaging
    
    # Labor
    equipment_labor = float(equipment["labor_person_hr_per_day"].sum()) if not equipment.empty else 0.0
    # Operating labor calculation uses 192 hour baseline (4.8*5*8)
    operating_labor = max(equipment_labor, 192.0) * plant.labor_rate * plant.days_per_year
    supervision = operating_labor * 0.25
    direct_salary_overhead = (operating_labor + supervision) * 0.5
    labor_costs = operating_labor + supervision + direct_salary_overhead
    
    isbl = capex["ISBL plant cost"]
    osbl = capex["OSBL cost"]
    fixed_capital = capex["Fixed capital investment"]
    
    maintenance = isbl * 0.05
    taxes_insurance = (isbl + osbl) * 0.01
    rent = (isbl + osbl) * 0.02
    gna = labor_costs * 0.65
    env_charges = (isbl + osbl) * 0.01
    interest_fixed = 0.0
    revenue_basis = cm_recovery_revenue_per_kg_feed(scenario, process) * annual_kg
    rnd = 0.01 * revenue_basis
    
    k1 = 7 / 52
    k2 = -raw_materials * 2 / 52 + 0.02 * (isbl + osbl)
    fcop_base = labor_costs + maintenance + taxes_insurance + rent + rnd + gna + env_charges + interest_fixed
    
    annualized_capital = _annualized_capital_cost(fixed_capital, plant.capital_charge_rate, plant.plant_life_years)
    
    if throughput_tpy > 0:
        denom = 0.98 - 0.06 * k1
        ccop = (variable_costs + fcop_base + 0.02 * annualized_capital + 0.06 * k2) / denom
        working_capital = k1 * ccop + k2
        interest_working = 0.06 * working_capital
        tcop = ccop + annualized_capital
        sales_marketing = 0.01 * tcop
        license_fees = 0.01 * tcop
        fixed_costs = fcop_base + interest_working + sales_marketing + license_fees
        cash_cost = variable_costs + fixed_costs
    else:
        working_capital = interest_working = sales_marketing = license_fees = fixed_costs = cash_cost = tcop = 0.0
        
    rows = [
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
        ("R&D costs", rnd),
        ("General plant overhead", rnd + sales_marketing + gna),
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
    return pd.DataFrame([{CommonColumns.ITEM: item, CommonColumns.VALUE: value} for item, value in rows])

def cm_recovery_product_outputs(scenario: Scenario, process: str) -> pd.DataFrame:
    products = _cm_recovery_product_quantities(scenario, process)
    records = (
        [
            {"product": product, "kg_per_kg_black_mass": quantity}
            for product, quantity in products.items()
            if quantity > 0
        ]
    )
    return pd.DataFrame(records, columns=["product", "kg_per_kg_black_mass"])


def _cm_recovery_product_quantities(scenario: Scenario, process: str) -> dict[str, float]:
    bm = preprocessing_black_mass_composition(scenario).set_index(CommonColumns.COMPONENT)["fraction_of_black_mass"]
    cu = bm.get("Copper", 0.0)
    al = bm.get("Aluminum", 0.0)
    graphite = bm.get("Graphite", 0.0)

    element_mass = _elemental_mass_for_scenario(scenario)
    li = sum(bm.get(chem, 0.0) * element_mass[chem]["Li"] / element_mass[chem]["Total"] for chem in element_mass)
    co = sum(bm.get(chem, 0.0) * element_mass[chem]["Co"] / element_mass[chem]["Total"] for chem in element_mass)
    ni = sum(bm.get(chem, 0.0) * element_mass[chem]["Ni"] / element_mass[chem]["Total"] for chem in element_mass)
    mn = sum(bm.get(chem, 0.0) * element_mass[chem]["Mn"] / element_mass[chem]["Total"] for chem in element_mass)

    products = {}
    if process == "Pyro":
        products["Copper metal"] = cu * 0.95
        products["Co2+ in product"] = co * 0.95
        products["Ni2+ in product"] = ni * 0.95
    elif process == "Hydro":
        if uses_new_recycling_flow(scenario):
            products["Mn2+ in product"] = mn * new_flow_parameter_value(scenario, "hydro_mn_recovery")
            products["Co2+ in product"] = co * new_flow_parameter_value(scenario, "hydro_co_recovery")
            products["Ni2+ in product"] = ni * new_flow_parameter_value(scenario, "hydro_ni_recovery")
            products["Lithium carbonate (crude)"] = li * new_flow_parameter_value(scenario, "hydro_li_recovery") / 7.0 * 37.0
            return products
        products["Mn2+ in product"] = mn * 0.98
        products["Co2+ in product"] = co * 0.98
        products["Ni2+ in product"] = ni * 0.98
        products["Lithium carbonate (crude)"] = li * 0.9 / 7.0 * 37.0
        products["Copper"] = cu * 0.9
        products["Aluminum"] = al * 0.9
        products["Graphite"] = graphite * 0.9
    elif process in {"Direct", "Custom"}:
        if process == "Direct" and uses_new_recycling_flow(scenario):
            recovery = new_flow_parameter_value(scenario, "direct_rejuvenated_cathode_recovery")
            for chem in NMC_CATHODE_MATERIALS:
                val = bm.get(chem, 0.0)
                if val > 0:
                    products[f"Rejuvenated {chem}"] = val * recovery
            return products
        products["Copper"] = cu * 0.9
        products["Aluminum"] = al * 0.9
        products["Graphite"] = graphite * 0.9
        for chem in NMC_CATHODE_MATERIALS:
            val = bm.get(chem, 0.0)
            if val > 0:
                products[chem] = val * 0.9

    return products


def _elemental_mass_for_scenario(scenario: Scenario) -> dict[str, dict[str, float]]:
    values = dict(ELEMENTAL_MASS)
    if (
        is_custom_nmc(scenario.feedstock_chemistry)
        or is_custom_nmc(scenario.cathode_chemistry)
        or any(is_custom_nmc(feedstock.chemistry) for feedstock in scenario.feedstocks)
    ):
        values[CUSTOM_NMC_LABEL] = custom_nmc_elemental_mass(scenario)
    return values


def _uses_nmc622_workbook_revenue_overrides(scenario: Scenario, process: str) -> bool:
    return (
        not uses_new_recycling_flow(scenario)
        and process in CM_RECOVERY_NMC622_PRODUCT_OVERRIDES
        and scenario.feedstock_chemistry == "NMC(622)"
        and all(feedstock.chemistry == "NMC(622)" for feedstock in scenario.feedstocks)
    )


def _cm_recovery_revenue_product_quantities(scenario: Scenario, process: str) -> dict[str, float]:
    if _uses_nmc622_workbook_revenue_overrides(scenario, process):
        return dict(CM_RECOVERY_NMC622_PRODUCT_OVERRIDES[process])
    return _cm_recovery_product_quantities(scenario, process)


def cm_recovery_revenue_product_outputs(scenario: Scenario, process: str) -> pd.DataFrame:
    products = _cm_recovery_revenue_product_quantities(scenario, process)
    records = (
        [
            {"product": product, "kg_per_kg_black_mass": quantity}
            for product, quantity in products.items()
            if quantity > 0
        ]
    )
    return pd.DataFrame(records, columns=["product", "kg_per_kg_black_mass"])


def cm_recovery_product_prices() -> dict[str, float]:
    prices: dict[str, float] = {}
    for label, price in CM_RECOVERY_PRODUCT_PRICES.items():
        prices[label] = price
        prices[label.casefold()] = price
    return prices


def _price_for_product(prices: dict[str, float], product: str) -> float:
    return prices.get(product, prices.get(product.casefold(), 0.0))


def _source_row_for_product(process: str, product: str) -> int | None:
    return CM_RECOVERY_PRODUCT_SOURCE_ROWS.get(process, {}).get(product.casefold())


def cm_recovery_revenue_per_kg_feed(scenario: Scenario, process: str) -> float:
    products = cm_recovery_revenue_product_outputs(scenario, process)
    if products.empty:
        return 0.0

    prices = cm_recovery_product_prices()
    return float(
        sum(
            row["kg_per_kg_black_mass"] * _price_for_product(prices, str(row["product"]))
            for row in products.to_dict("records")
        )
    )


def cm_recovery_revenue_output_table(
    scenario: Scenario | None = None,
    processes: tuple[str, ...] = ("Pyro", "Hydro", "Direct", "Custom"),
) -> pd.DataFrame:
    scenario = scenario or default_scenario()
    prices = cm_recovery_product_prices()
    records = []
    for process in processes:
        products = cm_recovery_revenue_product_outputs(scenario, process)
        for row in products.to_dict("records"):
            product_label = str(row["product"])
            quantity = float(row["kg_per_kg_black_mass"])
            price = _price_for_product(prices, product_label)
            records.append(
                {
                    CommonColumns.PROCESS: process,
                    CommonColumns.MATERIAL: product_label,
                    "quantity_kg_per_kg_black_mass": quantity,
                    "price_per_kg": price,
                    "calculated_value_per_kg_feedstock": quantity * price,
                    "source_row": _source_row_for_product(process, product_label),
                    "source": (
                        "workbook_override"
                        if _uses_nmc622_workbook_revenue_overrides(scenario, process)
                        else "scenario_formula"
                    ),
                }
            )
    return pd.DataFrame(records)


def cm_recovery_cost_summary(scenario: Scenario, process: str) -> pd.DataFrame:
    throughput = cm_recovery_throughput_parameters(scenario).cost_design_tpy
    capex = cm_recovery_capex_summary(scenario, process).set_index(CommonColumns.ITEM)[CommonColumns.VALUE].to_dict()
    opex = cm_recovery_opex_summary(scenario, process).set_index(CommonColumns.ITEM)[CommonColumns.VALUE].to_dict()

    fixed_capital = capex.get("Fixed capital investment", 0.0)
    working_capital = opex.get("Working capital", 0.0)
    
    feed_cost_per_kg = (
        new_flow_parameter_value(scenario, "cm_feed_cost_usd_per_kg", CM_RECOVERY_FEED_COSTS[process])
        if uses_new_recycling_flow(scenario) and process in {"Hydro", "Direct"}
        else CM_RECOVERY_FEED_COSTS.get(process, CM_RECOVERY_FEED_COSTS["Pyro"])
    )

    rows = [
        ("Total capital investment ($)", fixed_capital + working_capital),
        ("Fixed capital investment ($)", fixed_capital),
        ("Working capital ($)", working_capital),
        ("Variable costs of production ($/yr)", opex.get("Variable costs of production", 0.0)),
        ("Fixed costs of production ($/yr)", opex.get("Fixed costs of production", 0.0)),
        ("Cash cost of production ($/yr)", opex.get("Cash cost of production", 0.0)),
        ("Annualized capital cost ($/yr)", opex.get("Annualized capital cost", 0.0)),
        ("Feed cost ($/kg feed)", feed_cost_per_kg),
    ]
    
    records = [{CommonColumns.ITEM: item, CommonColumns.VALUE: value} for item, value in rows]
    total_cost = 0.0
    if throughput > 0:
        total_cost = (opex.get("Cash cost of production", 0.0) + opex.get("Annualized capital cost", 0.0)) / throughput / 1000
        if feed_cost_per_kg < 0:
            total_cost += feed_cost_per_kg
    
    records.append({CommonColumns.ITEM: "Total cost ($/kg black mass processed)", CommonColumns.VALUE: total_cost})
    return pd.DataFrame(records)
