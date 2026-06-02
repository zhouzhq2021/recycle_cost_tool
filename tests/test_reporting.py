import pytest

from recycle_cost.model import Scenario, get_scenario_from_preset, FeedstockInput
from recycle_cost.reporting import (
    python_ported_process_stage_output_summary,
    python_ported_output_recycling_revenue_table,
    python_ported_output_cost_breakdown,
    python_ported_report_manufacturing_comparison,
    python_ported_report_closed_loop_total_results,
    python_ported_report_comparison,
    python_ported_manufacturing_output_summary,
    python_ported_output_summary_table,
    python_ported_stage_summary,
)
from recycle_cost.schemas import CommonColumns, AuditColumns, StageSummaryColumns, OutputSummaryColumns


def test_python_ported_process_stage_output_summary_default():
    scenario = get_scenario_from_preset("pack_hydro")
    summary = python_ported_process_stage_output_summary(scenario).set_index([StageSummaryColumns.STAGE, CommonColumns.METRIC, "column"])

    assert summary.loc[("Collection & Transport", "Cost per kgfeedstock", "total"), AuditColumns.PYTHON_VALUE] == pytest.approx(0.0321027, abs=1e-6)
    assert summary.loc[("Recycle", "Cost per kg feedstock processed", "Hydro"), AuditColumns.PYTHON_VALUE] == pytest.approx(33.88709743614676)
    assert summary.loc[("Recycle", "GHGs", "Hydro"), AuditColumns.PYTHON_VALUE] == pytest.approx(32846.87316477094)
    assert summary.loc[("Cathode Production", "Total Energy", "Pyro"), AuditColumns.PYTHON_VALUE] == pytest.approx(47.46026348224687)


def test_python_ported_output_recycling_revenue_table_default():
    scenario = get_scenario_from_preset("pack_hydro")
    table = python_ported_output_recycling_revenue_table(scenario).set_index([CommonColumns.PROCESS, CommonColumns.MATERIAL])

    assert table.loc[("Hydro", "Co2+ in product"), AuditColumns.PYTHON_VALUE] == pytest.approx(6.3445436208)
    assert table.loc[("Direct", "NMC(622)"), AuditColumns.PYTHON_VALUE] == pytest.approx(14.25)


def test_python_ported_output_cost_breakdown_default():
    breakdown = python_ported_output_cost_breakdown(include_workbook=True).set_index(["section", CommonColumns.ITEM, "column"])

    assert breakdown.loc[("Battery production cost", "Materials", "recycled materials from hydro"), AuditColumns.PYTHON_VALUE] >= 0.0
    assert breakdown.loc[("Recycling cost", "Labor", "Hydro"), AuditColumns.PYTHON_VALUE] == pytest.approx(0.0)


def test_python_ported_report_manufacturing_comparison_default():
    comparison = python_ported_report_manufacturing_comparison().set_index(CommonColumns.METRIC)

    # Virgin Manufacture cost - NMC(622) Pack is approx 93.5 $/kWh in current logic
    assert comparison.loc["Cost ($)", "Virgin Manufacture"] == pytest.approx(93.51878, abs=1e-3)


def test_python_ported_report_closed_loop_total_results_default():
    scenario = get_scenario_from_preset("pack_hydro")
    results = python_ported_report_closed_loop_total_results(scenario).set_index(CommonColumns.METRIC)

    # Cost ($) for Pyro in nmc622_pack scenario
    assert results.loc["Cost ($)", "Pyro"] > 0.0
    assert results.loc["GHG emission (g CO2e)", "Hydro"] == pytest.approx(3191.98449, abs=1e-3)


def test_python_ported_report_comparison_default():
    scenario = get_scenario_from_preset("pack_hydro")
    comparison = python_ported_report_comparison(scenario).set_index(["section", CommonColumns.METRIC])

    assert comparison.loc[("Manufacturing", "Cost ($)"), "Virgin Manufacture"] == pytest.approx(93.51878, abs=1e-3)


def test_python_ported_manufacturing_output_summary_default():
    summary = python_ported_manufacturing_output_summary().set_index(CommonColumns.METRIC)

    assert summary.loc["Cost per kWh batttery produced", "python_virgin_cell"] == pytest.approx(93.51878, abs=1e-3)


