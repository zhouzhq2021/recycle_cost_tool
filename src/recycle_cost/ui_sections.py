from __future__ import annotations

import altair as alt
import math
import pandas as pd
import streamlit as st

from .app_services import (
    csv_bytes,
    custom_feedstock_composition_table,
    result_bundle_bytes,
    scenario_display_table,
    scenario_json_bytes,
    scenario_record,
)
from .cathode import cathode_chemistry_for_scenario
from .cm_recovery import cm_recovery_throughput
from .preprocessing import preprocessing_throughput


DEFAULT_TABLE_HEIGHT = 300
COMPACT_TABLE_HEIGHT = 210

PROCESS_LABELS = {
    "Pyro": "Pyro",
    "Hydro": "Hydro",
    "Direct": "Direct",
    "Custom": "Custom",
}


def format_report_number(value) -> str:
    try:
        if value is None or pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return str(value)
    if not math.isfinite(float(value)):
        return ""
    value = float(value)
    abs_value = abs(value)
    if abs_value == 0:
        return "0.0000"
    if abs_value < 1:
        return f"{value:,.6f}"
    if abs_value < 100:
        return f"{value:,.4f}"
    return f"{value:,.2f}"


def format_report_table(data: pd.DataFrame) -> pd.DataFrame:
    table = data.copy()
    for column in table.columns:
        if pd.api.types.is_numeric_dtype(table[column]):
            table[column] = table[column].map(format_report_number)
    return table


def recycling_report_summary_table(output_summary: pd.DataFrame, active_process: str) -> pd.DataFrame:
    output_index = output_summary.set_index("metric")

    def value(metric: str) -> float:
        try:
            return float(output_index.loc[metric, active_process])
        except (KeyError, TypeError, ValueError):
            return 0.0

    cost = value("Recycling cost")
    revenue = value("Recycling revenue")
    rows = [
        ("Recycling cost", cost, "$/kg feedstock"),
        ("Recycling revenue", revenue, "$/kg feedstock"),
        ("Net recycling cost", cost - revenue, "$/kg feedstock"),
        ("Recycling GHGs", value("Recycling GHGs"), "g CO2e/kg feedstock"),
        ("Recycling total energy", value("Recycling total energy"), "MJ/kg feedstock"),
        ("Recycling water", value("Recycling water"), "gal/kg feedstock"),
    ]
    return pd.DataFrame(rows, columns=["metric", active_process, "unit"])


def recycling_route_comparison_table(output_summary: pd.DataFrame) -> pd.DataFrame:
    output_index = output_summary.set_index("metric")
    routes = ["Pyro", "Hydro", "Direct", "Custom"]
    rows = []
    for route in routes:
        cost = _output_metric_value(output_index, "Recycling cost", route)
        revenue = _output_metric_value(output_index, "Recycling revenue", route)
        rows.append(
            {
                "route": route,
                "cost": cost,
                "revenue": revenue,
                "net_cost": cost - revenue,
                "ghgs": _output_metric_value(output_index, "Recycling GHGs", route),
                "energy": _output_metric_value(output_index, "Recycling total energy", route),
                "water": _output_metric_value(output_index, "Recycling water", route),
            }
        )
    return pd.DataFrame(rows)


def production_report_summary_table(output_summary: pd.DataFrame) -> pd.DataFrame:
    output_index = output_summary.set_index("metric")
    rows = [
        ("Cell manufacturing cost", _output_metric_value(output_index, "Cell manufacturing cost", "Virgin"), "$/kWh"),
        ("Cell manufacturing total energy", _output_metric_value(output_index, "Cell manufacturing total energy", "Virgin"), "MJ/kWh"),
        ("Cell manufacturing water", _output_metric_value(output_index, "Cell manufacturing water", "Virgin"), "gal/kWh"),
        ("Cell manufacturing GHGs", _output_metric_value(output_index, "Cell manufacturing GHGs", "Virgin"), "g CO2e/kWh"),
    ]
    return pd.DataFrame(rows, columns=["metric", "Virgin", "unit"])


