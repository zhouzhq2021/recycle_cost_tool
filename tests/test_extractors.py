import pytest

from recycle_cost.extractors import (
    extract_batpac_material_costs,
    extract_geographic_parameters,
    extract_greet_combustion_factors,
    extract_material_prices,
)
from recycle_cost.disassembly import (
    disassembly_cost_breakdown,
    disassembly_feedstock_table,
    disassembly_material_recovery,
    disassembly_revenue_summary,
    disassembly_weight_summary,
)
from recycle_cost.model import FeedstockInput, Scenario, TransportDistances, default_scenario, output_summary_table
from recycle_cost.preprocessing import (
    preprocessing_black_mass_composition,
    preprocessing_cost_summary,
    preprocessing_environment_summary,
    preprocessing_feedstock_composition,
    preprocessing_feedstock_streams,
    preprocessing_product_outputs,
    preprocessing_throughput,
    preprocessing_workbook_snapshot,
)
from recycle_cost.transport import (
    scenario_transport_segments,
    transport_cost_breakdown,
    transport_environment_breakdown,
    transport_total_cost,
)


def test_default_scenario_reads_saved_inputs():
    scenario = default_scenario()
    assert scenario.manufacturing_chemistry == "NMC(622)"
    assert scenario.manufacturing_location == "U.S."
    assert scenario.feedstock_type == "Black mass"
    assert scenario.feedstock_tonnes_per_year == 10000


def test_output_summary_reads_saved_values():
    summary = output_summary_table().set_index("metric")
    assert round(summary.loc["Cell manufacturing cost", "Virgin"], 6) == round(93.51878378782261, 6)
    assert round(summary.loc["Recycling cost", "Pyro"], 6) == round(4.732668897365612, 6)
    assert round(summary.loc["Recycling cost", "Hydro"], 6) == round(5.085318217825357, 6)


def test_material_price_extraction_contains_core_metals():
    prices = extract_material_prices()
    metals = prices[prices["group"] == "Metals"].set_index("material")
    assert {"Co", "Ni", "Mn"}.issubset(set(metals.index))
    assert metals.loc["Co", "selected"] > 0


def test_geographic_extraction_contains_regions():
    geo = extract_geographic_parameters()
    assert {"U.S.", "California", "China", "Korea"}.issubset(set(geo["region"]))
    assert "Battery manufacturing" in set(geo["section"])


def test_batpac_extraction_contains_material_costs():
    costs = extract_batpac_material_costs().set_index("material")
    assert "NMC(111)" in costs.index
    assert costs.loc["NMC(111)", "cost_per_kg"] > 0


def test_greet_extraction_contains_combustion_factors():
    factors = extract_greet_combustion_factors()
    assert {"VOC", "CO", "NOx", "CO2"}.issubset(set(factors["pollutant"]))
    assert "Natural Gas" in set(factors["fuel"])


def test_transport_cost_matches_workbook_snapshot():
    breakdown = transport_cost_breakdown()
    assert breakdown["delta"].abs().max() < 1e-12
    assert round(transport_total_cost(), 12) == round(0.01240519995666417, 12)


def test_transport_environment_matches_workbook_snapshot():
    breakdown = transport_environment_breakdown()
    assert breakdown["delta"].abs().max() < 1e-10
    ghgs = breakdown.set_index("metric").loc["GHGs"]
    assert round(ghgs["calculated_total"], 9) == round(408.9271354098429, 9)


def test_default_scenario_can_drive_transport_module():
    scenario = default_scenario()
    segments = scenario_transport_segments(scenario)
    cost = transport_cost_breakdown(segments=segments)
    env = transport_environment_breakdown(segments=segments)
    assert cost["delta"].abs().max() < 1e-12
    assert env["delta"].abs().max() < 1e-10


def test_transport_environment_uses_scenario_distances():
    base = default_scenario()
    base_segments = scenario_transport_segments(base)
    base_env = transport_environment_breakdown(segments=base_segments).set_index("metric")

    scenario = Scenario(
        **{
            **base.__dict__,
            "transport_distances": TransportDistances(
                collection_to_disassembly=base.transport_distances.collection_to_disassembly,
                disassembly_to_preprocessor=base.transport_distances.disassembly_to_preprocessor,
                preprocessor_to_cm_recovery=base.transport_distances.preprocessor_to_cm_recovery * 2,
                manufacturer_to_preprocessor_or_cm_recovery=base.transport_distances.manufacturer_to_preprocessor_or_cm_recovery,
                recycler_to_cathode_producer=base.transport_distances.recycler_to_cathode_producer,
                cathode_producer_to_manufacturer=base.transport_distances.cathode_producer_to_manufacturer,
            ),
        }
    )
    changed_env = transport_environment_breakdown(segments=scenario_transport_segments(scenario)).set_index("metric")

    assert changed_env.loc["Total Energy", "calculated_total"] > base_env.loc["Total Energy", "calculated_total"]
    assert changed_env.loc["GHGs", "calculated_total"] > base_env.loc["GHGs", "calculated_total"]


