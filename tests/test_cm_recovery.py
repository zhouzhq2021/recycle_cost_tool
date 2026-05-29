import pytest
from recycle_cost.model import FeedstockInput, Scenario, default_scenario
from recycle_cost.cm_recovery import (
    cm_recovery_throughput,
    cm_recovery_cost_summary,
    cm_recovery_capex_summary,
    cm_recovery_opex_summary,
    cm_recovery_product_outputs,
    cm_recovery_revenue_output_table,
    cm_recovery_revenue_per_kg_feed,
)

def test_pyro_recovery_cost_default():
    base = default_scenario()
    scenario = Scenario(**{**base.__dict__, "manufacturing_location": "China"})
    throughput = cm_recovery_throughput(scenario)
    assert throughput == 10000

    costs = cm_recovery_cost_summary(scenario, "Pyro").set_index("item")

    total_cost = costs.loc["Total cost ($/kg black mass processed)", "value"]
    fixed_capital = costs.loc["Fixed capital investment ($)", "value"]

    assert fixed_capital == pytest.approx(75592543.84309334)
    assert total_cost == pytest.approx(4.7209338121193545)

def test_hydro_recovery_cost_default():
    base = default_scenario()
    scenario = Scenario(**{**base.__dict__, "manufacturing_location": "China"})
    costs = cm_recovery_cost_summary(scenario, "Hydro").set_index("item")

    total_cost = costs.loc["Total cost ($/kg black mass processed)", "value"]
    assert total_cost == pytest.approx(5.090005111487754)

def test_direct_recovery_cost_default():
    base = default_scenario()
    scenario = Scenario(**{**base.__dict__, "manufacturing_location": "China"})
    costs = cm_recovery_cost_summary(scenario, "Direct").set_index("item")

    total_cost = costs.loc["Total cost ($/kg black mass processed)", "value"]
    fixed_capital = costs.loc["Fixed capital investment ($)", "value"]

    assert fixed_capital == pytest.approx(56957381.00711118)
    assert total_cost == pytest.approx(6.584075479342885)


def test_cm_recovery_opex_matches_workbook_default():
    base = default_scenario()
    scenario = Scenario(**{**base.__dict__, "manufacturing_location": "China"})

    expected = {
        "Pyro": {
            "Variable costs of production": 32357723.688910976,
            "Fixed costs of production": 6870396.681543301,
            "Working capital": 5405261.819937901,
            "Annualized capital cost": 7981217.750739242,
        },
        "Hydro": {
            "Variable costs of production": 41533923.86166618,
            "Fixed costs of production": 5169874.53104399,
            "Working capital": 5513445.38575069,
            "Annualized capital cost": 4196252.722167366,
        },
        "Direct": {
            "Variable costs of production": 52873938.951833054,
            "Fixed costs of production": 6953137.279948758,
            "Working capital": 6995755.364851855,
            "Annualized capital cost": 6013678.561647034,
        },
    }

    for process, values in expected.items():
        opex = cm_recovery_opex_summary(scenario, process).set_index("item")
        for item, expected_value in values.items():
            assert opex.loc[item, "value"] == pytest.approx(expected_value)


def test_cm_recovery_variable_opex_scales_with_throughput():
    base = default_scenario()
    scenario = Scenario(**{**base.__dict__, "manufacturing_location": "China"})
    doubled = Scenario(
        **{
            **scenario.__dict__,
            "feedstock_tonnes_per_year": 20000,
            "feedstocks": (FeedstockInput("NMC(622)", "Black mass", 20000),),
        }
    )

    base_opex = cm_recovery_opex_summary(scenario, "Hydro").set_index("item")
    doubled_opex = cm_recovery_opex_summary(doubled, "Hydro").set_index("item")

    for item in ["Raw Materials", "Utilities", "Effluent disposal", "Variable costs of production"]:
        assert doubled_opex.loc[item, "value"] == pytest.approx(base_opex.loc[item, "value"] * 2)


