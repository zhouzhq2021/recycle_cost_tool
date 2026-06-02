import pytest
import pandas as pd
from recycle_cost.model import FeedstockInput, Scenario, default_scenario
from recycle_cost.preprocessing import (
    preprocessing_throughput,
    preprocessing_equipment_table,
    preprocessing_capex_summary,
    preprocessing_opex_summary,
    preprocessing_cost_summary
)

def test_default_scenario_preprocessing_cost():
    scenario = default_scenario()
    # For Black mass, preprocessing throughput should be 0
    assert preprocessing_throughput(scenario) == 0
    
    costs = preprocessing_cost_summary(scenario).set_index("item")
    assert costs.loc["Total capital investment ($)", "value"] == 0
    assert costs.loc["Cash cost of production ($/yr)", "value"] == 0
    assert costs.loc["Total cost ($/kg feedstock processed)", "value"] == 0

def test_nmc622_pack_preprocessing_cost():
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
    
    throughput = preprocessing_throughput(scenario)
    assert throughput == 10000
    
    equipment = preprocessing_equipment_table(scenario)
    assert not equipment.empty
    assert equipment["equipment_cost"].sum() > 0
    
    capex = preprocessing_capex_summary(scenario).set_index("item")
    assert capex.loc["Fixed capital investment", "value"] > 0
    
    opex = preprocessing_opex_summary(scenario).set_index("item")
    assert opex.loc["Operating labor", "value"] > 0
    assert opex.loc["Total cost of production", "value"] > 0
    
    costs = preprocessing_cost_summary(scenario).set_index("item")
    # Verified against manual check or reasonable ranges
    # Purchased Equipment should be around 4.03M * regional_cost_factor(1.0) = 4.03M
    # Fixed Capital should be around 4.03M * (1 + 0.5 + 0.6 + 0.3 + 0.2 + 0.3 + 0.2 + 0.1) + OSBL + Design + Contingency
    # ISBL = 4.03M * 3.2 = 12.9M
    # Fixed Capital = 12.9M * 1.4 (OSBL) * 1.25 (Design) * 1.1 (Contingency) approx...
    # Actually my capex_summary uses specific multipliers.
    
    assert costs.loc["Fixed capital investment ($)", "value"] > 10000000 # > 10M
    assert costs.loc["Cash cost of production ($/yr)", "value"] > 1000000 # > 1M
    
    # Positive feedstock fees are included as raw material cost in the workbook formula.
    total_cost_per_kg = costs.loc["Total cost ($/kg feedstock processed)", "value"]
    assert total_cost_per_kg == pytest.approx(29.103150893041146)

def test_preprocessing_cost_scaling():
    base = default_scenario()
    def get_cost(tpy):
        s = Scenario(
            **{
                **base.__dict__,
                "feedstock_type": "End-of-life battery: pack",
                "feedstocks": (FeedstockInput("NMC(622)", "End-of-life battery: pack", tpy),),
            }
        )
        return preprocessing_cost_summary(s).set_index("item").loc["Total cost ($/kg feedstock processed)", "value"]
    
    cost_10k = get_cost(10000)
    cost_20k = get_cost(20000)
    
    # Economies of scale: cost per kg should decrease as throughput increases
    assert cost_20k < cost_10k
