import io
import json
import zipfile

import pandas as pd

from recycle_cost.app_services import (
    parameter_tables_for_scenario,
    recycling_process_key,
    result_bundle_bytes,
    scenario_defaults_from_record,
    scenario_defaults_from_json_bytes,
    scenario_from_inputs,
    scenario_from_record,
    scenario_json_bytes,
    scenario_record,
    scenario_validation_messages,
    user_table,
)
from recycle_cost.model import Scenario, default_scenario


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


def test_scenario_defaults_from_json_bytes_rejects_non_object():
    fallback = {"feedstock_tonnes": 0}

    defaults = scenario_defaults_from_json_bytes(b'{"feedstock_tonnes_per_year": 10}', fallback)
    assert defaults["feedstock_tonnes"] == 10

    try:
        scenario_defaults_from_json_bytes(b"[1, 2, 3]", fallback)
    except ValueError as exc:
        assert "object" in str(exc)
    else:
        raise AssertionError("non-object scenario JSON should be rejected")


def test_scenario_from_inputs_maps_feedstock_and_transport_fields():
    scenario = scenario_from_inputs(
        battery_manufactured="Pack",
        throughput_gwh_per_year=50.0,
        manufacturing_chemistry="NMC(622)",
        manufacturing_location="U.S.",
        battery_collected="Module",
        feedstock_chemistry="NMC(811)",
        feedstock_type="End-of-life battery: pack",
        feedstock_tonnes_per_year=123.0,
        recycling_process="Direct",
        cathode_chemistry="NMC(622)",
        recycled_content=0.25,
        cathode_throughput_gwh_per_year=10.0,
        collection_to_disassembly=1.0,
        disassembly_to_preprocessor=2.0,
        preprocessor_to_cm_recovery=3.0,
        manufacturer_to_preprocessor_or_cm_recovery=4.0,
        recycler_to_cathode_producer=5.0,
        cathode_producer_to_manufacturer=6.0,
    )

    assert scenario.feedstocks[0].chemistry == "NMC(811)"
    assert scenario.feedstocks[0].tonnes_per_year == 123.0
    assert scenario.transport_distances.collection_to_disassembly == 1.0
    assert scenario.transport_distances.cathode_producer_to_manufacturer == 6.0


def test_scenario_from_record_preserves_multiple_feedstocks():
    fallback = default_scenario()
    scenario = scenario_from_record(
        {
            "recycling_process": "Direct",
            "feedstocks": [
                {"chemistry": "NMC(111)", "feedstock_type": "End-of-life battery: pack", "tonnes_per_year": 100.0},
                {"chemistry": "NMC(811)", "feedstock_type": "Black mass", "tonnes_per_year": 50.0},
            ],
            "collection_to_disassembly": 42.0,
        },
        fallback,
    )

    assert scenario.recycling_process == "Direct"
    assert len(scenario.feedstocks) == 2
    assert scenario.feedstocks[1].chemistry == "NMC(811)"
    assert scenario.transport_distances.collection_to_disassembly == 42.0
    assert scenario.transport_distances.disassembly_to_preprocessor == fallback.transport_distances.disassembly_to_preprocessor


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


def test_recycling_process_key_normalizes_workbook_labels():
    assert recycling_process_key("Pyrometallurgical") == "Pyro"
    assert recycling_process_key("Hydrometallurgical") == "Hydro"
    assert recycling_process_key("Direct") == "Direct"
    assert recycling_process_key("Custom") == "Custom"
    assert recycling_process_key("Select Process") is None


def test_scenario_validation_messages_cover_guidance_cases():
    scenario = Scenario(
        **{
            **default_scenario().__dict__,
            "feedstock_type": "Black mass",
            "feedstock_tonnes_per_year": 0.0,
            "recycling_process": "Select Process",
            "cathode_throughput_gwh_per_year": 0.0,
        }
    )
    text = {
        "zero_feedstock": "zero",
        "black_mass_no_disassembly": "black mass",
        "select_process_warning": "process",
        "cathode_zero": "cathode",
    }

    assert scenario_validation_messages(scenario, text) == [
        ("warning", "zero"),
        ("info", "black mass"),
        ("warning", "process"),
        ("info", "cathode"),
    ]
