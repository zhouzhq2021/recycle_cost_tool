import pytest

from recycle_cost.cathode import (
    cathode_available_precursors,
    cathode_available_precursors_for_scenario,
    cathode_capital_cost_calculated,
    cathode_chemical_prices,
    cathode_chemistry_for_scenario,
    cathode_cost_per_line_summary,
    cathode_cost_per_line_summary_calculated,
    cathode_detailed_cost_summary,
    cathode_direct_regeneration_environment_summary,
    cathode_environment_summary,
    cathode_general_inputs,
    cathode_labor_cost_calculated,
    cathode_maintenance_cost_calculated,
    cathode_material_conversion_costs,
    cathode_material_energy_demand,
    cathode_raw_material_cost_calculated,
    cathode_raw_material_cost_summary,
    cathode_recycled_virgin_split,
    cathode_recycled_virgin_split_calculated,
    cathode_recycled_virgin_split_for_scenario,
    cathode_required_precursors,
    cathode_throughput_tonnes_per_year,
    cathode_total_cost_calculated,
    cathode_utility_prices,
    cathode_utility_cost_calculated,
    cathode_virgin_environment_summary,
)
from recycle_cost.model import Scenario, default_scenario
from recycle_cost.schemas import CommonColumns, AuditColumns, CathodeColumns


def test_cathode_general_inputs_and_available_precursors_default():
    inputs = cathode_general_inputs().set_index(CommonColumns.ITEM)
    precursors = cathode_available_precursors().set_index(CommonColumns.MATERIAL)

    assert inputs.loc["throughput", CommonColumns.VALUE] == 0
    assert inputs.loc["cathode_chemistry", CommonColumns.VALUE] == "Select Chemistry"
    assert precursors.loc["Cobalt Oxide", "Pyro"] == pytest.approx(1661.8788907753253)
    assert precursors.loc["Cobalt Sulfate", "Hydro"] == pytest.approx(3313.6502546689308)
    assert precursors.loc["Manganese Sulfate", "Hydro"] == pytest.approx(3243.3879781420765)


def test_cathode_material_energy_demand_default():
    demand = cathode_material_energy_demand().set_index(CommonColumns.ITEM)

    assert demand.loc["Nickel Sulfate", "NMC(622)"] == pytest.approx(0.957927533839551)
    assert demand.loc["Cobalt Sulfate", "NMC(622)"] == pytest.approx(0.3198043908880819)
    assert demand.loc["Manganese Sulfate", "NMC(622)"] == pytest.approx(0.31157147573456584)
    assert demand.loc["Process water (gal)", "NMC(622)"] == pytest.approx(0.17643729536304803)
    assert demand.loc["Electricity", "NMC(622)"] == pytest.approx(25.2)
    assert demand.loc["Natural gas", "NMC(622)"] == pytest.approx(42.62976134996079)
    assert demand.loc["CO2", "NMC(622)"] == pytest.approx(227.02418289864636)


def test_cathode_prices_and_conversion_costs_default():
    chemicals = cathode_chemical_prices().set_index("chemical")
    utilities = cathode_utility_prices().set_index("utility")
    conversion = cathode_material_conversion_costs().set_index(CommonColumns.MATERIAL)

    assert chemicals.loc["Lithium Carbonate", "selected"] == pytest.approx(17.14)
    assert chemicals.loc["Nickel Sulfate", "selected"] == pytest.approx(6.394771170006465)
    assert utilities.loc["Natural gas ($/MMBTU)", "selected"] == pytest.approx(12)
    assert utilities.loc["Electricity ($/kWh)", "selected"] == pytest.approx(0.088)
    assert conversion.loc["Cobalt Oxide", "cost_per_kg_precursor"] == pytest.approx(1.0681590736444295)
    assert conversion.loc["Lithium Hydroxide", "cost_per_kg_precursor"] == pytest.approx(0.2715206237924763)


def test_cathode_nmc622_block_snapshots_default():
    required = cathode_required_precursors("NMC(622)").set_index(CommonColumns.MATERIAL)
    split = cathode_recycled_virgin_split("NMC(622)").set_index(CommonColumns.MATERIAL)
    environment = cathode_environment_summary("NMC(622)").set_index(CommonColumns.METRIC)
    costs = cathode_cost_per_line_summary("NMC(622)").set_index(CommonColumns.ITEM)
    detailed = cathode_detailed_cost_summary("NMC(622)").set_index(CommonColumns.ITEM)

    assert required.loc["Nickel Sulfate", "selected"] == pytest.approx(0.957927533839551)
    assert required.loc["Lithium Carbonate", "default_greet"] == pytest.approx(0.381159210960713)
    assert split.loc["Sodium Hydroxide", "pyro_virgin"] == pytest.approx(0.8443837517332456)
    assert split.loc["Ammonium Hydroxide", "hydro_virgin"] == pytest.approx(0.11725914201930376)
    assert environment.loc["GHGs", "energy_input"] == pytest.approx(2965.3492856599332)
    assert environment.loc["GHGs", "process"] == pytest.approx(226.63520651718068)
    assert costs.loc["Fixed capital investment ($)", "Pyro"] == pytest.approx(0)
    assert costs.loc["Total cost to recipient ($/kg cathode)", "Virgin"] == pytest.approx(0)
    assert detailed.loc["Raw materials", CathodeColumns.annual_col("Pyro")] == pytest.approx(0)


