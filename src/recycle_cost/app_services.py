from __future__ import annotations

import io
import json
import zipfile

import pandas as pd

from .cathode import (
    cathode_chemical_prices,
    cathode_chemistry_for_scenario,
    cathode_material_conversion_costs,
    cathode_required_precursors,
    cathode_utility_prices,
)
from .cm_recovery import cm_recovery_product_outputs, cm_recovery_product_prices
from .mat_conv import (
    mat_conv_allocation_factors_calculated,
    mat_conv_recycling_economics_calculated,
    mat_conv_recycling_environment_summary_calculated,
)
from .model import FeedstockInput, Scenario, TransportDistances
from .preprocessing import (
    preprocessing_black_mass_composition,
    preprocessing_feedstock_composition,
    preprocessing_product_outputs,
)
from .reporting import (
    python_ported_manufacturing_output_summary,
    python_ported_output_cost_breakdown,
    python_ported_output_recycling_revenue_table,
    python_ported_output_summary_table,
    python_ported_process_stage_output_summary,
    python_ported_report_comparison,
    python_ported_stage_summary,
)


def recycling_process_key(label: str) -> str | None:
    normalized = label.strip().casefold()
    if "pyro" in normalized:
        return "Pyro"
    if "hydro" in normalized:
        return "Hydro"
    if normalized == "direct":
        return "Direct"
    if normalized == "custom":
        return "Custom"
    return None


def scenario_validation_messages(scenario: Scenario, text: dict[str, str]) -> list[tuple[str, str]]:
    messages: list[tuple[str, str]] = []
    process = recycling_process_key(scenario.recycling_process)
    if safe_float(scenario.feedstock_tonnes_per_year) <= 0:
        messages.append(("warning", text["zero_feedstock"]))
    if scenario.feedstock_type == "Black mass":
        messages.append(("info", text["black_mass_no_disassembly"]))
    if process not in {"Pyro", "Hydro", "Direct", "Custom"}:
        messages.append(("warning", text["select_process_warning"]))
    if safe_float(scenario.cathode_throughput_gwh_per_year) <= 0:
        messages.append(("info", text["cathode_zero"]))
    return messages


def user_table(data: pd.DataFrame) -> pd.DataFrame:
    hidden_tokens = ("workbook", "delta", "status", "source_row")
    table = data.drop(
        columns=[
            column
            for column in data.columns
            if any(token in str(column).casefold() for token in hidden_tokens)
        ],
        errors="ignore",
    )
    table = table.rename(
        columns={
            "python_value": "value",
            "calculated_value": "value",
            "calculated_total": "total",
            "calculated_cost": "cost",
            "calculated_per_kg": "value_per_kg",
            "calculated_annual": "annual_value",
        }
    )
    table.columns = [str(column) for column in table.columns]
    for column in table.columns:
        if not (pd.api.types.is_object_dtype(table[column]) or pd.api.types.is_string_dtype(table[column])):
            continue
        table[column] = table[column].map(_display_value)
    return table


def _display_value(value) -> str:
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    return str(value)


def csv_bytes(data: pd.DataFrame) -> bytes:
    return user_table(data).to_csv(index=False).encode("utf-8")


def scenario_record(scenario: Scenario) -> dict[str, object]:
    distances = scenario.transport_distances
    return {
        "battery_manufactured": scenario.battery_manufactured,
        "throughput_gwh_per_year": scenario.throughput_gwh_per_year,
        "manufacturing_chemistry": scenario.manufacturing_chemistry,
        "manufacturing_location": scenario.manufacturing_location,
        "battery_collected": scenario.battery_collected,
        "feedstock_chemistry": scenario.feedstock_chemistry,
        "feedstock_type": scenario.feedstock_type,
        "feedstock_tonnes_per_year": scenario.feedstock_tonnes_per_year,
        "recycling_process": scenario.recycling_process,
        "recycling_flow_variant": scenario.recycling_flow_variant,
        "cathode_chemistry": scenario.cathode_chemistry,
        "recycled_content": scenario.recycled_content,
        "cathode_throughput_gwh_per_year": scenario.cathode_throughput_gwh_per_year,
        "collection_to_disassembly": distances.collection_to_disassembly,
        "disassembly_to_preprocessor": distances.disassembly_to_preprocessor,
        "preprocessor_to_cm_recovery": distances.preprocessor_to_cm_recovery,
        "manufacturer_to_preprocessor_or_cm_recovery": distances.manufacturer_to_preprocessor_or_cm_recovery,
        "recycler_to_cathode_producer": distances.recycler_to_cathode_producer,
        "cathode_producer_to_manufacturer": distances.cathode_producer_to_manufacturer,
        "feedstocks": [
            {
                "chemistry": feedstock.chemistry,
                "feedstock_type": feedstock.feedstock_type,
                "tonnes_per_year": feedstock.tonnes_per_year,
            }
            for feedstock in scenario.feedstocks
        ],
    }


