import pytest

from recycle_cost.cm_recovery import (
    cm_recovery_cost_summary,
    cm_recovery_product_outputs,
    cm_recovery_revenue_per_kg_feed,
    cm_recovery_throughput_parameters,
)
from recycle_cost.model import Scenario, get_scenario_from_preset
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


def test_new_recycling_flow_uses_s_cathode_pretreatment_products():
    scenario = _new_recycling_scenario("Hydrometallurgical")
    products = preprocessing_product_outputs(scenario).set_index("product")

    assert "S-Cathode" in products.index
    assert "S-Anode" in products.index
    assert "Battery electrolyte" in products.index
    assert "Black mass" not in products.index
    assert products.loc["S-Cathode", "kg_per_kg_feedstock"] == pytest.approx(0.27515055184260473)
    assert products.loc["Battery electrolyte", "kg_per_kg_feedstock"] == pytest.approx(0.056927131399294326)


def test_new_hydro_model_uses_s_cathode_for_recovery_outputs_and_report():
    scenario = _new_recycling_scenario("Hydrometallurgical")
    throughput = cm_recovery_throughput_parameters(scenario)
    products = cm_recovery_product_outputs(scenario, "Hydro").set_index("product")
    report = python_ported_output_summary_table(scenario).set_index(CommonColumns.METRIC)

    assert throughput.material_flow_tpy == pytest.approx(2751.5055184260473)
    assert "Lithium carbonate (crude)" in products.index
    assert "Graphite" not in products.index
    assert products.loc["Ni2+ in product", "kg_per_kg_black_mass"] == pytest.approx(0.355808)
    assert cm_recovery_revenue_per_kg_feed(scenario, "Hydro") == pytest.approx(15.373728269588174)
    assert report.loc["Recycling cost", "Hydro"] == pytest.approx(35.59873928784398)
    assert report.loc["Recycling revenue", "Hydro"] == pytest.approx(15.373728269588174)


def test_new_direct_model_outputs_rejuvenated_cathode_and_report_values():
    scenario = _new_recycling_scenario("Direct")
    products = cm_recovery_product_outputs(scenario, "Direct").set_index("product")
    report = python_ported_output_summary_table(scenario).set_index(CommonColumns.METRIC)
    cm_cost = cm_recovery_cost_summary(scenario, "Direct").set_index(CommonColumns.ITEM)

    assert "Rejuvenated NMC(622)" in products.index
    assert "NMC(622)" not in products.index
    assert products.loc["Rejuvenated NMC(622)", "kg_per_kg_black_mass"] == pytest.approx(0.964413)
    assert cm_cost.loc["Total cost ($/kg black mass processed)", CommonColumns.VALUE] == pytest.approx(4.897721711586309)
    assert report.loc["Recycling cost", "Direct"] == pytest.approx(35.163221757867724)
    assert report.loc["Recycling revenue", "Direct"] == pytest.approx(24.11032576069974)
