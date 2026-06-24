import pandas as pd

from recycle_cost.ui_sections import (
    _battery_production_cost_column,
    format_report_number,
    format_report_table,
    model_benchmark_policy_table,
    model_benchmark_diagnostics_table,
    production_report_summary_table,
    production_output_display_table,
    production_report_display_table,
    recycling_report_summary_table,
    recycling_route_comparison_table,
    selected_recycling_route_report_table,
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


def test_selected_recycling_route_report_table_includes_route_metrics_and_products():
    output = pd.DataFrame(
        [
            {"metric": "Recycling cost", "Hydro": 10.0},
            {"metric": "Recycling revenue", "Hydro": 2.5},
            {"metric": "Recycling GHGs", "Hydro": 100.0},
            {"metric": "Recycling total energy", "Hydro": 4.0},
            {"metric": "Recycling water", "Hydro": 0.2},
        ]
    )
    revenue = pd.DataFrame(
        [
            {"process": "Hydro", "material": "Ni2+ in product", "python_value": 1.5},
            {"process": "Hydro", "material": "Co2+ in product", "python_value": 1.0},
            {"process": "Direct", "material": "Rejuvenated NMC(622)", "python_value": 9.0},
        ]
    )

    report = selected_recycling_route_report_table(output, "Hydro", revenue).set_index(["section", "item"])

    assert report.loc[("Economics", "Net cost"), "value"] == 7.5
    assert report.loc[("Environment", "GHGs"), "value"] == 100.0
    assert report.loc[("Recovered products", "Ni2+ in product"), "value"] == 1.5
    assert ("Recovered products", "Rejuvenated NMC(622)") not in report.index


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


def test_battery_production_cost_column_uses_direct_reclaimed_label():
    assert _battery_production_cost_column("Hydro") == "recycled materials from hydro"
    assert _battery_production_cost_column("Direct") == "reclaimed materials from direct"


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


def test_production_display_tables_hide_recycling_route_columns():
    output = pd.DataFrame(
        [
            {"metric": "Cell manufacturing cost", "category": "Cost", "unit": "$/kWh", "Virgin": 101.0, "Pyro": 1.0},
            {"metric": "Recycling cost", "category": "Cost", "unit": "$/kg", "Virgin": 0.0, "Pyro": 2.0},
        ]
    )
    report = pd.DataFrame(
        [
            {"section": "Manufacturing", "metric": "Cost", "Virgin Manufacture": 101.0, "Pyro": 90.0},
            {"section": "Closed loop", "metric": "Cost", "Virgin Manufacture": 0.0, "Pyro": 80.0},
        ]
    )

    output_display = production_output_display_table(output)
    report_display = production_report_display_table(report)

    assert list(output_display.columns) == ["metric", "category", "unit", "Virgin"]
    assert output_display["metric"].tolist() == ["Cell manufacturing cost"]
    assert list(report_display.columns) == ["metric", "Virgin Manufacture"]
    assert report_display["metric"].tolist() == ["Cost"]


def test_new_flow_benchmark_policy_does_not_require_legacy_excel_match():
    policy = model_benchmark_policy_table(is_new_flow=True).set_index("item")

    assert "not expected to match legacy Excel exactly" in policy.loc["Benchmark target", "policy"]
    assert "Mass balance" in policy.loc["Validation basis", "policy"]


def test_new_flow_benchmark_diagnostics_focus_on_interpretability_not_legacy_equality():
    output = pd.DataFrame(
        [
            {"metric": "Recycling cost", "Hydro": 10.0},
            {"metric": "Recycling revenue", "Hydro": 2.0},
            {"metric": "Recycling GHGs", "Hydro": 30.0},
            {"metric": "Recycling total energy", "Hydro": 4.0},
            {"metric": "Recycling water", "Hydro": 0.5},
        ]
    )

    diagnostics = model_benchmark_diagnostics_table(output, "Hydro", is_new_flow=True)

    assert set(diagnostics["status"]) == {"Pass"}
    assert diagnostics["check"].str.contains("does not require legacy-value equality").any()
