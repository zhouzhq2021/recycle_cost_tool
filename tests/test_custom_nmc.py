import pytest

from recycle_cost.app_services import (
    custom_feedstock_composition_table,
    parameter_tables_for_scenario,
    scenario_display_table,
    scenario_from_inputs,
    scenario_from_record,
    scenario_record,
)
from recycle_cost.cm_recovery import cm_recovery_product_outputs
from recycle_cost.model import FeedstockInput, Scenario, get_scenario_from_preset
from recycle_cost.preprocessing import (
    default_custom_feedstock_composition,
    preprocessing_black_mass_composition,
    preprocessing_feedstock_composition,
    preprocessing_product_outputs,
)


def _custom_nmc_scenario(**overrides) -> Scenario:
    base = get_scenario_from_preset("pack_hydro")
    values = {
        **base.__dict__,
        "feedstock_chemistry": "Custom NMC",
        "cathode_chemistry": "Custom NMC",
        "manufacturing_chemistry": "Custom NMC",
        "feedstocks": (FeedstockInput("Custom NMC", "End-of-life battery: pack", 10000),),
        "custom_nmc_ni": 8.0,
        "custom_nmc_co": 1.0,
        "custom_nmc_mn": 1.0,
    }
    values.update(overrides)
    return Scenario(**values)


def test_scenario_inputs_and_record_preserve_custom_nmc_ratio():
    custom_composition = {
        **default_custom_feedstock_composition("End-of-life battery: pack"),
        "Active cathode material": 0.35,
        "Graphite": 0.12,
    }
    scenario = scenario_from_inputs(
        battery_manufactured="Pack",
        throughput_gwh_per_year=50.0,
        manufacturing_chemistry="Custom NMC",
        manufacturing_location="U.S.",
        battery_collected="Module",
        feedstock_chemistry="Custom NMC",
        feedstock_type="End-of-life battery: pack",
        feedstock_tonnes_per_year=10000.0,
        recycling_process="Hydrometallurgical",
        cathode_chemistry="Custom NMC",
        recycled_content=0.2,
        cathode_throughput_gwh_per_year=10.0,
        collection_to_disassembly=1.0,
        disassembly_to_preprocessor=2.0,
        preprocessor_to_cm_recovery=3.0,
        manufacturer_to_preprocessor_or_cm_recovery=4.0,
        recycler_to_cathode_producer=5.0,
        cathode_producer_to_manufacturer=6.0,
        custom_nmc_ni=8.0,
        custom_nmc_co=1.0,
        custom_nmc_mn=1.0,
        custom_feedstock_composition=custom_composition,
        custom_feedstock_composition_feedstock_type="End-of-life battery: pack",
    )

    record = scenario_record(scenario)
    restored = scenario_from_record(record, get_scenario_from_preset("pack_hydro"))

    assert scenario.feedstocks[0].chemistry == "Custom NMC"
    assert record["custom_nmc_ni"] == 8.0
    assert record["custom_nmc_co"] == 1.0
    assert record["custom_nmc_mn"] == 1.0
    assert record["custom_feedstock_composition"]["Active cathode material"] == 0.35
    assert record["custom_feedstock_composition"]["Graphite"] == 0.12
    assert record["custom_feedstock_composition_feedstock_type"] == "End-of-life battery: pack"
    assert restored.custom_feedstock_composition_feedstock_type == "End-of-life battery: pack"
    assert restored.custom_feedstock_composition["Active cathode material"] == pytest.approx(0.35)


def test_custom_nmc_black_mass_keeps_custom_active_material_label():
    scenario = _custom_nmc_scenario()
    black_mass = preprocessing_black_mass_composition(scenario).set_index("component")

    assert black_mass.loc["Custom NMC", "fraction_of_black_mass"] == pytest.approx(0.6007359868262668)
    assert black_mass.loc["NMC(622)", "fraction_of_black_mass"] == 0.0


def test_custom_nmc_hydro_products_follow_user_ratio():
    scenario = _custom_nmc_scenario()
    products = cm_recovery_product_outputs(scenario, "Hydro").set_index("product")

    assert products.loc["Ni2+ in product", "kg_per_kg_black_mass"] == pytest.approx(0.284161, abs=1e-6)
    assert products.loc["Co2+ in product", "kg_per_kg_black_mass"] == pytest.approx(0.035665, abs=1e-6)
    assert products.loc["Mn2+ in product", "kg_per_kg_black_mass"] == pytest.approx(0.033248, abs=1e-6)


def test_custom_nmc_new_direct_outputs_rejuvenated_custom_material():
    scenario = _custom_nmc_scenario(recycling_process="Direct", recycling_flow_variant="new")
    products = cm_recovery_product_outputs(scenario, "Direct").set_index("product")

    assert "Rejuvenated Custom NMC" in products.index
    assert products.loc["Rejuvenated Custom NMC", "kg_per_kg_black_mass"] == pytest.approx(0.964413)


def test_custom_feedstock_composition_replaces_nmc622_baseline():
    composition = {
        **default_custom_feedstock_composition("End-of-life battery: pack"),
        "Active cathode material": 0.35,
        "Graphite": 0.1,
        "Aluminum": 0.05,
    }
    scenario = _custom_nmc_scenario(custom_feedstock_composition=composition)
    feedstock = preprocessing_feedstock_composition(scenario).set_index("material")

    assert feedstock.loc["Active cathode material", "kg_per_kg_feedstock"] == pytest.approx(0.35)
    assert feedstock.loc["Graphite", "kg_per_kg_feedstock"] == pytest.approx(0.1)
    assert feedstock.loc["Aluminum", "kg_per_kg_feedstock"] == pytest.approx(0.05)