def scenario_from_inputs(
    *,
    battery_manufactured: str,
    throughput_gwh_per_year: float,
    manufacturing_chemistry: str,
    manufacturing_location: str,
    battery_collected: str,
    feedstock_chemistry: str,
    feedstock_type: str,
    feedstock_tonnes_per_year: float,
    recycling_process: str,
    cathode_chemistry: str,
    recycled_content: float,
    cathode_throughput_gwh_per_year: float,
    collection_to_disassembly: float,
    disassembly_to_preprocessor: float,
    preprocessor_to_cm_recovery: float,
    manufacturer_to_preprocessor_or_cm_recovery: float,
    recycler_to_cathode_producer: float,
    cathode_producer_to_manufacturer: float,
    recycling_flow_variant: str = "old",
) -> Scenario:
    return Scenario(
        battery_manufactured=battery_manufactured,
        throughput_gwh_per_year=throughput_gwh_per_year,
        manufacturing_chemistry=manufacturing_chemistry,
        manufacturing_location=manufacturing_location,
        battery_collected=battery_collected,
        feedstock_chemistry=feedstock_chemistry,
        feedstock_type=feedstock_type,
        feedstock_tonnes_per_year=feedstock_tonnes_per_year,
        recycling_process=recycling_process,
        cathode_chemistry=cathode_chemistry,
        recycled_content=recycled_content,
        cathode_throughput_gwh_per_year=cathode_throughput_gwh_per_year,
        transport_distances=TransportDistances(
            collection_to_disassembly=collection_to_disassembly,
            disassembly_to_preprocessor=disassembly_to_preprocessor,
            preprocessor_to_cm_recovery=preprocessor_to_cm_recovery,
            manufacturer_to_preprocessor_or_cm_recovery=manufacturer_to_preprocessor_or_cm_recovery,
            recycler_to_cathode_producer=recycler_to_cathode_producer,
            cathode_producer_to_manufacturer=cathode_producer_to_manufacturer,
        ),
        feedstocks=(FeedstockInput(feedstock_chemistry, feedstock_type, feedstock_tonnes_per_year),),
        recycling_flow_variant=recycling_flow_variant,
    )


