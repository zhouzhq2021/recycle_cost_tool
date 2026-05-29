import io
import json
import zipfile

import pandas as pd

from recycle_cost.app_services import (
    parameter_tables_for_scenario,
    result_bundle_bytes,
    scenario_defaults_from_record,
    scenario_json_bytes,
    scenario_record,
    user_table,
)
from recycle_cost.model import default_scenario


def test_user_table_hides_audit_columns_and_renames_values():
    table = user_table(
        pd.DataFrame(
            [
                {
                    "metric": "Cost",
                    "python_value": 1.5,
                    "workbook_value": 1.0,
                    "delta": 0.5,
                    "status": "python_calculated",
                    "source_row": 123,
                }
            ]
        )
    )

    assert list(table.columns) == ["metric", "value"]
    assert table.loc[0, "value"] == 1.5


def test_scenario_json_and_defaults_round_trip_primary_inputs():
    scenario = default_scenario()
    record = json.loads(scenario_json_bytes(scenario).decode("utf-8"))
    defaults = scenario_defaults_from_record(record, {"feedstock_tonnes": 0})

    assert record == scenario_record(scenario)
    assert defaults["manufacturing_chemistry"] == scenario.manufacturing_chemistry
    assert defaults["feedstock_tonnes"] == scenario.feedstock_tonnes_per_year


def test_result_bundle_contains_scenario_and_csv_tables():
    scenario = default_scenario()
    bundle = result_bundle_bytes(scenario, {"Summary": pd.DataFrame([{"metric": "Cost", "python_value": 1.0}])})

    with zipfile.ZipFile(io.BytesIO(bundle)) as archive:
        assert {"scenario.json", "summary.csv"}.issubset(set(archive.namelist()))
        assert "value" in archive.read("summary.csv").decode("utf-8")


def test_parameter_tables_for_scenario_include_core_sections():
    tables = parameter_tables_for_scenario(default_scenario(), "Hydro")

    assert {
        "Scenario inputs",
        "Feedstock streams",
        "Transport distances",
        "CM recovery product yields",
        "Material conversion allocation factors",
        "Material conversion recycling economics",
        "Material conversion recycling environment",
        "Material conversion cathode-only environment",
        "Cathode required precursors",
    }.issubset(tables)
    assert "calculated_mass_direct" in tables["Material conversion allocation factors"].columns
    assert "calculated_Direct" in tables["Material conversion recycling economics"].columns
    assert "calculated_Direct" in tables["Material conversion recycling environment"].columns