def test_python_ported_output_summary_table_default():
    scenario = get_scenario_from_preset("pack_hydro")
    table = python_ported_output_summary_table(scenario).set_index(CommonColumns.METRIC)

    assert table.loc["Cell manufacturing cost", "Virgin"] == pytest.approx(93.51878, abs=1e-3)
    assert table.loc["Cell manufacturing cost", "Hydro"] != table.loc["Cell manufacturing cost", "Hydro"]
    assert table.loc["Recycling total energy", "Hydro"] == pytest.approx(417.311924837617)
    assert table.loc["Recycling water", "Hydro"] == pytest.approx(53.22709554362699)
    assert table.loc["Recycling GHGs", "Hydro"] == pytest.approx(32846.87316477094)


def test_python_ported_output_summary_scrap_direct_documents_current_python_path():
    scenario = get_scenario_from_preset("scrap_direct")
    table = python_ported_output_summary_table(scenario).set_index(CommonColumns.METRIC)

    assert table.loc["Recycling cost", "Direct"] == pytest.approx(33.20220650827327)
    assert table.loc["Recycling GHGs", "Direct"] == pytest.approx(7610.990429185895)


def test_output_summary_recycled_manufacturing_environment_uses_scenario_content():
    scenario = get_scenario_from_preset("pack_direct")
    table = python_ported_output_summary_table(scenario).set_index(CommonColumns.METRIC)

    assert table.loc["Cell manufacturing total energy", "Direct"] == pytest.approx(890.721898761395)
    assert table.loc["Cell manufacturing water", "Direct"] == pytest.approx(60.9690912688901)
    assert table.loc["Cell manufacturing GHGs", "Direct"] == pytest.approx(63464.3860198095)


@pytest.mark.parametrize(
    ("chemistry", "expected_cost", "expected_energy", "expected_water", "expected_ghg"),
    [
        ("LFP", 86.14106935709425, 774.9659819648717, 46.60833574434578, 54289.42214748489),
        ("NCA", 91.75953647298617, 1030.1916809874078, 63.88310770261307, 70933.59182043519),
        ("NMC(811)", 88.6185805475398, 958.6612433544608, 57.81508371983569, 65991.28841192384),
    ],
)
def test_output_summary_virgin_manufacturing_chemistry_excel_parity(
    chemistry,
    expected_cost,
    expected_energy,
    expected_water,
    expected_ghg,
):
    base = get_scenario_from_preset("pack_hydro")
    scenario = Scenario(
        **{
            **base.__dict__,
            "manufacturing_chemistry": chemistry,
            "feedstock_chemistry": chemistry,
            "cathode_chemistry": chemistry,
            "feedstocks": (FeedstockInput(chemistry, "End-of-life battery: pack", 10000),),
        }
    )
    table = python_ported_output_summary_table(scenario).set_index(CommonColumns.METRIC)

    assert table.loc["Cell manufacturing cost", "Virgin"] == pytest.approx(expected_cost)
    assert table.loc["Cell manufacturing total energy", "Virgin"] == pytest.approx(expected_energy)
    assert table.loc["Cell manufacturing water", "Virgin"] == pytest.approx(expected_water)
    assert table.loc["Cell manufacturing GHGs", "Virgin"] == pytest.approx(expected_ghg)


@pytest.mark.parametrize(
    ("scenario", "process", "expected_ghg"),
    [
        (
            Scenario(
                **{
                    **get_scenario_from_preset("default").__dict__,
                    "recycling_process": "Pyrometallurgical",
                }
            ),
            "Pyro",
            37112.2536909963,
        ),
        (
            Scenario(
                **{
                    **get_scenario_from_preset("pack_pyro").__dict__,
                    "feedstock_chemistry": "LFP",
                    "cathode_chemistry": "LFP",
                    "feedstocks": (FeedstockInput("LFP", "End-of-life battery: pack", 10000),),
                }
            ),
            "Pyro",
            36662.7762592468,
        ),
        (
            Scenario(
                **{
                    **get_scenario_from_preset("pack_hydro").__dict__,
                    "battery_manufactured": "Module",
                    "battery_collected": "Cell",
                    "feedstock_type": "End-of-life battery: module",
                    "feedstock_tonnes_per_year": 8000,
                    "feedstocks": (FeedstockInput("NMC(622)", "End-of-life battery: module", 8000),),
                }
            ),
            "Hydro",
            32912.2103578861,
        ),
    ],
)
def test_recycling_ghg_feedstock_specific_excel_parity(scenario, process, expected_ghg):
    table = python_ported_output_summary_table(scenario).set_index(CommonColumns.METRIC)

    assert table.loc["Recycling GHGs", process] == pytest.approx(expected_ghg)


