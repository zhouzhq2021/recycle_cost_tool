import pandas as pd

from recycle_cost.ui_sections import (
    format_report_number,
    format_report_table,
    production_report_summary_table,
    recycling_report_summary_table,
    recycling_route_comparison_table,
)


def test_format_report_number_uses_stable_precision():
    assert format_report_number(0) == "0.0000"
    assert format_report_number(0.01234567) == "0.012346"
    assert format_report_number(5.0819271) == "5.0819"
    assert format_report_number(32462.70219) == "32,462.70"
    assert format_report_number(None) == ""


def test_format_report_table_formats_numeric_columns():
    table = format_report_table(pd.DataFrame([{"metric": "Cost", "value": 5.0819271}]))

    assert table.loc[0, "metric"] == "Cost"
    assert table.loc[0, "value"] == "5.0819"


def test_recycling_report_summary_table_includes_net_cost():
    output = pd.DataFrame(
        [
            {"metric": "Recycling cost", "Hydro": 10.0},
            {"metric": "Recycling revenue", "Hydro": 2.5},
            {"metric": "Recycling GHGs", "Hydro": 100.0},
            {"metric": "Recycling total energy", "Hydro": 4.0},
            {"metric": "Recycling water", "Hydro": 0.2},
        ]
    )

    summary = recycling_report_summary_table(output, "Hydro").set_index("metric")

    assert summary.loc["Net recycling cost", "Hydro"] == 7.5
    assert summary.loc["Recycling GHGs", "unit"] == "g CO2e/kg feedstock"


def test_recycling_route_comparison_table_includes_all_routes_and_net_cost():
    output = pd.DataFrame(
        [
            {"metric": "Recycling cost", "Pyro": 10.0, "Hydro": 9.0, "Direct": 8.0, "Custom": 7.0},
            {"metric": "Recycling revenue", "Pyro": 1.0, "Hydro": 2.0, "Direct": 3.0, "Custom": 4.0},
            {"metric": "Recycling GHGs", "Pyro": 100.0, "Hydro": 90.0, "Direct": 80.0, "Custom": 70.0},
            {"metric": "Recycling total energy", "Pyro": 10.0, "Hydro": 9.0, "Direct": 8.0, "Custom": 7.0},
            {"metric": "Recycling water", "Pyro": 1.0, "Hydro": 0.9, "Direct": 0.8, "Custom": 0.7},
        ]
    )

    comparison = recycling_route_comparison_table(output).set_index("route")

    assert set(comparison.index) == {"Pyro", "Hydro", "Direct", "Custom"}
    assert comparison.loc["Direct", "net_cost"] == 5.0
    assert comparison.loc["Custom", "ghgs"] == 70.0


def test_production_report_summary_table_extracts_virgin_metrics():
    output = pd.DataFrame(
        [
            {"metric": "Cell manufacturing cost", "Virgin": 101.0},
            {"metric": "Cell manufacturing total energy", "Virgin": 202.0},
            {"metric": "Cell manufacturing water", "Virgin": 3.0},
            {"metric": "Cell manufacturing GHGs", "Virgin": 404.0},
        ]
    )

    summary = production_report_summary_table(output).set_index("metric")

    assert summary.loc["Cell manufacturing cost", "Virgin"] == 101.0
    assert summary.loc["Cell manufacturing GHGs", "unit"] == "g CO2e/kWh"