def test_default_scenario_has_no_disassembly_flow():
    scenario = default_scenario()
    feedstocks = disassembly_feedstock_table(scenario)
    weights = disassembly_weight_summary(scenario)
    costs = disassembly_cost_breakdown(scenario).set_index("item")
    revenue = disassembly_revenue_summary(scenario).set_index("basis")
    assert feedstocks.empty
    assert weights["pack_equivalent_tonnes_per_year"] == 0
    assert costs.loc["Total cost", "pack_disassembly"] == 0
    assert costs.loc["Total cost", "module_disassembly"] == 0
    assert revenue.loc["$/kg battery pack", "pack_disassembly"] == 0


def test_nmc622_module_feedstock_drives_disassembly_formulas():
    base = default_scenario()
    scenario = Scenario(
        **{
            **base.__dict__,
            "feedstock_chemistry": "NMC(622)",
            "feedstock_type": "End-of-life battery: module",
            "feedstock_tonnes_per_year": 10000,
            "feedstocks": (FeedstockInput("NMC(622)", "End-of-life battery: module", 10000),),
        }
    )

    feedstocks = disassembly_feedstock_table(scenario)
    weights = disassembly_weight_summary(scenario)
    materials = disassembly_material_recovery(scenario).set_index("component")
    costs = disassembly_cost_breakdown(scenario).set_index("item")
    revenue = disassembly_revenue_summary(scenario).set_index("basis")

    assert len(feedstocks) == 1
    assert feedstocks.iloc[0]["pack_equivalent_tonnes_per_year"] == pytest.approx(14302.060258219795)
    assert weights["pack_weight_kg"] == pytest.approx(514.7856220198815)
    assert weights["cell_weight_kg"] == pytest.approx(319.2640800100628)
    assert weights["pack_count_per_year"] == 11113023
    assert materials.loc["Copper", "pack_disassembly_kg_per_pack"] == pytest.approx(3.248537620338378)
    assert materials.loc["Aluminum", "module_disassembly_kg_per_pack"] == pytest.approx(10.620248367697937)
    assert costs.loc["Total cost", "pack_disassembly"] == pytest.approx(0.4594781345081143, abs=1e-8)
    assert costs.loc["Total cost", "module_disassembly"] == pytest.approx(0.3744912948276293)
    assert revenue.loc["$/kg battery pack", "pack_disassembly"] == pytest.approx(0.1917734937799231)


def test_default_scenario_has_no_preprocessing_flow():
    scenario = default_scenario()
    snapshot = preprocessing_workbook_snapshot()
    streams = preprocessing_feedstock_streams(scenario)
    products = preprocessing_product_outputs(scenario).set_index("product")
    env = preprocessing_environment_summary(scenario).set_index("metric")

    assert preprocessing_throughput(scenario) == 0
    assert streams.loc[0, "feedstock_type"] == "Black mass"
    assert streams.loc[0, "tonnes_per_year"] == 0
    assert products.loc["Black mass", "kg_per_kg_feedstock"] == 0
    assert products.loc["Waste(water)", "kg_per_kg_feedstock"] == pytest.approx(0.378541)
    assert snapshot["throughput_tonnes_per_year"] == 0
    assert snapshot["generic_black_mass_kg_per_kg"] == 1
    assert env.loc["GHGs", "total"] == pytest.approx(232.29678195015583)


def test_nmc622_pack_feedstock_drives_generic_preprocessing_formulas():
    base = default_scenario()
    scenario = Scenario(
        **{
            **base.__dict__,
            "feedstock_chemistry": "NMC(622)",
            "feedstock_type": "End-of-life battery: pack",
            "feedstock_tonnes_per_year": 10000,
            "feedstocks": (FeedstockInput("NMC(622)", "End-of-life battery: pack", 10000),),
        }
    )

    composition = preprocessing_feedstock_composition(scenario).set_index("material")
    products = preprocessing_product_outputs(scenario).set_index("product")
    black_mass = preprocessing_black_mass_composition(scenario).set_index("component")
    costs = preprocessing_cost_summary(scenario).set_index("item")

    assert preprocessing_throughput(scenario) == 10000
    assert composition.loc["Active cathode material", "kg_per_kg_feedstock"] == pytest.approx(0.27773172591601875)
    assert composition.loc["Aluminum", "kg_per_kg_feedstock"] == pytest.approx(0.11947395788122792)
    assert products.loc["Black mass", "kg_per_kg_feedstock"] == pytest.approx(0.4392031531424168)
    assert products.loc["Copper", "kg_per_kg_feedstock"] == pytest.approx(0.06537785446393655)
    assert black_mass.loc["NMC(622)", "fraction_of_black_mass"] == pytest.approx(0.6007359868262668)
    assert black_mass.loc["Graphite", "fraction_of_black_mass"] == pytest.approx(0.36382821104978386)
    assert costs.loc["Total cost ($/kg feedstock processed)", "value"] == pytest.approx(29.103150893041146)