def scenario_from_record(record: dict[str, object], fallback: Scenario) -> Scenario:
    feedstock_records = record.get("feedstocks")
    feedstocks: tuple[FeedstockInput, ...]
    if isinstance(feedstock_records, list) and feedstock_records:
        parsed_feedstocks = []
        for item in feedstock_records:
            if not isinstance(item, dict):
                continue
            parsed_feedstocks.append(
                FeedstockInput(
                    str(item.get("chemistry", fallback.feedstock_chemistry)),
                    str(item.get("feedstock_type", fallback.feedstock_type)),
                    safe_float(item.get("tonnes_per_year"), safe_float(fallback.feedstock_tonnes_per_year)),
                )
            )
        feedstocks = tuple(parsed_feedstocks)
    else:
        feedstocks = (
            FeedstockInput(
                str(record.get("feedstock_chemistry", fallback.feedstock_chemistry)),
                str(record.get("feedstock_type", fallback.feedstock_type)),
                safe_float(record.get("feedstock_tonnes_per_year"), safe_float(fallback.feedstock_tonnes_per_year)),
            ),
        )

    primary = feedstocks[0] if feedstocks else fallback.feedstocks[0]
    distances = fallback.transport_distances
    return Scenario(
        battery_manufactured=str(record.get("battery_manufactured", fallback.battery_manufactured)),
        throughput_gwh_per_year=safe_float(record.get("throughput_gwh_per_year"), safe_float(fallback.throughput_gwh_per_year)),
        manufacturing_chemistry=str(record.get("manufacturing_chemistry", fallback.manufacturing_chemistry)),
        manufacturing_location=str(record.get("manufacturing_location", fallback.manufacturing_location)),
        battery_collected=str(record.get("battery_collected", fallback.battery_collected)),
        feedstock_chemistry=str(record.get("feedstock_chemistry", primary.chemistry)),
        feedstock_type=str(record.get("feedstock_type", primary.feedstock_type)),
        feedstock_tonnes_per_year=safe_float(record.get("feedstock_tonnes_per_year"), primary.tonnes_per_year),
        recycling_process=str(record.get("recycling_process", fallback.recycling_process)),
        recycling_flow_variant=str(record.get("recycling_flow_variant", fallback.recycling_flow_variant)),
        cathode_chemistry=str(record.get("cathode_chemistry", fallback.cathode_chemistry)),
        recycled_content=safe_float(record.get("recycled_content"), safe_float(fallback.recycled_content)),
        cathode_throughput_gwh_per_year=safe_float(
            record.get("cathode_throughput_gwh_per_year"),
            safe_float(fallback.cathode_throughput_gwh_per_year),
        ),
        transport_distances=TransportDistances(
            collection_to_disassembly=safe_float(
                record.get("collection_to_disassembly"),
                distances.collection_to_disassembly,
            ),
            disassembly_to_preprocessor=safe_float(
                record.get("disassembly_to_preprocessor"),
                distances.disassembly_to_preprocessor,
            ),
            preprocessor_to_cm_recovery=safe_float(
                record.get("preprocessor_to_cm_recovery"),
                distances.preprocessor_to_cm_recovery,
            ),
            manufacturer_to_preprocessor_or_cm_recovery=safe_float(
                record.get("manufacturer_to_preprocessor_or_cm_recovery"),
                distances.manufacturer_to_preprocessor_or_cm_recovery,
            ),
            recycler_to_cathode_producer=safe_float(
                record.get("recycler_to_cathode_producer"),
                distances.recycler_to_cathode_producer,
            ),
            cathode_producer_to_manufacturer=safe_float(
                record.get("cathode_producer_to_manufacturer"),
                distances.cathode_producer_to_manufacturer,
            ),
        ),
        feedstocks=feedstocks,
    )


