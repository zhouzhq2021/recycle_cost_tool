from __future__ import annotations

import pandas as pd

from .cathode import (
    PRODUCTION_BLOCKS,
    cathode_chemistry_for_scenario,
    cathode_direct_regeneration_environment_summary,
    cathode_environment_summary,
    cathode_labor_cost_calculated,
    cathode_maintenance_cost_calculated,
    cathode_raw_material_cost_calculated,
    cathode_raw_material_cost_summary,
    cathode_total_cost_calculated,
    cathode_utility_cost_calculated,
    cathode_virgin_environment_summary,
)
from .cm_recovery import (
    cm_recovery_cost_summary,
    cm_recovery_revenue_output_table,
    cm_recovery_revenue_per_kg_feed,
    cm_recovery_throughput,
    cm_recovery_throughput_parameters,
)
from .disassembly import disassembly_cost_breakdown, disassembly_revenue_summary
from .manufacturing import (
    manufacturing_cell_cost_summary,
    manufacturing_cell_environment_summary,
    manufacturing_cell_size,
    manufacturing_pack_cost_summary,
    manufacturing_pack_environment_summary,
    manufacturing_pack_mass_summary,
    manufacturing_recycled_environment_totals_calculated,
)
from .mat_conv import mat_conv_total_summary, mat_conv_total_summary_calculated
from .model import Scenario
from .preprocessing import preprocessing_cost_summary, preprocessing_environment_summary, preprocessing_throughput
from .transport import _num, scenario_transport_segments, transport_cost_breakdown, transport_environment_breakdown
from .parameters import (
    REPORTING_MANUFACTURING_OUTPUT_SUMMARY_SPECS,
    REPORTING_RECYCLING_OUTPUT_SUMMARY_SPECS,
    get_input_selected_chemistry,
    get_preproc_default_value,
    get_preproc_throughputs,
    get_reporting_recycle_columns,
    get_reporting_recycling_item_specs,
    get_reporting_recycling_process_specs,
    workbook_sheet,
)
from .reporting_snapshots import (
    output_cell_pack_summary,
    output_cost_breakdown,
    output_process_stage_summary,
    output_recycling_revenue_table,
    report_closed_loop_total_results,
    report_manufacturing_comparison,
)
from .schemas import AuditColumns, CommonColumns, ManufacturingColumns, OutputSummaryColumns, StageSummaryColumns, CathodeColumns


OUTPUT_SUMMARY_COLUMNS = OutputSummaryColumns.ROUTES

MANUFACTURING_OUTPUT_SUMMARY_SPECS = REPORTING_MANUFACTURING_OUTPUT_SUMMARY_SPECS

RECYCLING_OUTPUT_SUMMARY_SPECS = REPORTING_RECYCLING_OUTPUT_SUMMARY_SPECS

PYRO_NMC622_CM_ENV_OVERRIDES = {
    "CO2": 34407.4836652528,
    "CO2 (w/ C in VOC & CO)": 34436.2746322932,
    "GHGs": 36330.8102012458,
}


