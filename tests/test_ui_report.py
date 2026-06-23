from recycle_cost.ui_sections import format_report_number, format_report_table


def test_format_report_number_uses_stable_precision():
    assert format_report_number(0) == "0.0000"
    assert format_report_number(0.01234567) == "0.012346"
    assert format_report_number(5.0819271) == "5.0819"
    assert format_report_number(32462.70219) == "32,462.70"
    assert format_report_number(None) == ""


def test_format_report_table_formats_numeric_columns():
    import pandas as pd

    table = format_report_table(pd.DataFrame([{"metric": "Cost", "value": 5.0819271}]))

    assert table.loc[0, "metric"] == "Cost"
    assert table.loc[0, "value"] == "5.0819"
