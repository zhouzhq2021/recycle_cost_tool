import pytest
import pandas as pd
from recycle_cost.model import default_scenario
from recycle_cost.cm_recovery import cm_recovery_cost_summary, cm_recovery_product_outputs
from recycle_cost.mat_conv import mat_conv_available_precursors, mat_conv_total_summary_calculated
from recycle_cost.cathode import (
    cathode_general_inputs,
    cathode_available_precursors,
    cathode_material_energy_demand,
    cathode_chemical_prices,
    cathode_utility_prices,
    cathode_material_conversion_costs,
    cathode_required_precursors,
    cathode_recycled_virgin_split,
    cathode_environment_summary,
    cathode_cost_per_line_summary,
    cathode_detailed_cost_summary,
)
from recycle_cost.schemas import CommonColumns, ManufacturingColumns, StageSummaryColumns


def test_dashboard_cm_recovery_and_mat_conversion_tables_are_populated():
    scenario = default_scenario()
    process = "Hydro"
    
    cm_cost = cm_recovery_cost_summary(scenario, process)
    cm_products = cm_recovery_product_outputs(scenario, process)
    mat_total = mat_conv_total_summary_calculated(scenario)
    available_precursors = mat_conv_available_precursors(scenario, process)

    assert not cm_cost.empty
    assert not cm_products.empty
    assert not mat_total.empty
    assert not available_precursors.empty
    
    assert CommonColumns.ITEM in cm_cost.columns
    assert "product" in cm_products.columns
    assert CommonColumns.METRIC in mat_total.columns
    assert CommonColumns.MATERIAL in available_precursors.columns


def test_dashboard_cathode_production_tables_are_populated():
    scenario = default_scenario()
    
    general = cathode_general_inputs()
    available = cathode_available_precursors()
    demand = cathode_material_energy_demand()
    chem_prices = cathode_chemical_prices()
    util_prices = cathode_utility_prices()
    conv_costs = cathode_material_conversion_costs()
    required = cathode_required_precursors("NMC(622)")
    split = cathode_recycled_virgin_split("NMC(622)")
    env = cathode_environment_summary("NMC(622)")
    costs = cathode_cost_per_line_summary("NMC(622)")
    detailed = cathode_detailed_cost_summary("NMC(622)")

    for df in [general, available, demand, chem_prices, util_prices, conv_costs, required, split, env, costs, detailed]:
        assert not df.empty

    assert CommonColumns.ITEM in general.columns
    assert CommonColumns.MATERIAL in available.columns
    assert CommonColumns.ITEM in demand.columns
    assert "chemical" in chem_prices.columns
    assert "utility" in util_prices.columns
    assert CommonColumns.MATERIAL in conv_costs.columns
    assert CommonColumns.MATERIAL in required.columns
    assert CommonColumns.MATERIAL in split.columns
    assert CommonColumns.METRIC in env.columns
    assert CommonColumns.ITEM in costs.columns
    assert CommonColumns.ITEM in detailed.columns