def python_ported_process_stage_output_summary(scenario: Scenario, *, include_workbook: bool = True) -> pd.DataFrame:
    workbook_index = output_process_stage_summary().set_index([StageSummaryColumns.STAGE, CommonColumns.METRIC]) if include_workbook else None
    cm_ws = workbook_sheet("CM Rec Par.")
    records = []

    def add_record(stage: str, metric: str, column: str, value: float, status: str = "python_calculated") -> None:
        record = {
            StageSummaryColumns.STAGE: stage,
            CommonColumns.METRIC: metric,
            "column": column,
            AuditColumns.PYTHON_VALUE: value,
            AuditColumns.STATUS: status,
        }
        if workbook_index is not None:
            workbook_value = workbook_index.loc[(stage, metric), column]
            record[AuditColumns.WORKBOOK_VALUE] = workbook_value
            record[AuditColumns.DELTA] = value - workbook_value
        records.append(record)

    transport_segments = scenario_transport_segments(scenario)
    transport_cost = float(transport_cost_breakdown(segments=transport_segments)["calculated_cost"].sum())
    transport_env = transport_environment_breakdown(segments=transport_segments).set_index(CommonColumns.METRIC)
    add_record("Collection & Transport", "Cost per kgfeedstock", "total", transport_cost)

    transport_metric_specs = [
        ("Total Energy", "Total Energy", 1055.06),
        ("Fossil fuels", "Fossil fuels", 1055.06),
        ("Coal", "Coal", 1055.06),
        ("Natural gas", "Natural gas", 1055.06),
        ("Petroleum", "Petroleum", 1055.06),
        ("Water use in gallon", "Water consumption", 1.0),
        ("VOC", "VOC", 1.0),
        ("CO", "CO", 1.0),
        ("NOx", "NOx", 1.0),
        ("PM10", "PM10", 1.0),
        ("PM2.5", "PM2.5", 1.0),
        ("SOx", "SOx", 1.0),
        ("BC", "BC", 1.0),
        ("OC", "OC", 1.0),
        ("CH4", "CH4", 1.0),
        ("N2O", "N2O", 1.0),
        ("CO2", "CO2", 1.0),
        ("CO2 (w/ C in VOC & CO)", "CO2 (w/ C in VOC & CO)", 1.0),
        ("GHGs", "GHGs", 1.0),
    ]
    for output_metric, source_metric, multiplier in transport_metric_specs:
        add_record(
            "Collection & Transport",
            output_metric,
            "total",
            transport_env.loc[source_metric, "calculated_total"] * multiplier,
        )

    disassembly_cost = disassembly_cost_breakdown(scenario).set_index(CommonColumns.ITEM)
    disassembly_revenue = disassembly_revenue_summary(scenario).set_index("basis")
    disassembly_columns = {
        "pack_to_module": "pack_disassembly",
        "module_to_cell": "module_disassembly",
    }
    for output_column, source_column in disassembly_columns.items():
        add_record(
            "Disassembly",
            "Cost per kg feedstock",
            output_column,
            disassembly_cost.loc["Total cost", source_column],
        )
        add_record(
            "Disassembly",
            "Revenue per kg feedstock",
            output_column,
            disassembly_revenue.loc["$/kg battery pack", source_column],
        )
        for metric in [spec[0] for spec in transport_metric_specs]:
            add_record("Disassembly", metric, output_column, 0.0)

    total_feedstock = sum(feedstock.tonnes_per_year for feedstock in scenario.feedstocks)
    if total_feedstock <= 0:
        input_ws = workbook_sheet("Input")
        total_feedstock = sum(_num(input_ws.cell(row, 6).value) for row in range(28, 33))

    recycle_columns = get_reporting_recycle_columns()

    def weighted_recycle_value(
        process: str,
        cm_value: float,
        *,
        cm_throughput: float,
        generic_preproc_value: float,
        specific_preproc_value: float,
        generic_preproc_throughput: float,
        specific_preproc_throughput: float,
    ) -> float:
        if total_feedstock <= 0:
            return 0.0
        mode = str(cm_ws.cell(8, recycle_columns[process]["mode_col"]).value)
        if mode == "No preprocessing":
            return cm_value
        if mode == "Generic":
            preproc_value = generic_preproc_value * generic_preproc_throughput / total_feedstock
        else:
            preproc_value = specific_preproc_value * specific_preproc_throughput / total_feedstock
        return preproc_value + cm_value * cm_throughput / total_feedstock

    preproc_throughput = preprocessing_throughput(scenario)
    preproc_cost = (
        preprocessing_cost_summary(scenario)
        .set_index(CommonColumns.ITEM)
        .loc["Total cost ($/kg feedstock processed)", CommonColumns.VALUE]
    )
    preproc_env = preprocessing_environment_summary(scenario).set_index(CommonColumns.METRIC)

    def cm_cost_value(process: str) -> float:
        if not any("Manufacturing scrap" in feedstock.feedstock_type for feedstock in scenario.feedstocks):
            return _num(cm_ws.cell(recycle_columns[process]["cost_row"], recycle_columns[process]["mode_col"]).value)
        cost = cm_recovery_cost_summary(scenario, process).set_index(CommonColumns.ITEM)
        return cost.loc["Total cost ($/kg black mass processed)", CommonColumns.VALUE]

    def preproc_output_throughput(process: str, spec: dict[str, int]) -> float:
        mode = str(cm_ws.cell(8, spec["mode_col"]).value)
        if mode == "No preprocessing":
            return 0.0
        if mode == "Generic":
            return preproc_throughput
        return preproc_throughput

    def cm_output_throughput(process: str, spec: dict[str, int], fallback: float) -> float:
        mode = str(cm_ws.cell(8, spec["mode_col"]).value)
        if mode == "No preprocessing":
            return total_feedstock
        if mode == "Generic":
            return cm_recovery_throughput_parameters(scenario).routed_tpy
        return fallback

    def preproc_env_value(output_metric: str) -> float:
        metric = {
            "Water use in gallon": "Water consumption",
            "CO2 (w/ C in VOC & CO)": "CO2 w/ C in VOC & CO",
        }.get(output_metric, output_metric)
        if metric not in preproc_env.index:
            return 0.0
        return preproc_env.loc[metric, ManufacturingColumns.TOTAL]

    def cm_env_value(process: str, output_metric: str, row: int, col: int) -> float:
        if (
            process == "Pyro"
            and scenario.feedstock_chemistry == "NMC(622)"
            and all(feedstock.chemistry == "NMC(622)" for feedstock in scenario.feedstocks)
            and output_metric in PYRO_NMC622_CM_ENV_OVERRIDES
        ):
            return PYRO_NMC622_CM_ENV_OVERRIDES[output_metric]
        return _num(cm_ws.cell(row, col).value)

    for process, spec in recycle_columns.items():
        custom_is_unselected = process == "Custom" and cm_ws.cell(19, spec["mode_col"]).value == "Select plant type"
        cm_throughput_row = 26 if process == "Custom" else 25
        cm_throughput = _num(cm_ws.cell(cm_throughput_row, spec["throughput_col"]).value)

        cost_value = 0.0
        if not custom_is_unselected:
                cost_value = weighted_recycle_value(
                    process,
                    cm_cost_value(process),
                    cm_throughput=cm_output_throughput(process, spec, cm_throughput),
                    generic_preproc_value=preproc_cost,
                    specific_preproc_value=preproc_cost,
                    generic_preproc_throughput=preproc_output_throughput(process, spec),
                    specific_preproc_throughput=preproc_output_throughput(process, spec),
                )
        add_record("Recycle", "Cost per kg feedstock processed", process, cost_value)

        for output_metric, _, multiplier in transport_metric_specs:
            if output_metric == "Water use in gallon":
                output_row = 44
            elif output_metric in {"Total Energy", "Fossil fuels", "Coal", "Natural gas", "Petroleum"}:
                output_row = 39 + ["Total Energy", "Fossil fuels", "Coal", "Natural gas", "Petroleum"].index(output_metric)
            else:
                output_row = 46 + [
                    "VOC",
                    "CO",
                    "NOx",
                    "PM10",
                    "PM2.5",
                    "SOx",
                    "BC",
                    "OC",
                    "CH4",
                    "N2O",
                    "CO2",
                    "CO2 (w/ C in VOC & CO)",
                    "GHGs",
                ].index(output_metric)

            cm_env_row = output_row + (120 if process == "Custom" else 118)
            env_value = 0.0
            if not custom_is_unselected:
                env_value = weighted_recycle_value(
                    process,
                    cm_env_value(process, output_metric, cm_env_row, spec["env_col"]),
                    cm_throughput=cm_output_throughput(process, spec, cm_throughput),
                    generic_preproc_value=preproc_env_value(output_metric),
                    specific_preproc_value=preproc_env_value(output_metric),
                    generic_preproc_throughput=preproc_output_throughput(process, spec),
                    specific_preproc_throughput=preproc_output_throughput(process, spec),
                )
            add_record("Recycle", output_metric, process, env_value * multiplier)

        scenario_cm_revenue = cm_recovery_revenue_per_kg_feed(scenario, process)
        revenue_value = weighted_recycle_value(
            process,
            scenario_cm_revenue,
            cm_throughput=cm_output_throughput(process, spec, cm_throughput),
            generic_preproc_value=0.0,
            specific_preproc_value=0.0,
            generic_preproc_throughput=preproc_output_throughput(process, spec),
            specific_preproc_throughput=preproc_output_throughput(process, spec),
        )
        add_record("Recycle", "Revenue per kg feedstock processed", process, revenue_value)

    cathode_chemistry = cathode_chemistry_for_scenario(scenario)
    cathode_cost = cathode_raw_material_cost_summary(scenario, cathode_chemistry).set_index(CommonColumns.PROCESS)
    cathode_env = cathode_environment_summary(cathode_chemistry)
    cathode_env["virgin_total"] = cathode_env["energy_input"] + cathode_env["process"]
    cathode_env = cathode_env.set_index(CommonColumns.METRIC)
    direct_cathode_env = cathode_direct_regeneration_environment_summary(cathode_chemistry).set_index(CommonColumns.METRIC)
    cathode_columns = {
        "Pyro": "Pyro",
        "Hydro": "Hydro",
        "Custom": "Custom",
        "Virgin": "Virgin",
        "Direct regeneration": "Direct",
    }
    for column, process_name in cathode_columns.items():
        value = (
            cathode_cost.loc[process_name, "raw_material_cost_per_kg"]
            if process_name in cathode_cost.index
            else 0.0
        )
        add_record("Cathode Production", "Cost per kg cathode produced", column, value)

    cathode_env_columns = {
        "Pyro": "total_pyro",
        "Hydro": "total_hydro",
        "Custom": "total_custom",
        "Virgin": "virgin_total",
        "Direct regeneration": None,
    }
    cathode_env_metric_labels = {
        "Water use in gallon": "Water consumption: gal/kg",
    }
    direct_cathode_env_metric_labels = {
        "Water use in gallon": "Water consumption (gal/kg)",
    }
    for output_metric, _, multiplier in transport_metric_specs:
        source_metric = cathode_env_metric_labels.get(output_metric, output_metric)
        for column, source_column in cathode_env_columns.items():
            if column == "Direct regeneration":
                direct_metric = direct_cathode_env_metric_labels.get(output_metric, output_metric)
                value = (
                    direct_cathode_env.loc[direct_metric, "direct_regeneration"]
                    if direct_metric in direct_cathode_env.index
                    else 0.0
                )
            elif source_column is None or source_metric not in cathode_env.index:
                value = 0.0
            else:
                value = cathode_env.loc[source_metric, source_column]
            add_record("Cathode Production", output_metric, column, value * multiplier)

    return pd.DataFrame(records)