def _output_metric_value(output_index: pd.DataFrame, metric: str, column: str) -> float:
    try:
        value = output_index.loc[metric, column]
    except (KeyError, TypeError):
        return 0.0
    try:
        if pd.isna(value):
            return 0.0
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def route_comparison_chart(route_comparison: pd.DataFrame, value_column: str, title: str) -> alt.Chart:
    chart_data = route_comparison[["route", value_column]].copy()
    base = alt.Chart(chart_data).encode(
        y=alt.Y("route:N", title=None, sort=["Pyro", "Hydro", "Direct", "Custom"]),
        x=alt.X(f"{value_column}:Q", title=title),
        tooltip=["route", alt.Tooltip(f"{value_column}:Q", format=",.4f")],
    )
    bars = base.mark_bar(cornerRadiusTopRight=3, cornerRadiusBottomRight=3, size=24).encode(
        color=alt.Color("route:N", legend=None, sort=["Pyro", "Hydro", "Direct", "Custom"]),
    )
    labels = base.mark_text(align="left", dx=4, fontSize=11).encode(
        text=alt.Text(f"{value_column}:Q", format=",.2f"),
    )
    return (bars + labels).properties(height=220)


def render_report_table(title: str | None, data: pd.DataFrame, *, height: int = DEFAULT_TABLE_HEIGHT) -> None:
    if title:
        st.markdown(f"**{title}**")
    st.dataframe(format_report_table(data), width="stretch", height=height, hide_index=True, row_height=34)


def render_table(title: str | None, data: pd.DataFrame, text, user_table, *, height: int = DEFAULT_TABLE_HEIGHT) -> None:
    if title:
        st.markdown(f"**{title}**")
    st.dataframe(user_table(data), width="stretch", height=height, hide_index=True, row_height=34)


def render_table_grid(tables, text, user_table, *, columns: int = 2, height: int = COMPACT_TABLE_HEIGHT) -> None:
    for start in range(0, len(tables), columns):
        row = tables[start : start + columns]
        row_height = max((spec[2] if len(spec) > 2 else height) for spec in row)
        cols = st.columns(columns, gap="medium")
        for col, spec in zip(cols, row, strict=False):
            title, data, *_ = spec
            with col:
                render_table(title, data, text, user_table, height=row_height)


def metric_chart(data: pd.DataFrame, metric: str) -> alt.Chart:
    row = data[data["metric"] == metric].iloc[0]
    cases = ["Virgin", "Pyro", "Hydro", "Direct", "Custom"]
    chart_data = (
        pd.DataFrame(
            {
                "case": cases,
                "value": [row["Virgin"], row["Pyro"], row["Hydro"], row["Direct"], row["Custom"]],
            }
        )
        .dropna()
        .query("value == value")
    )
    base = alt.Chart(chart_data).encode(
        y=alt.Y("case:N", title=None, sort=cases),
        x=alt.X("value:Q", title=row["unit"]),
        tooltip=["case", alt.Tooltip("value:Q", format=",.3f")],
    )
    bars = base.mark_bar(cornerRadiusTopRight=3, cornerRadiusBottomRight=3, size=24).encode(
        color=alt.Color("case:N", legend=None, sort=cases),
    )
    labels = base.mark_text(align="left", dx=4, fontSize=11).encode(
        text=alt.Text("value:Q", format=",.2f"),
    )
    return (bars + labels).properties(height=220)