def test_cm_recovery_capex_matches_workbook_default():
    base = default_scenario()
    scenario = Scenario(**{**base.__dict__, "manufacturing_location": "China"})

    expected = {
        "Pyro": 75592543.84309334,
        "Hydro": 39743987.41943308,
        "Direct": 56957381.00711118,
    }

    for process, expected_value in expected.items():
        capex = cm_recovery_capex_summary(scenario, process).set_index("item")
        assert capex.loc["Fixed capital investment", "value"] == pytest.approx(expected_value)


def test_cm_recovery_revenue_output_table_uses_scenario_formula_outputs():
    revenue = cm_recovery_revenue_output_table().set_index(["process", "material"])

    assert revenue.loc[("Pyro", "Copper metal"), "source_row"] == 127
    assert revenue.loc[("Pyro", "Co2+ in product"), "calculated_value_per_kg_feedstock"] == pytest.approx(
        3.5115060841972157
    )
    assert revenue.loc[("Hydro", "Graphite"), "calculated_value_per_kg_feedstock"] == pytest.approx(
        0.06580909387258863
    )
    assert revenue.loc[("Hydro", "Copper"), "calculated_value_per_kg_feedstock"] == pytest.approx(
        0.06629396654724373
    )
    assert revenue.loc[("Direct", "NMC(622)"), "calculated_value_per_kg_feedstock"] == pytest.approx(
        13.582609095794663
    )
    assert revenue.loc[("Custom", "Copper"), "source_row"] == 134
    assert revenue.loc[("Custom", "Copper"), "calculated_value_per_kg_feedstock"] == pytest.approx(
        0.06629396654724373
    )
    assert ("Pyro", "Flue Dust") not in revenue.index


def test_cm_recovery_revenue_changes_with_scenario_feedstock_chemistry():
    base = default_scenario()
    lfp = Scenario(
        **{
            **base.__dict__,
            "feedstock_chemistry": "LFP",
            "feedstock_type": "Black mass",
            "feedstock_tonnes_per_year": 10000,
            "feedstocks": (FeedstockInput("LFP", "Black mass", 10000),),
        }
    )
    nmc811 = Scenario(
        **{
            **base.__dict__,
            "feedstock_chemistry": "NMC(811)",
            "feedstock_type": "Black mass",
            "feedstock_tonnes_per_year": 10000,
            "feedstocks": (FeedstockInput("NMC(811)", "Black mass", 10000),),
        }
    )

    lfp_direct = cm_recovery_product_outputs(lfp, "Direct").set_index("product")
    nmc811_direct = cm_recovery_product_outputs(nmc811, "Direct").set_index("product")

    assert "LFP" in lfp_direct.index
    assert "NMC(811)" in nmc811_direct.index
    assert "NMC(622)" not in lfp_direct.index
    assert cm_recovery_revenue_per_kg_feed(lfp, "Pyro") == pytest.approx(0.09205308067415952)
    assert cm_recovery_revenue_per_kg_feed(nmc811, "Pyro") == pytest.approx(6.212498037288018)
    assert cm_recovery_revenue_per_kg_feed(lfp, "Direct") != pytest.approx(
        cm_recovery_revenue_per_kg_feed(nmc811, "Direct")
    )


def test_lco_recovery_uses_lco_elemental_mass():
    base = default_scenario()
    scenario = Scenario(
        **{
            **base.__dict__,
            "feedstock_chemistry": "LCO",
            "feedstock_type": "Black mass",
            "feedstock_tonnes_per_year": 10000,
            "feedstocks": (FeedstockInput("LCO", "Black mass", 10000),),
        }
    )

    products = cm_recovery_product_outputs(scenario, "Pyro").set_index("product")

    assert products.loc["Co2+ in product", "kg_per_kg_black_mass"] > 0
    assert "Ni2+ in product" not in products.index