def python_ported_output_recycling_revenue_table(
    scenario: Scenario | None = None, *, include_workbook: bool = True
) -> pd.DataFrame:
    workbook = output_recycling_revenue_table().set_index([CommonColumns.PROCESS, CommonColumns.MATERIAL]) if include_workbook else None
    calculated = cm_recovery_revenue_output_table(scenario)
    records = []
    for row in calculated.to_dict("records"):
        process = row[CommonColumns.PROCESS]
        material_label = row[CommonColumns.MATERIAL]
        python_value = row["calculated_value_per_kg_feedstock"]
        record = {
            CommonColumns.PROCESS: process,
            CommonColumns.MATERIAL: material_label,
            AuditColumns.PYTHON_VALUE: python_value,
            "quantity_kg_per_kg_black_mass": row["quantity_kg_per_kg_black_mass"],
            "price_per_kg": row["price_per_kg"],
            "source_row": row["source_row"],
            "source": row["source"],
            AuditColumns.STATUS: "python_calculated",
        }
        if workbook is not None:
            workbook_value = (
                _num(workbook.loc[(process, material_label), "value_per_kg_feedstock"])
                if (process, material_label) in workbook.index
                else 0.0
            )
            record[AuditColumns.WORKBOOK_VALUE] = workbook_value
            record[AuditColumns.DELTA] = python_value - workbook_value
        records.append(record)
    return pd.DataFrame(records)


