import pytest
from recycle_cost.model import default_scenario, Scenario
from recycle_cost.mat_conv import (
    mat_conv_available_precursors,
    mat_conv_allocation_factors,
    mat_conv_allocation_factors_calculated,
    mat_conv_conversion_costs,
    mat_conv_conversion_environment,
    mat_conv_recovered_materials,
    mat_conv_recycling_economics,
    mat_conv_recycling_economics_calculated,
    mat_conv_recycling_environment_summary,
    mat_conv_recycling_environment_summary_calculated,
    mat_conv_total_summary,
    mat_conv_workbook_available_precursors,
)
from recycle_cost.schemas import CommonColumns, AuditColumns

def test_mat_conv_available_precursors_default():
    base = default_scenario()
    scenario = Scenario(**{**base.__dict__, "manufacturing_location": "China"})
    
    precursors = mat_conv_available_precursors(scenario, "Pyro").set_index(CommonColumns.MATERIAL)
    assert precursors.loc["Cobalt Oxide", "kg_per_kg_feedstock"] == pytest.approx(0.09499551979879571)
    assert precursors.loc["Cobalt Sulfate", "kg_per_kg_feedstock"] == pytest.approx(0.1834001580607249)
    assert precursors.loc["Nickel Sulfate", "kg_per_kg_feedstock"] == pytest.approx(0.5491168982689551)
    
def test_mat_conv_conversion_costs_default():
    base = default_scenario()
    scenario = Scenario(**{**base.__dict__, "manufacturing_location": "China"})
    
    costs = mat_conv_conversion_costs(scenario).set_index(CommonColumns.MATERIAL)
    assert costs.loc["Cobalt Oxide", "material_cost_per_kg"] == pytest.approx(0.9313631286502133)
    assert costs.loc["Cobalt Oxide", "utility_cost_per_kg"] == pytest.approx(0.13679594499421627)
    assert costs.loc["Cobalt Oxide", "cost_per_kg"] == pytest.approx(1.0681590736444295)
    assert costs.loc["Nickel Sulfate", "cost_per_kg"] == pytest.approx(0.053752330931967275)


def test_mat_conv_workbook_snapshot_tables_default():
    recovered = mat_conv_recovered_materials(default_scenario()).set_index(CommonColumns.MATERIAL)
    workbook_precursors = mat_conv_workbook_available_precursors().set_index(CommonColumns.MATERIAL)
    economics = mat_conv_recycling_economics().set_index(CommonColumns.ITEM)
    allocation = mat_conv_allocation_factors().set_index(CommonColumns.MATERIAL)

    assert recovered.loc["Co2+ in product", "Pyro"] == pytest.approx(0.06973705171768675)
    assert recovered.loc["NMC(622)", "Direct"] == pytest.approx(0.5433043638317865)
    assert workbook_precursors.loc["Cobalt Oxide", "Pyro"] == pytest.approx(0.16618788907753254)
    assert economics.loc["cost_recycled_materials_to_convert", "Direct"] == pytest.approx(6.502244183213815)
    assert allocation.loc["NMC(622)", "economic_direct"] == pytest.approx(0.9929821921589066)


def test_mat_conv_allocation_factors_calculated_follow_scenario_products():
    calculated = mat_conv_allocation_factors_calculated(default_scenario()).set_index(CommonColumns.MATERIAL)

    assert calculated.loc["Copper metal", AuditColumns.calculated("mass_pyro")] == pytest.approx(0.03417359100905223)
    assert calculated.loc["Co2+ in product", AuditColumns.calculated("economic_pyro")] == pytest.approx(0.49489421005113576)
    assert calculated.loc["NMC(622)", AuditColumns.calculated("mass_direct")] == pytest.approx(0.6120139466191254)
    assert calculated.loc["NMC(622)", AuditColumns.calculated("economic_direct")] == pytest.approx(0.9898789924782604)
    assert calculated.loc["NMC(622)", AuditColumns.workbook("economic_direct")] == pytest.approx(0.9929821921589066)
    assert abs(calculated.loc["NMC(622)", "economic_direct_delta"]) > 0.0


def test_mat_conv_recycling_economics_calculated_uses_python_output_stage_values():
    economics = mat_conv_recycling_economics_calculated(default_scenario()).set_index(CommonColumns.ITEM)

    assert economics.loc["total_recycling_cost", AuditColumns.calculated("Pyro")] == pytest.approx(4.745074097322276)
    assert economics.loc["total_recycling_cost", "pyro_delta"] == pytest.approx(0.0, abs=1e-12)
    assert economics.loc["revenue_all_recycled_materials", AuditColumns.calculated("Direct")] == pytest.approx(13.721484342029777)
    assert economics.loc["revenue_all_recycled_materials", "direct_delta"] == pytest.approx(-0.629226186845022)
    assert economics.loc["cost_recycled_materials_to_convert", AuditColumns.calculated("Direct")] == pytest.approx(6.464079023973588)


def test_mat_conv_recycling_environment_summary_calculated_uses_output_and_transport_values():
    environment = mat_conv_recycling_environment_summary_calculated(default_scenario()).set_index(CommonColumns.METRIC)

    assert environment.loc["Total Energy", AuditColumns.calculated("Pyro")] == pytest.approx(0.429539944427567)
    assert environment.loc["Total Energy", "pyro_delta"] == pytest.approx(0.0, abs=1e-12)
    assert environment.loc["Water consumption (gal/kg)", AuditColumns.calculated("Hydro")] == pytest.approx(53.211384286194355)
    assert environment.loc["GHGs", AuditColumns.calculated("Direct")] == pytest.approx(7766.196919210193)
    assert environment.loc["GHGs", "direct_delta"] == pytest.approx(203.2054314529766)


def test_mat_conv_recycling_environment_summary_calculated_allocates_cathode_materials_only():
    environment = mat_conv_recycling_environment_summary_calculated(
        default_scenario(),
        cathode_materials_only=True,
    ).set_index(CommonColumns.METRIC)

    assert environment.loc["Total Energy", AuditColumns.calculated("Hydro")] == pytest.approx(0.24598586921425348)
    assert environment.loc["Total Energy", "hydro_delta"] == pytest.approx(0.08939623852802117)
    assert environment.loc["GHGs", AuditColumns.calculated("Direct")] == pytest.approx(4753.020827289609)
    assert environment.loc["GHGs", AuditColumns.workbook("Direct")] == pytest.approx(4302.300547176513)


def test_mat_conv_environment_snapshot_tables_default():
    total_recycling = mat_conv_recycling_environment_summary().set_index(CommonColumns.METRIC)
    cathode_only = mat_conv_recycling_environment_summary(cathode_materials_only=True).set_index(CommonColumns.METRIC)
    conversion = mat_conv_conversion_environment().set_index([CommonColumns.MATERIAL, CommonColumns.METRIC])
    summary = mat_conv_total_summary().set_index(CommonColumns.METRIC)

    assert total_recycling.loc["GHGs", "Pyro"] == pytest.approx(37521.18082640617)
    assert cathode_only.loc["Water consumption (gal/kg)", "Hydro"] == pytest.approx(20.96721213926428)
    assert conversion.loc[("Cobalt Oxide", "GHGs"), CommonColumns.VALUE] == pytest.approx(2925.0671014546183)
    assert summary.loc["Total cost of material conversion ($/kg)", CommonColumns.VALUE] == pytest.approx(1.0681590736444295)