def parameter_tables_for_scenario(scenario: Scenario, process: str) -> dict[str, pd.DataFrame]:
    chemistry = cathode_chemistry_for_scenario(scenario)
    scenario_rows = [
        {"group": "production", "parameter": key, "value": value}
        for key, value in scenario_record(scenario).items()
        if key != "feedstocks"
    ]
    feedstock_rows = [
        {
            "chemistry": feedstock.chemistry,
            "feedstock_type": feedstock.feedstock_type,
            "tonnes_per_year": feedstock.tonnes_per_year,
        }
        for feedstock in scenario.feedstocks
    ]
    transport_rows = [
        {"route": route, "distance_miles": distance}
        for route, distance in (
            ("collection_to_disassembly", scenario.transport_distances.collection_to_disassembly),
            ("disassembly_to_preprocessor", scenario.transport_distances.disassembly_to_preprocessor),
            ("preprocessor_to_cm_recovery", scenario.transport_distances.preprocessor_to_cm_recovery),
            (
                "manufacturer_to_preprocessor_or_cm_recovery",
                scenario.transport_distances.manufacturer_to_preprocessor_or_cm_recovery,
            ),
            ("recycler_to_cathode_producer", scenario.transport_distances.recycler_to_cathode_producer),
            ("cathode_producer_to_manufacturer", scenario.transport_distances.cathode_producer_to_manufacturer),
        )
    ]
    seen_prices = set()
    cm_price_rows = []
    for product, price in cm_recovery_product_prices().items():
        key = str(product).casefold()
        if key in seen_prices:
            continue
        seen_prices.add(key)
        cm_price_rows.append({"product": product, "price_per_kg": price})
    cm_prices = pd.DataFrame(cm_price_rows)
    return {
        "Scenario inputs": pd.DataFrame(scenario_rows),
        "Feedstock streams": pd.DataFrame(feedstock_rows),
        "Transport distances": pd.DataFrame(transport_rows),
        "Preprocessing feedstock composition": preprocessing_feedstock_composition(scenario),
        "Preprocessing product yields": preprocessing_product_outputs(scenario),
        "Black mass composition": preprocessing_black_mass_composition(scenario),
        "CM recovery product yields": cm_recovery_product_outputs(scenario, process),
        "CM recovery product prices": cm_prices,
        "Material conversion allocation factors": mat_conv_allocation_factors_calculated(scenario),
        "Material conversion recycling economics": mat_conv_recycling_economics_calculated(scenario),
        "Material conversion recycling environment": mat_conv_recycling_environment_summary_calculated(scenario),
        "Material conversion cathode-only environment": mat_conv_recycling_environment_summary_calculated(
            scenario,
            cathode_materials_only=True,
        ),
        "Cathode required precursors": cathode_required_precursors(chemistry),
        "Cathode chemical prices": cathode_chemical_prices(),
        "Cathode utility prices": cathode_utility_prices(),
        "Cathode conversion costs": cathode_material_conversion_costs(),
    }


def calculated_result_tables(scenario: Scenario, process: str) -> dict[str, pd.DataFrame]:
    return {
        "stage_summary": python_ported_stage_summary(scenario, process),
        "manufacturing_summary": python_ported_manufacturing_output_summary(include_workbook=False),
        "process_stage": python_ported_process_stage_output_summary(scenario, include_workbook=False),
        "cost_breakdown": python_ported_output_cost_breakdown(include_workbook=False),
        "recycling_revenue": python_ported_output_recycling_revenue_table(scenario, include_workbook=False),
        "report_results": python_ported_report_comparison(scenario, include_workbook=False),
        "output_summary": python_ported_output_summary_table(scenario),
    }


def export_tables_for_scenario(
    scenario: Scenario,
    result_tables: dict[str, pd.DataFrame],
    text: dict[str, str],
) -> dict[str, pd.DataFrame]:
    return {
        text["current_scenario"]: pd.DataFrame([scenario_record(scenario)]),
        text["stage_summary"]: result_tables["stage_summary"],
        text["process_stage"]: result_tables["process_stage"],
        text["cost_breakdown"]: result_tables["cost_breakdown"],
        text["recycling_revenue"]: result_tables["recycling_revenue"],
        text["manufacturing_summary"]: result_tables["manufacturing_summary"],
        text["output_summary"]: result_tables["output_summary"],
        text["report_results"]: result_tables["report_results"],
    }


def scenario_json_bytes(scenario: Scenario) -> bytes:
    return json.dumps(scenario_record(scenario), indent=2, ensure_ascii=False).encode("utf-8")