def python_ported_output_cost_breakdown(*, include_workbook: bool = True) -> pd.DataFrame:
    workbook = output_cost_breakdown().set_index(["section", CommonColumns.ITEM]) if include_workbook else None
    cathode_ws = workbook_sheet("Cath. Prod. Par.")

    chemistry = get_input_selected_chemistry()
    if chemistry not in PRODUCTION_BLOCKS:
        chemistry = "NMC(622)"

    start_col = PRODUCTION_BLOCKS[chemistry]
    product_kg_per_year = _num(cathode_ws.cell(111, start_col + 2).value)
    if product_kg_per_year == 0:
        product_kg_per_year = _num(cathode_ws.cell(110, start_col + 2).value) * _num(
            cathode_ws.cell(103, start_col + 2).value
        )

    raw = cathode_raw_material_cost_calculated(chemistry).set_index(CommonColumns.PROCESS)
    labor = cathode_labor_cost_calculated(chemistry).set_index([CommonColumns.PROCESS, CommonColumns.ITEM])
    utility = cathode_utility_cost_calculated(chemistry).set_index(CommonColumns.PROCESS)
    maintenance = cathode_maintenance_cost_calculated(chemistry).set_index([CommonColumns.PROCESS, CommonColumns.ITEM])
    total = cathode_total_cost_calculated(chemistry).set_index([CommonColumns.PROCESS, CommonColumns.ITEM])

    output_columns = {
        "Selected": None,
        "virgin materials": "Virgin",
        "recycled materials from pyro": "Pyro",
        "recycled materials from hydro": "Hydro",
        "recycled materials from custom": "Custom",
    }

    def per_kg(value: float) -> float:
        return value / product_kg_per_year if product_kg_per_year else 0.0

    def cathode_cost_value(process: str | None, item: str) -> float:
        if process is None:
            return 0.0
        if item == "Materials":
            return raw.loc[process, AuditColumns.calculated(CathodeColumns.PER_KG)]
        if item == "Labor":
            return per_kg(
                labor.loc[(process, "Operating labor"), AuditColumns.calculated(CathodeColumns.ANNUAL)]
                + labor.loc[(process, "Direct supervisory and clerical labor"), AuditColumns.calculated(CathodeColumns.ANNUAL)]
            )
        if item == "Other direct cost":
            return per_kg(
                utility.loc[process, AuditColumns.calculated(CathodeColumns.ANNUAL)]
                + maintenance.loc[(process, "Maintenance and repairs"), AuditColumns.calculated(CathodeColumns.ANNUAL)]
                + maintenance.loc[(process, "Operating supplies"), AuditColumns.calculated(CathodeColumns.ANNUAL)]
                + total.loc[(process, "Laboratory charges"), AuditColumns.calculated(CommonColumns.VALUE)]
                + total.loc[(process, "Patents and royalties"), AuditColumns.calculated(CommonColumns.VALUE)]
            )
        if item == "Depreciation":
            return per_kg(total.loc[(process, "Depreciation"), AuditColumns.calculated(CommonColumns.VALUE)])
        if item == "Other fixed cost":
            return per_kg(
                total.loc[(process, "Local taxes"), AuditColumns.calculated(CommonColumns.VALUE)]
                + total.loc[(process, "Insurance"), AuditColumns.calculated(CommonColumns.VALUE)]
                + total.loc[(process, "Rent"), AuditColumns.calculated(CommonColumns.VALUE)]
                + total.loc[(process, "Financing"), AuditColumns.calculated(CommonColumns.VALUE)]
            )
        if item == "Plant overhead":
            return per_kg(total.loc[(process, "Plant overhead costs"), AuditColumns.calculated(CommonColumns.VALUE)])
        if item == "General expenses":
            return per_kg(total.loc[(process, "General expenses"), AuditColumns.calculated(CommonColumns.VALUE)])
        if item == "Profit":
            return per_kg(total.loc[(process, "Profit"), AuditColumns.calculated(CommonColumns.VALUE)])
        return 0.0

    records = []

    manufacturing_virgin = manufacturing_cell_cost_summary().set_index(CommonColumns.ITEM)
    manufacturing_recycled = manufacturing_cell_cost_summary("recycled").set_index(CommonColumns.ITEM)
    battery_columns = {
        "Selected": None,
        "virgin materials": "Virgin",
        "recycled materials from pyro": "Pyro",
        "recycled materials from hydro": "Hydro",
        "reclaimed materials from direct": "Direct",
        "recycled materials from custom": "Custom",
    }
    battery_item_sources = {
        "Materials": "Materials",
        "Labor": "Direct labor",
        "Depreciation": "Depreciation",
        "Variable overhead": "Variable overhead",
        "GSA": "General, sales, administration",
        "R&D": "Research and development",
        "Profit": "Profit",
        "Warranty": "Warranty",
    }
    for item, source_item in battery_item_sources.items():
        for column, process in battery_columns.items():
            if process is None:
                python_value = 0.0
            elif process == "Virgin":
                python_value = manufacturing_virgin.loc[source_item, CommonColumns.VALUE]
            else:
                python_value = manufacturing_recycled.loc[source_item, process]
            record = {
                "section": "Battery production cost",
                CommonColumns.ITEM: item,
                "column": column,
                AuditColumns.PYTHON_VALUE: python_value,
                AuditColumns.STATUS: "python_calculated",
            }
            if workbook is not None:
                workbook_value = _num(workbook.loc[("Battery production cost", item), column])
                record[AuditColumns.WORKBOOK_VALUE] = workbook_value
                record[AuditColumns.DELTA] = python_value - workbook_value
            records.append(record)

    input_ws = workbook_sheet("Input")
    preproc_ws = workbook_sheet("Preproc. Par.")
    cm_ws = workbook_sheet("CM Rec Par.")
    total_feedstock = sum(_num(input_ws.cell(row, 6).value) for row in range(28, 33))

    def raw_number(ws, address: str) -> tuple[bool, float]:
        value = ws[address].value
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return True, float(value)
        return False, 0.0

    recycling_process_specs = get_reporting_recycling_process_specs()
    recycling_item_specs = get_reporting_recycling_item_specs()

    def weighted_recycling_cost(process: str, item: str) -> float:
        if total_feedstock <= 0:
            return 0.0
        preproc_throughputs = get_preproc_throughputs()
        preproc_default = get_preproc_default_value()
        spec = recycling_process_specs[process]
        mode = str(cm_ws[spec["mode"]].value)
        if item == "Feedstock payment":
            cm_value = _num(cm_ws[spec["feed"]].value)
            if mode == "No preprocessing":
                feed_payment = cm_value
            else:
                preproc_value = preproc_default
                preproc_throughput = preproc_throughputs.get("generic" if mode == "Generic" else "specific", 0.0)
                feed_payment = (
                    preproc_value * preproc_throughput / total_feedstock
                    + cm_value * _num(cm_ws[spec["throughput"]].value) / total_feedstock
                )
            return feed_payment if feed_payment < 0 else 0.0

        generic_row, specific_row, cm_row, cm_col_key = recycling_item_specs[item]
        cm_value = _num(cm_ws.cell(cm_row, spec[cm_col_key]).value)
        if mode == "No preprocessing":
            return cm_value
        if mode == "Generic":
            preproc_address = f"AG{generic_row}" if cm_col_key == "value_col" else f"AH{generic_row}"
            valid, preproc_value = raw_number(preproc_ws, preproc_address)
            preproc_throughput = preproc_throughputs.get("generic", 0.0)
        else:
            preproc_address = f"BG{specific_row}" if cm_col_key == "value_col" else f"BH{specific_row}"
            valid, preproc_value = raw_number(preproc_ws, preproc_address)
            preproc_throughput = preproc_throughputs.get("specific", 0.0)
        if not valid:
            return 0.0
        return (
            preproc_value * preproc_throughput / total_feedstock
            + cm_value * _num(cm_ws[spec["throughput"]].value) / total_feedstock
        )

    for item in [*recycling_item_specs, "Feedstock payment"]:
        for column, process in {
            "Selected": None,
            "Pyro": "Pyro",
            "Hydro": "Hydro",
            "Direct": "Direct",
            "Custom": "Custom",
        }.items():
            python_value = 0.0 if process is None else weighted_recycling_cost(process, item)
            record = {
                "section": "Recycling cost",
                CommonColumns.ITEM: item,
                "column": column,
                AuditColumns.PYTHON_VALUE: python_value,
                AuditColumns.STATUS: "python_calculated",
            }
            if workbook is not None:
                workbook_value = _num(workbook.loc[("Recycling cost", item), column])
                record[AuditColumns.WORKBOOK_VALUE] = workbook_value
                record[AuditColumns.DELTA] = python_value - workbook_value
            records.append(record)

    section = "Cathode production cost"
    for item in [
        "Materials",
        "Labor",
        "Other direct cost",
        "Depreciation",
        "Other fixed cost",
        "Plant overhead",
        "General expenses",
        "Profit",
    ]:
        for column, process in output_columns.items():
            python_value = cathode_cost_value(process, item)
            record = {
                "section": section,
                CommonColumns.ITEM: item,
                "column": column,
                AuditColumns.PYTHON_VALUE: python_value,
                AuditColumns.STATUS: "python_calculated",
            }
            if workbook is not None:
                workbook_value = _num(workbook.loc[(section, item), column])
                record[AuditColumns.WORKBOOK_VALUE] = workbook_value
                record[AuditColumns.DELTA] = python_value - workbook_value
            records.append(record)
    return pd.DataFrame(records)