def test_custom_feedstock_composition_changes_legacy_black_mass_yield():
    composition = {
        **default_custom_feedstock_composition("End-of-life battery: pack"),
        "Active cathode material": 0.35,
        "Graphite": 0.1,
        "Carbon black": 0.02,
        "Binder: PVDF": 0.0,
        "Binder: anode": 0.0,
        "Copper": 0.0,
        "Aluminum": 0.0,
    }
    scenario = _custom_nmc_scenario(custom_feedstock_composition=composition)
    products = preprocessing_product_outputs(scenario).set_index("product")
    black_mass = preprocessing_black_mass_composition(scenario).set_index("component")

    assert products.loc["Black mass", "kg_per_kg_feedstock"] == pytest.approx((0.35 + 0.1 + 0.02) * 0.95)
    assert black_mass.loc["Custom NMC", "fraction_of_black_mass"] == pytest.approx(0.35 * 0.95 / ((0.35 + 0.1 + 0.02) * 0.95))


def test_custom_feedstock_composition_changes_new_preprocessing_outputs():
    composition = {
        **default_custom_feedstock_composition("End-of-life battery: pack"),
        "Active cathode material": 0.4,
        "Graphite": 0.2,
        "Carbon black": 0.02,
        "Binder: PVDF": 0.0,
        "Binder: anode": 0.0,
    }
    scenario = _custom_nmc_scenario(recycling_process="Direct", recycling_flow_variant="new", custom_feedstock_composition=composition)
    products = preprocessing_product_outputs(scenario).set_index("product")

    assert products.loc["S-Cathode", "kg_per_kg_feedstock"] == pytest.approx(0.4 * 0.985 + 0.02 * 0.25)
    assert products.loc["S-Anode", "kg_per_kg_feedstock"] == pytest.approx(0.2 * 0.94 + 0.02 * 0.75)


def test_custom_feedstock_composition_is_ignored_for_mismatched_feedstock_type():
    pack_composition = {
        **default_custom_feedstock_composition("End-of-life battery: pack"),
        "Active cathode material": 0.9,
    }
    scenario = _custom_nmc_scenario(
        feedstock_type="End-of-life battery: module",
        feedstocks=(FeedstockInput("Custom NMC", "End-of-life battery: module", 10000),),
        custom_feedstock_composition=pack_composition,
        custom_feedstock_composition_feedstock_type="End-of-life battery: pack",
    )
    feedstock = preprocessing_feedstock_composition(scenario).set_index("material")

    assert feedstock.loc["Active cathode material", "kg_per_kg_feedstock"] == pytest.approx(
        default_custom_feedstock_composition("End-of-life battery: module")["Active cathode material"]
    )


def test_custom_feedstock_composition_appears_in_scenario_display():
    composition = default_custom_feedstock_composition("End-of-life battery: module")
    scenario = _custom_nmc_scenario(
        feedstock_type="End-of-life battery: module",
        feedstocks=(FeedstockInput("Custom NMC", "End-of-life battery: module", 10000),),
        custom_feedstock_composition=composition,
        custom_feedstock_composition_feedstock_type="End-of-life battery: module",
    )
    text = {
        "battery_manufactured": "battery",
        "throughput": "throughput",
        "manufacturing_chemistry": "mfg chemistry",
        "manufacturing_location": "location",
        "battery_collected": "collected",
        "feedstock_chemistry": "feed chemistry",
        "feedstock_type": "feed type",
        "feedstock_tonnes": "feed tonnes",
        "recycling_process": "process",
        "cathode_chemistry": "cathode",
        "cathode_throughput": "cathode throughput",
        "recycled_content": "recycled",
        "collection_to_disassembly": "route a",
        "disassembly_to_preprocessor": "route b",
        "preprocessor_to_cm": "route c",
        "manufacturer_to_preprocessor": "route d",
        "recycler_to_cathode": "route e",
        "cathode_to_manufacturer": "route f",
        "custom_nmc_ratio": "ratio",
        "custom_feedstock_composition_feedstock_type": "composition type",
        "custom_feedstock_summary": "composition total",
        "field": "field",
        "value": "value",
    }
    display = scenario_display_table(scenario, text).set_index("field")

    assert display.loc["ratio", "value"] == "8/1/1"
    assert display.loc["composition type", "value"] == "End-of-life battery: module"
    assert display.loc["composition total", "value"] == pytest.approx(1.0)


def test_custom_feedstock_composition_table_compares_with_default():
    composition = {
        **default_custom_feedstock_composition("End-of-life battery: pack"),
        "Active cathode material": 0.35,
    }
    scenario = _custom_nmc_scenario(
        custom_feedstock_composition=composition,
        custom_feedstock_composition_feedstock_type="End-of-life battery: pack",
    )
    table = custom_feedstock_composition_table(scenario).set_index("material")

    assert table.loc["Active cathode material", "custom_kg_per_kg_feedstock"] == pytest.approx(0.35)
    assert table.loc["Active cathode material", "delta"] == pytest.approx(
        0.35 - default_custom_feedstock_composition("End-of-life battery: pack")["Active cathode material"]
    )


def test_parameter_tables_include_custom_feedstock_composition_table():
    composition = {
        **default_custom_feedstock_composition("End-of-life battery: pack"),
        "Graphite": 0.22,
    }
    scenario = _custom_nmc_scenario(
        custom_feedstock_composition=composition,
        custom_feedstock_composition_feedstock_type="End-of-life battery: pack",
    )
    tables = parameter_tables_for_scenario(scenario, "Hydro")
    table = tables["Custom feedstock composition"].set_index("material")

    assert table.loc["Graphite", "custom_kg_per_kg_feedstock"] == pytest.approx(0.22)
    assert "delta" in table.columns