def scenario_defaults_from_record(record: dict[str, object], fallback: dict[str, object]) -> dict[str, object]:
    defaults = dict(fallback)
    field_map = {
        "battery_manufactured": "battery_manufactured",
        "throughput": "throughput_gwh_per_year",
        "manufacturing_chemistry": "manufacturing_chemistry",
        "manufacturing_location": "manufacturing_location",
        "battery_collected": "battery_collected",
        "feedstock_chemistry": "feedstock_chemistry",
        "feedstock_type": "feedstock_type",
        "feedstock_tonnes": "feedstock_tonnes_per_year",
        "recycling_process": "recycling_process",
        "recycling_flow_variant": "recycling_flow_variant",
        "cathode_chemistry": "cathode_chemistry",
        "cathode_throughput": "cathode_throughput_gwh_per_year",
        "recycled_content": "recycled_content",
        "collection_to_disassembly": "collection_to_disassembly",
        "disassembly_to_preprocessor": "disassembly_to_preprocessor",
        "preprocessor_to_cm_recovery": "preprocessor_to_cm_recovery",
        "manufacturer_to_preprocessor_or_cm_recovery": "manufacturer_to_preprocessor_or_cm_recovery",
        "recycler_to_cathode_producer": "recycler_to_cathode_producer",
        "cathode_producer_to_manufacturer": "cathode_producer_to_manufacturer",
    }
    for default_key, record_key in field_map.items():
        if record_key in record and record[record_key] is not None:
            defaults[default_key] = record[record_key]
    feedstocks = record.get("feedstocks")
    if isinstance(feedstocks, list) and feedstocks:
        first = feedstocks[0]
        if isinstance(first, dict):
            defaults["feedstock_chemistry"] = first.get("chemistry", defaults["feedstock_chemistry"])
            defaults["feedstock_type"] = first.get("feedstock_type", defaults["feedstock_type"])
            defaults["feedstock_tonnes"] = first.get("tonnes_per_year", defaults["feedstock_tonnes"])
    return defaults


def scenario_defaults_from_json_bytes(data: bytes, fallback: dict[str, object]) -> dict[str, object]:
    record = json.loads(data.decode("utf-8"))
    if not isinstance(record, dict):
        raise ValueError("Scenario JSON must be an object")
    return scenario_defaults_from_record(record, fallback)


def safe_float(value: object, fallback: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


def nonnegative_float(value: object, fallback: float = 0.0) -> float:
    return max(0.0, safe_float(value, fallback))


def fraction_float(value: object, fallback: float = 0.0) -> float:
    return min(1.0, nonnegative_float(value, fallback))


def result_bundle_bytes(scenario: Scenario, tables: dict[str, pd.DataFrame]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("scenario.json", scenario_json_bytes(scenario))
        for name, table in tables.items():
            filename = f"{name.lower().replace(' ', '_').replace('/', '_')}.csv"
            archive.writestr(filename, csv_bytes(table))
    return buffer.getvalue()


def scenario_display_table(scenario: Scenario, text: dict[str, str]) -> pd.DataFrame:
    rows = [
        (text["battery_manufactured"], scenario.battery_manufactured),
        (text["throughput"], scenario.throughput_gwh_per_year),
        (text["manufacturing_chemistry"], scenario.manufacturing_chemistry),
        (text["manufacturing_location"], scenario.manufacturing_location),
        (text["battery_collected"], scenario.battery_collected),
        (text["feedstock_chemistry"], scenario.feedstock_chemistry),
        (text["feedstock_type"], scenario.feedstock_type),
        (text["feedstock_tonnes"], scenario.feedstock_tonnes_per_year),
        (text["recycling_process"], scenario.recycling_process),
        (text["cathode_chemistry"], scenario.cathode_chemistry),
        (text["cathode_throughput"], scenario.cathode_throughput_gwh_per_year),
        (text["recycled_content"], scenario.recycled_content),
        (text["collection_to_disassembly"], scenario.transport_distances.collection_to_disassembly),
        (text["disassembly_to_preprocessor"], scenario.transport_distances.disassembly_to_preprocessor),
        (text["preprocessor_to_cm"], scenario.transport_distances.preprocessor_to_cm_recovery),
        (
            text["manufacturer_to_preprocessor"],
            scenario.transport_distances.manufacturer_to_preprocessor_or_cm_recovery,
        ),
        (text["recycler_to_cathode"], scenario.transport_distances.recycler_to_cathode_producer),
        (text["cathode_to_manufacturer"], scenario.transport_distances.cathode_producer_to_manufacturer),
    ]
    return pd.DataFrame(rows, columns=[text["field"], text["value"]])


def option_index(options: tuple[str, ...], value: str) -> int:
    if value in options:
        return options.index(value)
    normalized = value.strip()
    for index, option in enumerate(options):
        if option.strip() == normalized:
            return index
    return 0
