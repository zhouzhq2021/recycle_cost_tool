import pytest

from recycle_cost.cm_recovery import (
    cm_recovery_cost_summary,
    cm_recovery_product_outputs,
    cm_recovery_revenue_per_kg_feed,
    cm_recovery_throughput_parameters,
)
from recycle_cost.model import Scenario, get_scenario_from_preset
from recycle_cost.new_flow_parameters import new_flow_parameters_complete, new_flow_parameter_specs
from recycle_cost.preprocessing import preprocessing_product_outputs
from recycle_cost.reporting import python_ported_output_summary_table
from recycle_cost.schemas import CommonColumns


def _new_recycling_scenario(process: str) -> Scenario:
    base = get_scenario_from_preset("pack_hydro")
    return Scenario(
        **{
            **base.__dict__,
            "recycling_process": process,
            "recycling_flow_variant": "new",
        }
    )


def _complete_new_recycling_scenario(process: str) -> Scenario:
    scenario = _new_recycling_scenario(process)
    process_key = "Direct" if process == "Direct" else "Hydro"
    values = {
        spec.key: (spec.default_value if spec.default_value is not None else 0.9)
        for spec in new_flow_parameter_specs(process_key)
    }
    return Scenario(**{**scenario.__dict__, "new_flow_parameters": values})


def _legacy_recycling_scenario(process: str) -> Scenario:
    base = get_scenario_from_preset("pack_hydro")
    return Scenario(
        **{
            **base.__dict__,
            "recycling_process": process,
            "recycling_flow_variant": "old",
        }
    )


@pytest.mark.parametrize("process", ["Hydrometallurgical", "Direct"])
def test_legacy_hydro_and_direct_retain_original_preprocessing(process):
    scenario = _legacy_recycling_scenario(process)
    products = preprocessing_product_outputs(scenario).set_index("product")

    assert "Black mass" in products.index
    assert "S-Cathode" not in products.index
    assert "Battery electrolyte" not in products.index
    assert products.loc["Black mass", "kg_per_kg_feedstock"] == pytest.approx(0.43920315314241677)


def test_new_recycling_flow_requires_user_supplied_extra_parameters():
    scenario = _new_recycling_scenario("Hydrometallurgical")
    assert new_flow_parameters_complete(scenario) is False


def test_complete_new_recycling_flow_uses_user_parameterized_s_cathode_products():
    scenario = _complete_new_recycling_scenario("Hydrometallurgical")
    products = preprocessing_product_outputs(scenario).set_index("product")

    assert new_flow_parameters_complete(scenario) is True
    assert "S-Cathode" in products.index
    assert "S-Anode" in products.index
    assert "Battery electrolyte" in products.index
    assert "Black mass" not in products.index
    assert products.loc["S-Cathode", "kg_per_kg_feedstock"] > 0
    assert products.loc["Battery electrolyte", "kg_per_kg_feedstock"] > 0


def test_new_hydro_model_uses_s_cathode_for_recovery_outputs_and_report():
    scenario = _complete_new_recycling_scenario("Hydrometallurgical")
    throughput = cm_recovery_throughput_parameters(scenario)
    products = cm_recovery_product_outputs(scenario, "Hydro").set_index("product")
    report = python_ported_output_summary_table(scenario).set_index(CommonColumns.METRIC)

    assert throughput.material_flow_tpy > 0
    assert "Lithium carbonate (crude)" in products.index
    assert "Graphite" not in products.index
    assert products.loc["Ni2+ in product", "kg_per_kg_black_mass"] > 0
    assert cm_recovery_revenue_per_kg_feed(scenario, "Hydro") > 0
    assert report.loc["Recycling cost", "Hydro"] > 0
    assert report.loc["Recycling revenue", "Hydro"] > 0


def test_new_direct_model_outputs_rejuvenated_cathode_and_report_values():
    scenario = _complete_new_recycling_scenario("Direct")
    products = cm_recovery_product_outputs(scenario, "Direct").set_index("product")
    report = python_ported_output_summary_table(scenario).set_index(CommonColumns.METRIC)
    cm_cost = cm_recovery_cost_summary(scenario, "Direct").set_index(CommonColumns.ITEM)

    assert "Rejuvenated NMC(622)" in products.index
    assert "NMC(622)" not in products.index
    assert products.loc["Rejuvenated NMC(622)", "kg_per_kg_black_mass"] > 0
    assert cm_cost.loc["Total cost ($/kg black mass processed)", CommonColumns.VALUE] > 0
    assert report.loc["Recycling cost", "Direct"] > 0
    assert report.loc["Recycling revenue", "Direct"] > 0