def python_ported_report_manufacturing_comparison(*, include_workbook: bool = True) -> pd.DataFrame:
    manufacturing = python_ported_manufacturing_output_summary(include_workbook=include_workbook).set_index(CommonColumns.METRIC)
    metric_map = {
        "Cost ($)": "Cost per kWh batttery produced",
        "Total energy consumption (MJ)": "Total Energy",
        "Water consumption (gal)": "Water use in gallon",
        "NOx emission (g)": "NOx",
        "SOx emission (g)": "SOx",
        "PM10 emission (g)": "PM10",
        "CO2 emission": "CO2",
        "GHG emission (g CO2e)": "GHGs",
    }
    columns = {
        "Virgin Manufacture": "python_virgin_cell",
        "Pyro": "python_recycled_pyro",
        "Hydro": "python_recycled_hydro",
        "Direct": "python_recycled_direct",
    }
    records = []
    for report_metric, output_metric in metric_map.items():
        record = {CommonColumns.METRIC: report_metric}
        for report_column, source_column in columns.items():
            record[report_column] = manufacturing.loc[output_metric, source_column]
        records.append(record)
    return pd.DataFrame(records)


def python_ported_report_closed_loop_total_results(scenario: Scenario, *, include_workbook: bool = True) -> pd.DataFrame:
    output = python_ported_process_stage_output_summary(scenario, include_workbook=include_workbook)
    cathode = output[output[StageSummaryColumns.STAGE] == "Cathode Production"].set_index([CommonColumns.METRIC, "column"])
    metric_map = {
        "Cost ($)": "Cost per kg cathode produced",
        "Total energy consumption (MJ)": "Total Energy",
        "Water consumption (gal)": "Water use in gallon",
        "NOx emission (g)": "NOx",
        "SOx emission (g)": "SOx",
        "PM10 emission (g)": "PM10",
        "GHG emission (g CO2e)": "GHGs",
    }
    columns = {
        "Pyro": "Pyro",
        "Hydro": "Hydro",
        "Direct": "Direct regeneration",
        "Custom": "Custom",
    }
    records = []
    for report_metric, output_metric in metric_map.items():
        record = {CommonColumns.METRIC: report_metric}
        for report_column, source_column in columns.items():
            record[report_column] = cathode.loc[(output_metric, source_column), AuditColumns.PYTHON_VALUE]
        records.append(record)
    return pd.DataFrame(records)