def render_overview_section(
    scenario,
    summary,
    stage_summary,
    manufacturing_summary,
    report_results,
    text,
    user_table,
):
    top = summary.set_index("metric")
    stage_index = stage_summary.set_index("stage")

    cols = st.columns(4)
    cols[0].metric(text["virgin_cost"], f"{top.loc['Cell manufacturing cost', 'Virgin']:.2f} $/kWh")
    cols[1].metric(text["virgin_energy"], f"{top.loc['Cell manufacturing total energy', 'Virgin']:.1f} MJ/kWh")
    cols[2].metric(text["pyro_cost"], f"{top.loc['Recycling cost', 'Pyro']:.2f} $/kg")
    cols[3].metric(text["hydro_cost"], f"{top.loc['Recycling cost', 'Hydro']:.2f} $/kg")

    flow_cols = st.columns(4)
    flow_cols[0].metric(text["preprocessing_cost"], f"{stage_index.loc['Preprocessing', 'cost']:.6f} $/kg")
    flow_cols[1].metric(text["cm_cost"], f"{stage_index.loc['CM Recovery', 'cost']:.6f} $/kg")
    flow_cols[2].metric(text["cathode_raw_cost"], f"{stage_index.loc['Cathode Production', 'cost']:.6f} $/kg")
    flow_cols[3].metric(text["cell_cost"], f"{stage_index.loc['Cell Manufacturing', 'cost']:.6f} $/kg")

    st.subheader(text["scenario_inputs"])
    render_table_grid([(None, scenario_display_table(scenario, text))], text, user_table)
    custom_composition = custom_feedstock_composition_table(scenario)
    if not custom_composition.empty:
        render_table(text["custom_feedstock_composition_comparison"], custom_composition, text, user_table)
    st.download_button(
        text["download_scenario"],
        scenario_json_bytes(scenario),
        file_name="everbatt_scenario.json",
        mime="application/json",
        key="overview_scenario_json",
    )

    st.subheader(text["stage_summary"])
    render_table(None, stage_summary, text, user_table)

    left, right = st.columns([1.2, 0.8], gap="medium")
    with left:
        metric = st.selectbox(text["metric"], summary["metric"].tolist(), index=0)
        render_table(None, summary[summary["metric"] == metric].drop(columns=["category"]), text, user_table, height=220)
    with right:
        st.altair_chart(metric_chart(summary, metric), width="stretch")

    st.subheader(text["report_results"])
    route_comparison = recycling_route_comparison_table(summary)
    chart_cols = st.columns(2, gap="medium")
    with chart_cols[0]:
        st.altair_chart(route_comparison_chart(route_comparison, "net_cost", text["net_recycling_cost"]), width="stretch")
    with chart_cols[1]:
        st.altair_chart(route_comparison_chart(route_comparison, "ghgs", "GHGs"), width="stretch")
    render_table_grid(
        [(text["report_results"], report_results, DEFAULT_TABLE_HEIGHT), (text["manufacturing_summary"], manufacturing_summary)],
        text,
        user_table,
    )


def render_branch_report_section(scenario, result_tables, branch: str, process_key: str, text, user_table) -> None:
    output_summary = result_tables["output_summary"]
    stage_summary = result_tables["stage_summary"]
    manufacturing_summary = result_tables["manufacturing_summary"]
    report_results = result_tables["report_results"]
    process_stage = result_tables["process_stage"]
    cost_breakdown = result_tables["cost_breakdown"]
    recycling_revenue = result_tables["recycling_revenue"]
    active_process = process_key if process_key in PROCESS_LABELS else "Hydro"

    _render_report_header(scenario, branch, active_process, text)
    if branch == "production":
        _render_production_report(output_summary, manufacturing_summary, report_results, text)
    else:
        _render_recycling_report(
            scenario,
            output_summary,
            stage_summary,
            process_stage,
            cost_breakdown,
            recycling_revenue,
            report_results,
            active_process,
            text,
            user_table,
        )
    _render_complete_report_tables(result_tables, text)


def _render_report_header(scenario, branch: str, process_key: str, text) -> None:
    cols = st.columns(4)
    cols[0].metric(text["selected_branch"], text["normal_preparation"] if branch == "production" else text["battery_recycling"])
    cols[1].metric(text["cathode_chemistry"], scenario.cathode_chemistry)
    cols[2].metric(text["manufacturing_location"], scenario.manufacturing_location)
    cols[3].metric(text["recycling_process"], process_key if branch == "recycling" else text["not_applicable"])
    st.caption(text["report_precision_hint"])


