from __future__ import annotations

import altair as alt
import pandas as pd
import streamlit as st

from .app_services import (
    csv_bytes,
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
    render_table_grid(
        [(text["report_results"], report_results, DEFAULT_TABLE_HEIGHT), (text["manufacturing_summary"], manufacturing_summary)],
        text,
        user_table,
    )


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
    cols[0].metric(text["throughput_label"], f"{preprocessing_throughput(scenario):,.1f} t/yr")
    cols[1].metric(text["black_mass"], f"{preprocessing_products.set_index('product').loc['Black mass', 'kg_per_kg_feedstock']:.6f}")
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