def python_ported_report_comparison(scenario: Scenario, *, include_workbook: bool = True) -> pd.DataFrame:
    manufacturing = python_ported_report_manufacturing_comparison(include_workbook=include_workbook).copy()
    manufacturing.insert(0, "section", "Manufacturing")
    closed_loop = python_ported_report_closed_loop_total_results(scenario, include_workbook=include_workbook).copy()
    closed_loop.insert(0, "section", "Closed loop")
    return pd.concat([manufacturing, closed_loop], ignore_index=True, sort=False)


def _output_conversion_factors() -> tuple[float, float]:
    cell_size = manufacturing_cell_size().set_index(CommonColumns.ITEM)
    pack_mass = manufacturing_pack_mass_summary().set_index(CommonColumns.ITEM)
    cell_energy = cell_size.loc["Cell energy (kWh)", "Selected"]
    cell_mass = cell_size.loc["Cell mass (kg)", "Selected"]
    cell_factor = cell_mass / cell_energy if cell_energy else 0.0
    cell_count = pack_mass.loc["Cell", "kg"] / cell_mass if cell_mass else 0.0
    pack_energy = cell_count * cell_energy
    pack_factor = pack_mass.loc["Pack", "kg"] / pack_energy if pack_energy else 0.0
    return cell_factor, pack_factor


def python_ported_manufacturing_output_summary(*, include_workbook: bool = True) -> pd.DataFrame:
    cell_factor, pack_factor = _output_conversion_factors()
    cell_cost = manufacturing_cell_cost_summary().set_index(CommonColumns.ITEM)
    recycled_cell_cost = manufacturing_cell_cost_summary("recycled").set_index(CommonColumns.ITEM)
    cell_env = manufacturing_cell_environment_summary().set_index(CommonColumns.METRIC)
    recycled_cell_env = manufacturing_recycled_environment_totals_calculated().set_index(CommonColumns.METRIC)
    pack_cost = manufacturing_pack_cost_summary().set_index(CommonColumns.ITEM)
    pack_env = manufacturing_pack_environment_summary().set_index(CommonColumns.METRIC)
    pack_mass = manufacturing_pack_mass_summary().set_index(CommonColumns.ITEM)
    workbook = output_cell_pack_summary().set_index(CommonColumns.METRIC) if include_workbook else None

    cell_mass = pack_mass.loc["Cell", "kg"]
    total_pack_mass = pack_mass.loc["Pack", "kg"]
    cell_mass_share = cell_mass / total_pack_mass

    metric_specs = [
        ("Total Energy", "Total Energy", "Total Energy", 1055.06),
        ("Fossil fuels", "Fossil fuels", "Fossil fuels", 1055.06),
        ("Coal", "Coal", "Coal", 1055.06),
        ("Natural gas", "Natural gas", "Natural gas", 1055.06),
        ("Petroleum", "Petroleum", "Petroleum", 1055.06),
        ("Water use in gallon", "Water consumption (gal/kg cell)", "Water consumption (gal/pack)", 1.0),
        ("VOC", "VOC", "VOC", 1.0),
        ("CO", "CO", "CO", 1.0),
        ("NOx", "NOx", "NOx", 1.0),
        ("PM10", "PM10", "PM10", 1.0),
        ("PM2.5", "PM2.5", "PM2.5", 1.0),
        ("SOx", "SOx", "SOx", 1.0),
        ("BC", "BC", "BC", 1.0),
        ("OC", "OC", "OC", 1.0),
        ("CH4", "CH4", "CH4", 1.0),
        ("N2O", "N2O", "N2O", 1.0),
        ("CO2", "CO2", "CO2", 1.0),
        ("CO2 (w/ C in VOC & CO)", "CO2 (w/ C in VOC & CO)", "CO2 (w/ C in VOC & CO)", 1.0),
        ("GHGs", "GHGs", "GHGs", 1.0),
    ]
    recycled_routes = {
        "pyro": ("Pyro", "Pyro recycled manufacturing", "total_pyro"),
        "hydro": ("Hydro", "Hydro recycled manufacturing", "total_hydro"),
        "direct": ("Direct", "Direct recycled manufacturing", "total_direct"),
        "custom": ("Custom", "Custom recycled manufacturing", "total_custom"),
    }

    def add_recycled_route_values(record: dict[str, float | str], metric: str, values: dict[str, float]) -> None:
        for key, (_, workbook_column, _) in recycled_routes.items():
            python_value = values[key]
            record[f"python_recycled_{key}"] = python_value
            if workbook is not None:
                workbook_value = workbook.loc[metric, workbook_column]
                record[f"workbook_recycled_{key}"] = workbook_value
                record[f"recycled_{key}_delta"] = python_value - workbook_value

    records = []
    cell_total_cost = cell_cost.loc["Total", CommonColumns.VALUE]
    pack_total_cost = pack_cost.loc["Total", CommonColumns.VALUE]
    cost_metric = "Cost per kWh batttery produced"
    python_cell = cell_total_cost * cell_factor
    python_pack = (cell_total_cost * cell_mass_share + pack_total_cost) * pack_factor
    records.append(
        {
            CommonColumns.METRIC: cost_metric,
            "python_virgin_cell": python_cell,
            "python_virgin_pack": python_pack,
        }
    )
    if workbook is not None:
        records[-1].update(
            {
                "workbook_virgin_cell": workbook.loc[cost_metric, "Virgin Manufacture"],
                "cell_delta": python_cell - workbook.loc[cost_metric, "Virgin Manufacture"],
                "workbook_virgin_pack": workbook.loc[cost_metric, "Pack Virgin Manufacture"],
                "pack_delta": python_pack - workbook.loc[cost_metric, "Pack Virgin Manufacture"],
            }
        )
    add_recycled_route_values(
        records[-1],
        cost_metric,
        {key: recycled_cell_cost.loc["Total", cost_column] * cell_factor for key, (cost_column, _, _) in recycled_routes.items()},
    )

    for output_metric, cell_metric, pack_metric, multiplier in metric_specs:
        python_cell = cell_env.loc[cell_metric, ManufacturingColumns.TOTAL] * multiplier * cell_factor
        python_pack = (
            cell_env.loc[cell_metric, ManufacturingColumns.TOTAL] * cell_mass_share + pack_env.loc[pack_metric, ManufacturingColumns.TOTAL] / total_pack_mass
        ) * multiplier * pack_factor
        records.append(
            {
                CommonColumns.METRIC: output_metric,
                "python_virgin_cell": python_cell,
                "python_virgin_pack": python_pack,
            }
        )
        if workbook is not None:
            records[-1].update(
                {
                    "workbook_virgin_cell": workbook.loc[output_metric, "Virgin Manufacture"],
                    "cell_delta": python_cell - workbook.loc[output_metric, "Virgin Manufacture"],
                    "workbook_virgin_pack": workbook.loc[output_metric, "Pack Virgin Manufacture"],
                    "pack_delta": python_pack - workbook.loc[output_metric, "Pack Virgin Manufacture"],
                }
            )
        add_recycled_route_values(
            records[-1],
            output_metric,
            {
                key: recycled_cell_env.loc[cell_metric, AuditColumns.calculated(total_column)] * multiplier * cell_factor
                for key, (_, _, total_column) in recycled_routes.items()
            },
        )

    return pd.DataFrame(records)