def _render_production_report(output_summary, manufacturing_summary, report_results, text) -> None:
    output_index = output_summary.set_index("metric")
    kpi_cols = st.columns(4)
    kpi_cols[0].metric(text["cell_cost"], f"{output_index.loc['Cell manufacturing cost', 'Virgin']:.2f} $/kWh")
    kpi_cols[1].metric(text["virgin_energy"], f"{output_index.loc['Cell manufacturing total energy', 'Virgin']:.2f} MJ/kWh")
    kpi_cols[2].metric(text["water"], f"{output_index.loc['Cell manufacturing water', 'Virgin']:.2f} gal/kWh")
    kpi_cols[3].metric("GHGs", f"{output_index.loc['Cell manufacturing GHGs', 'Virgin']:,.2f} g CO2e/kWh")

    report_table = report_results[report_results["section"] == "Manufacturing"][
        ["metric", "Virgin Manufacture", "Pyro", "Hydro", "Direct", "Custom"]
    ]
    output_table = output_summary[
        output_summary["metric"].astype(str).str.startswith("Cell manufacturing")
    ][["metric", "category", "unit", "Virgin", "Pyro", "Hydro", "Direct", "Custom"]]
    manufacturing_columns = [
        "metric",
        "python_virgin_cell",
        "python_virgin_pack",
        "python_recycled_pyro",
        "python_recycled_hydro",
        "python_recycled_direct",
        "python_recycled_custom",
    ]
    manufacturing_table = manufacturing_summary[[column for column in manufacturing_columns if column in manufacturing_summary.columns]]
    production_summary = production_report_summary_table(output_summary)

    tab_summary, tab_report, tab_output, tab_manufacturing = st.tabs(
        [text["report_key_findings"], text["report_sheet_summary"], text["output_summary"], text["manufacturing_summary"]]
    )
    with tab_summary:
        render_report_table(text["report_key_findings"], production_summary, height=220)
    with tab_report:
        render_report_table(text["production_report"], report_table)
    with tab_output:
        render_report_table(text["production_output_summary"], output_table)
    with tab_manufacturing:
        render_report_table(text["manufacturing_summary"], manufacturing_table, height=420)


