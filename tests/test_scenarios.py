import pytest
from recycle_cost.model import default_scenario, Scenario, FeedstockInput, get_scenario_from_preset
from recycle_cost.mat_conv import mat_conv_available_precursors
from recycle_cost.cathode import cathode_chemistry_for_scenario, cathode_raw_material_cost_summary
from recycle_cost.transport import scenario_transport_segments, transport_environment_breakdown
from recycle_cost.mat_conv import mat_conv_recycling_environment_summary_calculated
from recycle_cost.schemas import CommonColumns, AuditColumns, ManufacturingColumns


def test_mat_conv_feedstock_chemistry_impact():
    # Use pack_hydro as base for better material flow visibility
    base = get_scenario_from_preset("pack_hydro")
    
    # Test NMC(111)
    nmc111 = Scenario(**{**base.__dict__, "feedstocks": (FeedstockInput("NMC(111)", "End-of-life battery: pack", 10000.0),)})
    precursors_111 = mat_conv_available_precursors(nmc111, "Hydro").set_index(CommonColumns.MATERIAL)
    # 111 has less Ni than 622
    assert precursors_111.loc["Nickel Sulfate", "kg_per_kg_feedstock"] < 0.4
    assert precursors_111.loc["Nickel Sulfate", "kg_per_kg_feedstock"] == pytest.approx(0.32754059474256936)
    
    # Test NMC(811)
    nmc811 = Scenario(**{**base.__dict__, "feedstocks": (FeedstockInput("NMC(811)", "End-of-life battery: pack", 10000.0),)})
    precursors_811 = mat_conv_available_precursors(nmc811, "Hydro").set_index(CommonColumns.MATERIAL)
    # 811 has more Ni than 622 (approx 0.72 vs 0.54)
    assert precursors_811.loc["Nickel Sulfate", "kg_per_kg_feedstock"] > 0.6
    assert precursors_811.loc["Nickel Sulfate", "kg_per_kg_feedstock"] == pytest.approx(0.716501353756311)


def test_cathode_chemistry_impact():
    base = default_scenario()
    
    # Let's check NMC(811) which is definitely in PRODUCTION_BLOCKS
    nmc811_scenario = Scenario(**{**base.__dict__, "cathode_chemistry": "NMC(811)"})
    assert cathode_chemistry_for_scenario(nmc811_scenario) == "NMC(811)"
    
    costs_811 = cathode_raw_material_cost_summary(nmc811_scenario, "NMC(811)").set_index(CommonColumns.PROCESS)
    costs_622 = cathode_raw_material_cost_summary(base, "NMC(622)").set_index(CommonColumns.PROCESS)
    
    # Virgin raw material cost should differ
    assert costs_811.loc["Virgin", "raw_material_cost_per_kg"] != costs_622.loc["Virgin", "raw_material_cost_per_kg"]


def test_transport_distance_linkage_to_mat_conv():
    # Use Module collected so first leg is not zero
    base = get_scenario_from_preset("pack_hydro")
    
    # Increase transport distance
    long_dist = Scenario(**{**base.__dict__, 
        "transport_distances": base.transport_distances.__class__(
            **{**base.transport_distances.__dict__, "collection_to_disassembly": 2000.0}
        )
    })
    
    # Verify transport segments updated
    segments_base = scenario_transport_segments(base)
    segments_long = scenario_transport_segments(long_dist)
    assert segments_long[0].total_distance_miles == 2000.0
    assert segments_base[0].total_distance_miles == 100.0
    
    # Verify transport environment updated
    env_base = transport_environment_breakdown(segments=segments_base).set_index(CommonColumns.METRIC)
    env_long = transport_environment_breakdown(segments=segments_long).set_index(CommonColumns.METRIC)
    assert env_long.loc["GHGs", "calculated_total"] > env_base.loc["GHGs", "calculated_total"]
    
    # Verify linkage to mat_conv environmental audit
    mc_env_base = mat_conv_recycling_environment_summary_calculated(base).set_index(CommonColumns.METRIC)
    mc_env_long = mat_conv_recycling_environment_summary_calculated(long_dist).set_index(CommonColumns.METRIC)
    
    assert mc_env_long.loc["GHGs", AuditColumns.calculated("Pyro")] > mc_env_base.loc["GHGs", AuditColumns.calculated("Pyro")]