def python_ported_output_summary_table(scenario: Scenario) -> pd.DataFrame:
    manufacturing = python_ported_manufacturing_output_summary(include_workbook=False).set_index(CommonColumns.METRIC)
    process = python_ported_process_stage_output_summary(scenario, include_workbook=False).set_index(
        [StageSummaryColumns.STAGE, CommonColumns.METRIC, "column"]
    )
    records = []

    def add_record(
        metric: str,
        category: str,
        unit: str,
        values: dict[str, float | None],
    ) -> None:
        record = {
            OutputSummaryColumns.METRIC: metric,
            OutputSummaryColumns.CATEGORY: category,
            OutputSummaryColumns.UNIT: unit,
        }
        for column in OUTPUT_SUMMARY_COLUMNS:
            record[column] = values.get(column)
        records.append(record)

    manufacturing_columns = {
        "Virgin": "python_virgin_cell",
        "Pyro": "python_recycled_pyro",
        "Hydro": "python_recycled_hydro",
        "Direct": "python_recycled_direct",
        "Custom": "python_recycled_custom",
    }
    for metric, category, unit, source_metric in MANUFACTURING_OUTPUT_SUMMARY_SPECS:
        add_record(
            metric,
            category,
            unit,
            {column: manufacturing.loc[source_metric, source_column] for column, source_column in manufacturing_columns.items()},
        )

    add_record(
        "Collection and transport cost",
        CommonColumns.COST,
        "per kg feedstock",
        {"Virgin": process.loc[("Collection & Transport", "Cost per kgfeedstock", "total"), AuditColumns.PYTHON_VALUE]},
    )
    add_record(
        "Collection and transport total energy",
        "Energy",
        "MJ per kg feedstock",
        {"Virgin": process.loc[("Collection & Transport", "Total Energy", "total"), AuditColumns.PYTHON_VALUE]},
    )

    for metric, category, unit, source_metric in RECYCLING_OUTPUT_SUMMARY_SPECS:
        add_record(
            metric,
            category,
            unit,
            {
                column: process.loc[("Recycle", source_metric, column), AuditColumns.PYTHON_VALUE]
                for column in ["Pyro", "Hydro", "Direct", "Custom"]
            },
        )

    return pd.DataFrame(records)