def _render_recycling_report(
    scenario,
    output_summary,
    stage_summary,
    process_stage,
    cost_breakdown,
    recycling_revenue,
    report_results,
    active_process: str,
    text,
    user_table,
) -> None:
    output_index = output_summary.set_index("metric")
    kpi_cols = st.columns(4)
    kpi_cols[0].metric(text["recycling_process"], active_process)
    kpi_cols[1].metric(text["cost"], f"{output_index.loc['Recycling cost', active_process]:.4f} $/kg")
    kpi_cols[2].metric(text["revenue"], f"{output_index.loc['Recycling revenue', active_process]:.4f} $/kg")
    net_cost = output_index.loc["Recycling cost", active_process] - output_index.loc["Recycling revenue", active_process]
    kpi_cols[3].metric(text["net_recycling_cost"], f"{net_cost:.4f} $/kg")
    st.caption(f"GHGs: {output_index.loc['Recycling GHGs', active_process]:,.2f} g CO2e/kg")
    with st.expander(text["scenario_inputs"], expanded=False):
        render_table(None, scenario_display_table(scenario, text), text, user_table, height=260)
        custom_composition = custom_feedstock_composition_table(scenario)
        if not custom_composition.empty:
            render_table(text["custom_feedstock_composition_comparison"], custom_composition, text, user_table, height=360)

    stage_table = stage_summary[
        stage_summary["stage"].isin(
            ["Collection & Transport", "Disassembly", "Preprocessing", "CM Recovery", "Material Conversion", "Cathode Production"]
        )
    ]
    process_stage_table = process_stage[
        process_stage["stage"].isin(["Collection & Transport", "Disassembly", "Recycle", "Cathode Production"])
        & process_stage["column"].isin(["total", active_process, "Direct regeneration"])
    ]
    cost_table = cost_breakdown[
        (
            cost_breakdown["section"].isin(["Recycling cost", "Cathode production cost"])
            & cost_breakdown["column"].isin(["Selected", active_process])
        )
        | (
            cost_breakdown["section"].eq("Battery production cost")
            & cost_breakdown["column"].isin(["Selected", f"recycled materials from {active_process.lower()}"])
        )
    ]
    revenue_table = recycling_revenue[recycling_revenue["process"].eq(active_process)]
    closed_loop_report = report_results[report_results["section"].eq("Closed loop")][["metric", "Pyro", "Hydro", "Direct", "Custom"]]
    recycling_output = output_summary[
        output_summary["metric"].astype(str).str.startswith(("Recycling", "Collection"))
    ][["metric", "category", "unit", "Virgin", "Pyro", "Hydro", "Direct", "Custom"]]
    summary_table = recycling_report_summary_table(output_summary, active_process)
    route_comparison = recycling_route_comparison_table(output_summary)

    tab_summary, tab_report, tab_stage, tab_cost, tab_revenue, tab_output = st.tabs(
        [
            text["report_key_findings"],
            text["report_sheet_summary"],
            text["stage_summary"],
            text["cost_breakdown"],
            text["recycling_revenue"],
            text["output_summary"],
        ]
    )
    with tab_summary:
        render_report_table(text["report_key_findings"], summary_table, height=260)
        chart_cols = st.columns(2, gap="medium")
        with chart_cols[0]:
            st.altair_chart(route_comparison_chart(route_comparison, "net_cost", text["net_recycling_cost"]), width="stretch")
        with chart_cols[1]:
            st.altair_chart(route_comparison_chart(route_comparison, "ghgs", "GHGs"), width="stretch")
        render_report_table(text["route_comparison"], route_comparison, height=260)
    with tab_report:
        render_report_table(text["recycling_report"], closed_loop_report)
    with tab_stage:
        render_report_table(text["stage_summary"], stage_table, height=360)
        with st.expander(text["process_stage_details"], expanded=False):
            render_report_table(None, process_stage_table, height=420)
    with tab_cost:
        render_report_table(text["cost_breakdown"], cost_table, height=420)
    with tab_revenue:
        if revenue_table.empty:
            st.info(text["no_recycling_revenue"])
        else:
            render_report_table(text["recycling_revenue"], revenue_table, height=360)
    with tab_output:
        render_report_table(text["recycling_output_summary"], recycling_output)


def _render_complete_report_tables(result_tables, text) -> None:
    with st.expander(text["complete_excel_report_tables"], expanded=False):
        tabs = st.tabs(
            [
                text["output_summary"],
                text["stage_summary"],
                text["process_stage_details"],
                text["cost_breakdown"],
                text["recycling_revenue"],
                text["manufacturing_summary"],
                text["report_results"],
            ]
        )
        table_keys = [
            "output_summary",
            "stage_summary",
            "process_stage",
            "cost_breakdown",
            "recycling_revenue",
            "manufacturing_summary",
            "report_results",
        ]
        for tab, key in zip(tabs, table_keys, strict=True):
            with tab:
                render_report_table(None, result_tables[key], height=460)


def render_transport_section(transport_breakdown, transport_env, text, user_table):
    st.subheader(text["transport_cost"])
    cols = st.columns(2)
    cols[0].metric(text["cost"], f"{transport_breakdown['calculated_cost'].sum():.6f} $/kg")
    cols[1].metric("GHGs", f"{transport_env.set_index('metric').loc['GHGs', 'calculated_total']:.3f}")
    render_table(None, transport_breakdown, text, user_table, height=COMPACT_TABLE_HEIGHT)
    with st.expander(text["transport_env"]):
        render_table(None, transport_env, text, user_table)