@pytest.mark.parametrize(
    ("scenario", "process", "expected_revenue"),
    [
        (
            Scenario(
                **{
                    **get_scenario_from_preset("pack_pyro").__dict__,
                    "feedstock_chemistry": "LFP",
                    "cathode_chemistry": "LFP",
                    "feedstocks": (FeedstockInput("LFP", "End-of-life battery: pack", 10000),),
                }
            ),
            "Pyro",
            8.23602812394,
        ),
        (
            Scenario(
                **{
                    **get_scenario_from_preset("pack_direct").__dict__,
                    "feedstock_chemistry": "NCA",
                    "feedstock_tonnes_per_year": 9000,
                    "cathode_chemistry": "NCA",
                    "cathode_throughput_gwh_per_year": 9,
                    "feedstocks": (FeedstockInput("NCA", "End-of-life battery: pack", 9000),),
                }
            ),
            "Direct",
            14.3507105288748,
        ),
    ],
)
def test_output_summary_revenue_uses_excel_output_total_cache(scenario, process, expected_revenue):
    table = python_ported_output_summary_table(scenario).set_index(CommonColumns.METRIC)

    assert table.loc["Recycling revenue", process] == pytest.approx(expected_revenue)


@pytest.mark.parametrize(
    ("scenario", "process", "expected_cost"),
    [
        (
            Scenario(
                **{
                    **get_scenario_from_preset("pack_hydro").__dict__,
                    "battery_manufactured": "Module",
                    "battery_collected": "Cell",
                    "feedstock_type": "End-of-life battery: module",
                    "feedstock_tonnes_per_year": 8000,
                    "feedstocks": (FeedstockInput("NMC(622)", "End-of-life battery: module", 8000),),
                }
            ),
            "Hydro",
            33.1876580451194,
        ),
        (
            Scenario(
                **{
                    **get_scenario_from_preset("pack_pyro").__dict__,
                    "feedstock_chemistry": "LFP",
                    "cathode_chemistry": "LFP",
                    "feedstocks": (FeedstockInput("LFP", "End-of-life battery: pack", 10000),),
                }
            ),
            "Pyro",
            33.5164638397891,
        ),
        (
            Scenario(
                **{
                    **get_scenario_from_preset("default").__dict__,
                    "recycling_process": "Direct",
                    "feedstock_chemistry": "LFP",
                    "feedstock_type": "Black mass",
                    "feedstock_tonnes_per_year": 9000,
                    "cathode_chemistry": "LFP",
                    "feedstocks": (FeedstockInput("LFP", "Black mass", 9000),),
                }
            ),
            "Direct",
            6.05247093989836,
        ),
    ],
)
def test_output_summary_recycling_cost_excel_parity_for_matrix_cases(scenario, process, expected_cost):
    table = python_ported_output_summary_table(scenario).set_index(CommonColumns.METRIC)

    assert table.loc["Recycling cost", process] == pytest.approx(expected_cost)


@pytest.mark.parametrize(
        ("process", "obtained_cost"),
        [
        ("Pyro", 5.537501),
        ("Hydro", 5.508471),
        ("Direct", 7.196859),
        ],
)
def test_python_ported_stage_summary_nmc622_pack_recycling_routes(process, obtained_cost):
    scenario = get_scenario_from_preset("pack_hydro")
    summary = python_ported_stage_summary(scenario, process).set_index(StageSummaryColumns.STAGE)

    assert summary.loc["CM Recovery", StageSummaryColumns.PROCESS] == process
    assert summary.loc["CM Recovery", StageSummaryColumns.COST] == pytest.approx(obtained_cost, abs=1e-4)
    assert summary.loc["Material Conversion", StageSummaryColumns.COST] == pytest.approx(2.4615911, abs=1e-6)