def test_cathode_direct_regeneration_environment_summary_default():
    direct = cathode_direct_regeneration_environment_summary("NMC(622)").set_index(CommonColumns.METRIC)

    assert direct.loc["Total Energy", "direct_regeneration"] == pytest.approx(0.0865326170077573)
    assert direct.loc["Water consumption (gal/kg)", "direct_regeneration"] == pytest.approx(12.058548086343865)
    assert direct.loc["GHGs", "direct_regeneration"] == pytest.approx(7547.895697081495)


def test_cathode_direct_regeneration_environment_falls_back_to_virgin_when_no_direct_product():
    direct = cathode_direct_regeneration_environment_summary("LCO").set_index(CommonColumns.METRIC)

    assert direct.loc["Total Energy", "direct_regeneration"] == pytest.approx(0.2821389456725482)
    assert direct.loc["GHGs", "direct_regeneration"] == pytest.approx(21516.171766062387)


def test_cathode_recycled_virgin_split_calculated_matches_workbook_default():
    calculated = cathode_recycled_virgin_split_calculated("NMC(622)").set_index(CommonColumns.MATERIAL)

    assert calculated.loc["Sodium Hydroxide", AuditColumns.calculated("pyro_virgin")] == pytest.approx(0.8443837517332456)
    assert calculated.loc["Cobalt Sulfate", AuditColumns.calculated("pyro_virgin")] == pytest.approx(0.0)
    assert calculated.loc["Manganese Sulfate", AuditColumns.calculated("hydro_virgin")] == pytest.approx(0.0)
    delta_columns = [column for column in calculated.columns if column.endswith("_delta")]
    assert calculated[delta_columns].abs().max().max() == pytest.approx(0.0, abs=1e-12)


def test_cathode_raw_material_cost_calculated_matches_workbook_default():
    calculated = cathode_raw_material_cost_calculated("NMC(622)").set_index(CommonColumns.PROCESS)

    assert calculated.loc["Pyro", AuditColumns.calculated(CathodeColumns.ANNUAL)] == pytest.approx(0.0)
    assert calculated.loc["Virgin", AuditColumns.calculated(CathodeColumns.PER_KG)] == pytest.approx(0.0)
    assert calculated["annual_delta"].abs().max() == pytest.approx(0.0, abs=1e-9)
    assert calculated["per_kg_delta"].abs().max() == pytest.approx(0.0, abs=1e-12)


def test_cathode_utility_cost_calculated_matches_workbook_default():
    calculated = cathode_utility_cost_calculated("NMC(622)").set_index(CommonColumns.PROCESS)

    assert calculated.loc["Pyro", AuditColumns.calculated(CathodeColumns.ANNUAL)] == pytest.approx(0.0)
    assert calculated.loc["Virgin", "calculated_electricity"] == pytest.approx(0.0)
    assert calculated["annual_delta"].abs().max() == pytest.approx(0.0, abs=1e-9)


def test_cathode_labor_cost_calculated_matches_workbook_default():
    calculated = cathode_labor_cost_calculated("NMC(622)").set_index([CommonColumns.PROCESS, CommonColumns.ITEM])

    assert calculated.loc[("Pyro", "Operating labor"), "base_labor_per_day"] == pytest.approx(1224.0)
    assert calculated.loc[("Virgin", "Operating labor"), AuditColumns.calculated(CathodeColumns.ANNUAL)] == pytest.approx(0.0)
    assert calculated.loc[("Hydro", "Direct supervisory and clerical labor"), AuditColumns.calculated(CathodeColumns.ANNUAL)] == pytest.approx(0.0)
    assert calculated["annual_delta"].abs().max() == pytest.approx(0.0, abs=1e-9)