def render_disassembly_section(disassembly_weights, disassembly_costs, disassembly_revenue, disassembly_feedstocks, material_recovery, text, user_table):
    st.subheader(text["disassembly"])
    cols = st.columns(4)
    cols[0].metric(text["feedstock_label"], f"{disassembly_weights['pack_equivalent_tonnes_per_year']:,.1f} t/yr")
    cols[1].metric(text["pack_weight"], f"{disassembly_weights['pack_weight_kg']:,.2f} kg")
    cols[2].metric(text["cost"], f"{disassembly_costs.set_index('item').loc['Total cost', 'pack_disassembly']:.6f}")
    cols[3].metric(text["revenue"], f"{disassembly_revenue.set_index('basis').loc['$/kg battery pack', 'pack_disassembly']:.6f}")
    if disassembly_feedstocks.empty:
        st.info(text["no_disassembly"])
    else:
        render_table_grid([(text["feedstock_streams"], disassembly_feedstocks)], text, user_table)
    tab_cost, tab_recovery, tab_revenue = st.tabs([text["cost"], text["material_recovery"], text["revenue"]])
    with tab_cost:
        render_table(None, disassembly_costs, text, user_table)
    with tab_recovery:
        render_table(None, material_recovery, text, user_table)
    with tab_revenue:
        render_table(None, disassembly_revenue, text, user_table)


def render_preprocessing_section(scenario, preprocessing_streams, feedstock_composition, preprocessing_products, black_mass_composition, preprocessing_env, preprocessing_cost, equipment_table, capex_summary, opex_summary, text, user_table):
    st.subheader(text["preprocessing"])
    cols = st.columns(4)
    product_index = preprocessing_products.set_index("product")
    recovered_product = "Black mass" if "Black mass" in product_index.index else "S-Cathode" if "S-Cathode" in product_index.index else None
    recovered_value = product_index.loc[recovered_product, "kg_per_kg_feedstock"] if recovered_product else 0.0
    cols[0].metric(text["throughput_label"], f"{preprocessing_throughput(scenario):,.1f} t/yr")
    cols[1].metric(recovered_product or text["black_mass"], f"{recovered_value:.6f}")
    cols[2].metric("GHGs", f"{preprocessing_env.set_index('metric').loc['GHGs', 'total']:.3f}")
    cols[3].metric(text["cost"], f"{preprocessing_cost.set_index('item').loc['Total cost ($/kg feedstock processed)', 'value']:.6f}")
    tab_a, tab_b, tab_c = st.tabs([text["materials"], text["environment"], text["equipment_capex_opex"]])
    with tab_a:
        render_table_grid(
            [
                (text["feedstock_streams"], preprocessing_streams),
                (text["product_outputs"], preprocessing_products),
                (text["feedstock_composition"], feedstock_composition, DEFAULT_TABLE_HEIGHT),
                (text["black_mass_composition"], black_mass_composition, DEFAULT_TABLE_HEIGHT),
            ],
            text,
            user_table,
        )
    with tab_b:
        render_table(text["environment_summary"], preprocessing_env, text, user_table)
    with tab_c:
        render_table(text["equipment"], equipment_table, text, user_table)
        render_table_grid([(text["capex"], capex_summary), (text["opex"], opex_summary, DEFAULT_TABLE_HEIGHT)], text, user_table)


def render_cm_recovery_section(scenario, process, cm_cost, cm_products, cm_capex, equipment_table, text, user_table):
    st.subheader(text["cm_recovery"])
    if process in {"Pyro", "Hydro", "Direct"}:
        cols = st.columns(4)
        cols[0].metric(text["recycling_process"], process)
        cols[1].metric(text["throughput_label"], f"{cm_recovery_throughput(scenario):,.1f} t/yr")
        cols[2].metric(text["cost"], f"{cm_cost.set_index('item').loc['Total cost ($/kg black mass processed)', 'value']:.6f}")
        cols[3].metric(text["fixed_capital"], f"{cm_capex.set_index('item').loc['Fixed capital investment', 'value']:,.0f}")
        render_table_grid([(text["cost_summary"], cm_cost), (text["products"], cm_products)], text, user_table)
        render_table(text["equipment"], equipment_table, text, user_table)
        render_table_grid([(text["capex"], cm_capex)], text, user_table)
    else:
        st.info(text["select_recycling_process"])


