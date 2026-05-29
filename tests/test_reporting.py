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
    assert summary.loc[("Recycle", "GHGs", "Hydro"), AuditColumns.PYTHON_VALUE] == pytest.approx(32462.702189542604)
    assert summary.loc[("Cathode Production", "Total Energy", "Pyro"), AuditColumns.PYTHON_VALUE] == pytest.approx(47.46026348224687)


def test_python_ported_output_recycling_revenue_table_default():
    scenario = get_scenario_from_preset("pack_hydro")
    table = python_ported_output_recycling_revenue_table(scenario).set_index([CommonColumns.PROCESS, CommonColumns.MATERIAL])

    assert table.loc[("Hydro", "Copper"), AuditColumns.PYTHON_VALUE] == pytest.approx(0.0529302, abs=1e-6)
    assert table.loc[("Direct", "NMC(622)"), AuditColumns.PYTHON_VALUE] == pytest.approx(13.516559703591005)


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


@pytest.mark.parametrize(
        ("process", "obtained_cost"),
        [
        ("Pyro", 7.271354),
        ("Hydro", 6.543381),
        ("Direct", 8.256734),
        ],
)
def test_python_ported_stage_summary_nmc622_pack_recycling_routes(process, obtained_cost):
    scenario = get_scenario_from_preset("pack_hydro")
    summary = python_ported_stage_summary(scenario, process).set_index(StageSummaryColumns.STAGE)

    assert summary.loc["CM Recovery", StageSummaryColumns.PROCESS] == process
    assert summary.loc["CM Recovery", StageSummaryColumns.COST] == pytest.approx(obtained_cost, abs=1e-4)
    assert summary.loc["Material Conversion", StageSummaryColumns.COST] == pytest.approx(2.4615911, abs=1e-6)
