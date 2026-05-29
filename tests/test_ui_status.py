from recycle_cost.ui_status import calculation_status_rows, status_style


def test_calculation_status_rows_cover_dashboard_workflow():
    statuses = calculation_status_rows()

    assert {
        "Collection & transport",
        "Disassembly",
        "Preprocessing",
        "CM recovery",
        "Material conversion",
        "Cathode production",
        "Cell and pack manufacturing",
        "Output and report",
    }.issubset(set(statuses["workflow"]))
    assert set(statuses["status"]) == {"Python port"}
    assert statuses["workbook_area"].notna().all()


def test_status_style_falls_back_to_snapshot_style():
    assert status_style("Python port")["label"] == "PYTHON PORT"
    assert status_style("Mixed")["label"] == "MIXED"
    assert status_style("Unknown")["label"] == "WORKBOOK SNAPSHOT"