def test_cathode_capital_cost_calculated_matches_workbook_default():
    calculated = cathode_capital_cost_calculated("NMC(622)").set_index([CommonColumns.PROCESS, CommonColumns.ITEM])

    assert calculated.loc[("Pyro", "Direct costs ($)"), AuditColumns.calculated(CommonColumns.VALUE)] == pytest.approx(0.0)
    assert calculated.loc[("Virgin", "Total capital investment ($)"), AuditColumns.calculated(CommonColumns.VALUE)] == pytest.approx(0.0)
    assert calculated["delta"].abs().max() == pytest.approx(0.0, abs=1e-9)


def test_cathode_maintenance_cost_calculated_matches_workbook_default():
    calculated = cathode_maintenance_cost_calculated("NMC(622)").set_index([CommonColumns.PROCESS, CommonColumns.ITEM])

    assert calculated.loc[("Pyro", "Maintenance and repairs"), AuditColumns.calculated(CathodeColumns.ANNUAL)] == pytest.approx(0.0)
    assert calculated.loc[("Hydro", "Operating supplies"), AuditColumns.calculated(CathodeColumns.ANNUAL)] == pytest.approx(0.0)
    assert calculated["annual_delta"].abs().max() == pytest.approx(0.0, abs=1e-9)


def test_cathode_total_cost_calculated_matches_workbook_default():
    calculated = cathode_total_cost_calculated("NMC(622)").set_index([CommonColumns.PROCESS, CommonColumns.ITEM])

    assert calculated.loc[("Pyro", "Manufacturing cost"), AuditColumns.calculated(CommonColumns.VALUE)] == pytest.approx(0.0)
    assert calculated.loc[("Hydro", "Total product cost"), AuditColumns.calculated(CommonColumns.VALUE)] == pytest.approx(0.0)
    assert calculated.loc[("Virgin", "Total product cost to recipient"), AuditColumns.calculated(CommonColumns.VALUE)] == pytest.approx(0.0)
    assert calculated["delta"].abs().max() == pytest.approx(0.0, abs=1e-9)


def test_cathode_cost_per_line_summary_calculated_matches_workbook_default():
    calculated = cathode_cost_per_line_summary_calculated("NMC(622)").set_index(CommonColumns.ITEM)

    assert calculated.loc["Fixed capital investment ($)", AuditColumns.calculated("Pyro")] == pytest.approx(0.0)
    assert calculated.loc["Total product cost ($/yr)", AuditColumns.calculated("Hydro")] == pytest.approx(0.0)
    assert calculated.loc["Total cost to recipient ($/kg cathode)", AuditColumns.calculated("Virgin")] == pytest.approx(0.0)
    delta_columns = [column for column in calculated.columns if column.endswith("_delta")]
    assert calculated[delta_columns].abs().max().max() == pytest.approx(0.0, abs=1e-9)


def test_cathode_scenario_available_precursors_match_workbook_default():
    scenario = default_scenario()
    available = cathode_available_precursors_for_scenario(scenario).set_index(CommonColumns.MATERIAL)

    assert available.loc["Cobalt Oxide", "Pyro"] == pytest.approx(949.9551979879571)
    assert available.loc["Cobalt Sulfate", "Hydro"] == pytest.approx(1891.9174197642667)
    assert available.loc["Manganese Sulfate", "Hydro"] == pytest.approx(1843.3051820114854)
    assert available.loc["Nickel Sulfate", "Direct"] == pytest.approx(0)


def test_cathode_scenario_split_and_cost_for_synthetic_throughput():
    base = default_scenario()
    scenario = Scenario(
        **{
            **base.__dict__,
            "cathode_chemistry": "NMC(622)",
            "cathode_throughput_gwh_per_year": 2.0,
        }
    )
    split = cathode_recycled_virgin_split_for_scenario(scenario, "NMC(622)").set_index(CommonColumns.MATERIAL)
    costs = cathode_raw_material_cost_summary(scenario, "NMC(622)").set_index(CommonColumns.PROCESS)
    environment = cathode_virgin_environment_summary("NMC(622)").set_index(CommonColumns.METRIC)

    assert cathode_chemistry_for_scenario(scenario) == "NMC(622)"
    assert cathode_throughput_tonnes_per_year(scenario) == pytest.approx(816.5036051556764)
    assert split.loc["Cobalt Sulfate", "pyro_recycled"] == pytest.approx(2.2461647067401445)
    assert split.loc["Cobalt Sulfate", "pyro_virgin"] == pytest.approx(0)
    assert split.loc["Lithium Carbonate", "pyro_virgin"] == pytest.approx(0.381159210960713)
    assert costs.loc["Virgin", "raw_material_cost_per_kg"] == pytest.approx(19.580858690569464)
    assert costs.loc["Hydro", "raw_material_cost_per_kg"] == pytest.approx(0.9394227486505784)
    assert environment.loc["GHGs", "virgin_total"] == pytest.approx(3191.984492177114)