def render_mat_conversion_section(
    scenario,
    process,
    mat_total,
    available_precursors,
    recycling_economics,
    conversion_costs,
    recovered_materials,
    allocation_factors,
    environment_summary,
    text,
    user_table,
):
    st.subheader(text["mat_conversion"])
    if process in {"Pyro", "Hydro", "Direct"}:
        mat_env = mat_total.set_index("metric")
        cols = st.columns(3)
        cols[0].metric(text["cost"], f"{mat_env.loc['Total cost of material conversion ($/kg)', 'calculated_value']:.6f}")
        cols[1].metric("GHGs", f"{mat_env.loc['GHGs', 'calculated_value']:.3f}")
        cols[2].metric(text["water"], f"{mat_env.loc['Water consumption (gal/kg)', 'calculated_value']:.3f}")
        tab_materials, tab_economics, tab_environment, tab_total = st.tabs(
            [text["materials"], text["economics"], text["environment"], text["output_summary"]]
        )
        with tab_materials:
            render_table_grid(
                [(text["required_precursors"], available_precursors), (text["recovered_materials"], recovered_materials)],
                text,
                user_table,
            )
        with tab_economics:
            render_table_grid(
                [
                    (text["economics"], recycling_economics, DEFAULT_TABLE_HEIGHT),
                    (text["conversion_costs"], conversion_costs, DEFAULT_TABLE_HEIGHT),
                    (text["allocation"], allocation_factors),
                ],
                text,
                user_table,
            )
        with tab_environment:
            render_table(text["environment_summary"], environment_summary, text, user_table)
        with tab_total:
            render_table(None, mat_total, text, user_table)
    else:
        st.info(text["conversion_hint"])


def render_cathode_section(
    scenario,
    selected_rec_process,
    cathode_demand,
    cathode_virgin_env,
    cathode_raw_cost,
    cathode_cost_calculated,
    cathode_cost_summary,
    text,
    user_table,
):
    st.subheader(text["cathode"])
    cathode_chemistry = cathode_chemistry_for_scenario(scenario)

    cols = st.columns(4)
    # cathode_demand is a DataFrame, pick representative value or show mass per year
    total_kg = cathode_demand[cathode_demand["category"] == "material_input_kg_per_kg_cathode"][cathode_chemistry].sum()
    cols[0].metric(text["materials"], f"{total_kg:.3f} kg/kg")
    cols[1].metric(text["chemistry"], cathode_chemistry)
    
    cost_val = cathode_cost_calculated.set_index("item").loc["Total product cost to recipient", selected_rec_process] if selected_rec_process in cathode_cost_calculated.columns else 0.0
    cols[2].metric(text["cost"], f"{cost_val:.3f} $/kg")
    
    water_val = cathode_virgin_env.set_index("metric").loc["Water consumption: gal/kg", "virgin_total"]
    cols[3].metric(text["water"], f"{water_val:.3f} gal/kg")

    tab_demand, tab_raw, tab_cost = st.tabs([text["cathode_demand"], text["raw_material_costs"], text["cathode_cost"]])
    with tab_demand:
        render_table(None, cathode_demand, text, user_table)
    with tab_raw:
        render_table_grid([(None, cathode_raw_cost, DEFAULT_TABLE_HEIGHT)], text, user_table)
    with tab_cost:
        render_table_grid(
            [(text["cost_summary"], cathode_cost_summary, DEFAULT_TABLE_HEIGHT), (text["cost_breakdown"], cathode_cost_calculated, DEFAULT_TABLE_HEIGHT)],
            text,
            user_table,
        )