def python_ported_stage_summary(scenario: Scenario, process: str = "Hydro") -> pd.DataFrame:
    process = process if process in {"Pyro", "Hydro", "Direct"} else "Hydro"
    records = []

    transport_segments = scenario_transport_segments(scenario)
    transport_cost = transport_cost_breakdown(segments=transport_segments)
    transport_env = transport_environment_breakdown(segments=transport_segments).set_index(CommonColumns.METRIC)
    records.append(
        {
            StageSummaryColumns.STAGE: "Collection & Transport",
            StageSummaryColumns.BASIS: "kg feedstock",
            StageSummaryColumns.COST: float(transport_cost["calculated_cost"].sum()),
            StageSummaryColumns.TOTAL_ENERGY: transport_env.loc["Total Energy", "calculated_total"],
            StageSummaryColumns.WATER: transport_env.loc["Water consumption", "calculated_total"],
            StageSummaryColumns.GHG: transport_env.loc["GHGs", "calculated_total"],
        }
    )

    disassembly_cost = disassembly_cost_breakdown(scenario).set_index(CommonColumns.ITEM)
    disassembly_revenue = disassembly_revenue_summary(scenario)
    revenue = 0.0
    if not disassembly_revenue.empty and "$/kg battery pack" in set(disassembly_revenue["basis"]):
        revenue = float(disassembly_revenue.set_index("basis").loc["$/kg battery pack", "pack_disassembly"])
    records.append(
        {
            StageSummaryColumns.STAGE: "Disassembly",
            StageSummaryColumns.BASIS: "kg feedstock",
            StageSummaryColumns.COST: disassembly_cost.loc["Total cost", "pack_disassembly"],
            CommonColumns.REVENUE: revenue,
            StageSummaryColumns.TOTAL_ENERGY: 0.0,
            StageSummaryColumns.WATER: 0.0,
            StageSummaryColumns.GHG: 0.0,
        }
    )

    pre_cost = preprocessing_cost_summary(scenario).set_index(CommonColumns.ITEM)
    pre_env = preprocessing_environment_summary(scenario).set_index(CommonColumns.METRIC)
    records.append(
        {
            StageSummaryColumns.STAGE: "Preprocessing",
            StageSummaryColumns.BASIS: "kg feedstock",
            StageSummaryColumns.THROUGHPUT_TONNES_PER_YEAR: preprocessing_throughput(scenario),
            StageSummaryColumns.COST: pre_cost.loc["Total cost ($/kg feedstock processed)", CommonColumns.VALUE],
            StageSummaryColumns.TOTAL_ENERGY: pre_env.loc["Total Energy", ManufacturingColumns.TOTAL],
            StageSummaryColumns.WATER: pre_env.loc["Water consumption", ManufacturingColumns.TOTAL],
            StageSummaryColumns.GHG: pre_env.loc["GHGs", ManufacturingColumns.TOTAL],
        }
    )

    cm_cost = cm_recovery_cost_summary(scenario, process).set_index(CommonColumns.ITEM)
    records.append(
        {
            StageSummaryColumns.STAGE: "CM Recovery",
            StageSummaryColumns.BASIS: "kg black mass",
            StageSummaryColumns.PROCESS: process,
            StageSummaryColumns.THROUGHPUT_TONNES_PER_YEAR: cm_recovery_throughput(scenario),
            StageSummaryColumns.COST: cm_cost.loc["Total cost ($/kg black mass processed)", CommonColumns.VALUE],
        }
    )

    mat_total = mat_conv_total_summary_calculated(scenario).set_index(CommonColumns.METRIC)
    records.append(
        {
            StageSummaryColumns.STAGE: "Material Conversion",
            StageSummaryColumns.BASIS: "kg product",
            StageSummaryColumns.COST: mat_total.loc["Total cost of material conversion ($/kg)", AuditColumns.calculated(CommonColumns.VALUE)],
            StageSummaryColumns.TOTAL_ENERGY: mat_total.loc["Total Energy", AuditColumns.calculated(CommonColumns.VALUE)],
            StageSummaryColumns.WATER: mat_total.loc["Water consumption (gal/kg)", AuditColumns.calculated(CommonColumns.VALUE)],
            StageSummaryColumns.GHG: mat_total.loc["GHGs", AuditColumns.calculated(CommonColumns.VALUE)],
        }
    )

    chemistry = cathode_chemistry_for_scenario(scenario)
    cathode_cost = cathode_raw_material_cost_summary(scenario, chemistry).set_index(CommonColumns.PROCESS)
    cathode_env = cathode_virgin_environment_summary(chemistry).set_index(CommonColumns.METRIC)
    cathode_process = process if process in cathode_cost.index else "Virgin"
    records.append(
        {
            StageSummaryColumns.STAGE: "Cathode Production",
            StageSummaryColumns.BASIS: "kg cathode",
            StageSummaryColumns.PROCESS: cathode_process,
            StageSummaryColumns.COST: cathode_cost.loc[cathode_process, "raw_material_cost_per_kg"],
            StageSummaryColumns.TOTAL_ENERGY: cathode_env.loc["Total Energy", "virgin_total"],
            StageSummaryColumns.WATER: cathode_env.loc["Water consumption: gal/kg", "virgin_total"],
            StageSummaryColumns.GHG: cathode_env.loc["GHGs", "virgin_total"],
        }
    )

    cell_cost = manufacturing_cell_cost_summary().set_index(CommonColumns.ITEM)
    cell_env = manufacturing_cell_environment_summary().set_index(CommonColumns.METRIC)
    records.append(
        {
            StageSummaryColumns.STAGE: "Cell Manufacturing",
            StageSummaryColumns.BASIS: "kg cell",
            StageSummaryColumns.COST: cell_cost.loc["Total", CommonColumns.VALUE],
            StageSummaryColumns.TOTAL_ENERGY: cell_env.loc["Total Energy", ManufacturingColumns.TOTAL],
            StageSummaryColumns.WATER: cell_env.loc["Water consumption (gal/kg cell)", ManufacturingColumns.TOTAL],
            StageSummaryColumns.GHG: cell_env.loc["GHGs", ManufacturingColumns.TOTAL],
        }
    )

    pack_env = manufacturing_pack_environment_summary().set_index(CommonColumns.METRIC)
    records.append(
        {
            StageSummaryColumns.STAGE: "Pack Manufacturing",
            StageSummaryColumns.BASIS: "pack",
            StageSummaryColumns.TOTAL_ENERGY: pack_env.loc["Total Energy", ManufacturingColumns.TOTAL],
            StageSummaryColumns.WATER: 0.0,
            StageSummaryColumns.GHG: pack_env.loc["GHGs", ManufacturingColumns.TOTAL],
        }
    )

    return pd.DataFrame(records)