def render_manufacturing_section(
    virgin_cost_summary,
    virgin_env,
    pack_mass,
    recycled_env,
    gen_inputs,
    cell_size,
    cell_mat_inputs,
    recycled_cell_mat_inputs,
    recycled_cell_env,
    recycled_cell_cost,
    recycled_cathode_env,
    recycled_cathode_costs,
    module_masses,
    pack_component_masses,
    pack_env,
    selected_rec_process,
    text,
    user_table,
):
    st.subheader(text["manufacturing"])
    cols = st.columns(4)
    cols[0].metric(text["virgin_cost"], f"{virgin_cost_summary.set_index('item').loc['Total', 'value']:.6f}")
    cols[1].metric(text["virgin_ghgs"], f"{virgin_env.set_index('metric').loc['GHGs', 'total']:.3f}")
    cols[2].metric(text["pack_mass"], f"{pack_mass.set_index('item').loc['Pack', 'kg']:.3f} kg")
    cols[3].metric(text["recycled_energy"], f"{recycled_env.set_index('metric').loc['Total Energy', 'energy_inputs']:.6f}")
    tab_a, tab_b, tab_c = st.tabs([text["cell"], text["recycled_cell"], text["pack"]])
    with tab_a:
        render_table_grid([(text["model_parameters"], gen_inputs), (text["cell"], cell_size)], text, user_table)
        render_table(text["materials"], cell_mat_inputs, text, user_table)
        render_table_grid([(text["cost_summary"], virgin_cost_summary), (text["environment_summary"], virgin_env, DEFAULT_TABLE_HEIGHT)], text, user_table)
    with tab_b:
        render_table(text["materials"], recycled_cell_mat_inputs, text, user_table)
        render_table_grid(
            [
                (text["environment_summary"], recycled_cell_env, DEFAULT_TABLE_HEIGHT),
                (text["cost_summary"], recycled_cell_cost),
                (text["cathode"] + " - " + text["environment"], recycled_cathode_env, DEFAULT_TABLE_HEIGHT),
                (text["cathode"] + " - " + text["cost"], recycled_cathode_costs),
            ],
            text,
            user_table,
        )
    with tab_c:
        render_table_grid(
            [(text["cell"], module_masses), (text["pack"], pack_component_masses), (text["pack_mass"], pack_mass)],
            text,
            user_table,
        )
        render_table(text["environment_summary"], pack_env, text, user_table)


def render_parameters_section(parameter_tables, reference_tables, text, user_table):
    st.subheader(text["model_parameters"])
    parameter_table_name = st.selectbox(text["parameter_table"], list(parameter_tables), index=0)
    parameter_table = parameter_tables[parameter_table_name]
    render_table(None, parameter_table, text, user_table)
    st.download_button(
        text["download"],
        csv_bytes(parameter_table),
        file_name=f"{parameter_table_name.lower().replace(' ', '_')}.csv",
        mime="text/csv",
        key="model_parameter_download",
    )

    st.subheader(text["reference_table"])
    table_name = st.selectbox(text["reference_table"], list(reference_tables), index=0)
    selected_table = reference_tables[table_name]
    render_table(None, selected_table, text, user_table)
    st.download_button(
        text["download"],
        csv_bytes(selected_table),
        file_name=f"{table_name.lower().replace(' ', '_')}.csv",
        mime="text/csv",
        key="reference_parameter_download",
    )


def render_export_section(scenario, export_tables, text):
    st.subheader(text["export_results"])
    st.download_button(
        text["download_bundle"],
        result_bundle_bytes(scenario, export_tables),
        file_name="everbatt_results.zip",
        mime="application/zip",
        key="export_result_bundle",
    )
    st.download_button(
        text["download_scenario"],
        scenario_json_bytes(scenario),
        file_name="everbatt_scenario.json",
        mime="application/json",
        key="export_scenario_json",
    )
    for name, table in export_tables.items():
        st.download_button(
            f"{text['download']} - {name}",
            csv_bytes(table),
            file_name=f"{name.lower().replace(' ', '_')}.csv",
            mime="text/csv",
            key=f"export_csv_{name}",
        )
