from __future__ import annotations

import streamlit as st

from .app_services import (
    calculated_result_tables,
    export_tables_for_scenario,
    parameter_tables_for_scenario,
    user_table,
)
from .cathode import (
    cathode_chemistry_for_scenario,
    cathode_cost_per_line_summary,
    cathode_cost_per_line_summary_calculated,
    cathode_material_energy_demand,
    cathode_raw_material_cost_summary,
    cathode_virgin_environment_summary,
)
from .cm_recovery import (
    cm_recovery_capex_summary,
    cm_recovery_cost_summary,
    cm_recovery_equipment_table,
    cm_recovery_product_outputs,
)
from .disassembly import (
    disassembly_cost_breakdown,
    disassembly_feedstock_table,
    disassembly_material_recovery,
    disassembly_revenue_summary,
    disassembly_weight_summary,
)
from .manufacturing import (
    manufacturing_cell_cost_summary,
    manufacturing_cell_environment_summary,
    manufacturing_cell_material_inputs,
    manufacturing_cell_size,
    manufacturing_general_inputs,
    manufacturing_module_component_masses,
    manufacturing_pack_component_masses,
    manufacturing_pack_environment_summary,
    manufacturing_pack_mass_summary,
    manufacturing_recycled_cathode_material_costs,
    manufacturing_recycled_cathode_material_environment,
    manufacturing_recycled_environment_totals_calculated,
)
from .mat_conv import (
    mat_conv_allocation_factors_calculated,
    mat_conv_available_precursors,
    mat_conv_conversion_costs,
    mat_conv_recovered_materials,
    mat_conv_recycling_economics_calculated,
    mat_conv_recycling_environment_summary_calculated,
    mat_conv_total_summary_calculated,
)
from .model import Scenario
from .preprocessing import (
    preprocessing_black_mass_composition,
    preprocessing_capex_summary,
    preprocessing_cost_summary,
    preprocessing_equipment_table,
    preprocessing_environment_summary,
    preprocessing_feedstock_composition,
    preprocessing_feedstock_streams,
    preprocessing_opex_summary,
    preprocessing_product_outputs,
)
from .transport import scenario_transport_segments, transport_cost_breakdown, transport_environment_breakdown
from .ui_sections import (
    render_cathode_section,
    render_cm_recovery_section,
    render_disassembly_section,
    render_export_section,
    render_manufacturing_section,
    render_mat_conversion_section,
    render_overview_section,
    render_parameters_section,
    render_preprocessing_section,
    render_transport_section,
)


def render_app_pages(
    scenario: Scenario,
    process: str | None,
    text: dict[str, str],
    reference_tables: dict,
) -> None:
    st.title(text["app_title"])

    process_key = process or "Hydro"
    result_tables = calculated_result_tables(scenario, process_key)

    tabs = st.tabs(
        [
            text["overview"],
            text["process_flow"],
            text["cathode_manufacturing"],
            text["parameters"],
            text["export"],
        ]
    )

    with tabs[0]:
        render_overview_section(
            scenario,
            result_tables["output_summary"],
            result_tables["stage_summary"],
            result_tables["manufacturing_summary"],
            result_tables["report_results"],
            text,
            user_table,
        )

    with tabs[1]:
        process_tabs = st.tabs(
            [
                text["transport"],
                text["disassembly"],
                text["preprocessing"],
                text["cm_recovery"],
                text["mat_conversion"],
            ]
        )
        with process_tabs[0]:
            transport_segments = scenario_transport_segments(scenario)
            render_transport_section(
                transport_cost_breakdown(segments=transport_segments),
                transport_environment_breakdown(segments=transport_segments),
                text,
                user_table,
            )
        with process_tabs[1]:
            render_disassembly_section(
                disassembly_weight_summary(scenario),
                disassembly_cost_breakdown(scenario),
                disassembly_revenue_summary(scenario),
                disassembly_feedstock_table(scenario),
                disassembly_material_recovery(scenario),
                text,
                user_table,
            )
        with process_tabs[2]:
            render_preprocessing_section(
                scenario,
                preprocessing_feedstock_streams(scenario),
                preprocessing_feedstock_composition(scenario),
                preprocessing_product_outputs(scenario),
                preprocessing_black_mass_composition(scenario),
                preprocessing_environment_summary(scenario),
                preprocessing_cost_summary(scenario),
                preprocessing_equipment_table(scenario),
                preprocessing_capex_summary(scenario),
                preprocessing_opex_summary(scenario),
                text,
                user_table,
            )
        with process_tabs[3]:
            render_cm_recovery_section(
                scenario,
                process,
                cm_recovery_cost_summary(scenario, process),
                cm_recovery_product_outputs(scenario, process),
                cm_recovery_capex_summary(scenario, process),
                cm_recovery_equipment_table(scenario, process),
                text,
                user_table,
            )
        with process_tabs[4]:
            render_mat_conversion_section(
                scenario,
                process,
                mat_conv_total_summary_calculated(scenario),
                mat_conv_available_precursors(scenario, process),
                mat_conv_recycling_economics_calculated(scenario),
                mat_conv_conversion_costs(scenario),
                mat_conv_recovered_materials(scenario),
                mat_conv_allocation_factors_calculated(scenario),
                mat_conv_recycling_environment_summary_calculated(scenario),
                text,
                user_table,
            )

    with tabs[2]:
        production_tabs = st.tabs([text["cathode"], text["manufacturing"]])
        with production_tabs[0]:
            chemistry = cathode_chemistry_for_scenario(scenario)
            render_cathode_section(
                scenario,
                process or "Direct",
                cathode_material_energy_demand(),
                cathode_virgin_environment_summary(chemistry),
                cathode_raw_material_cost_summary(scenario, chemistry),
                cathode_cost_per_line_summary_calculated(chemistry),
                cathode_cost_per_line_summary(chemistry),
                text,
                user_table,
            )
        with production_tabs[1]:
            render_manufacturing_section(
                manufacturing_cell_cost_summary(),
                manufacturing_cell_environment_summary(),
                manufacturing_pack_mass_summary(),
                manufacturing_cell_environment_summary("recycled"),
                manufacturing_general_inputs(),
                manufacturing_cell_size(),
                manufacturing_cell_material_inputs(),
                manufacturing_cell_material_inputs("recycled"),
                manufacturing_recycled_environment_totals_calculated(),
                manufacturing_cell_cost_summary("recycled"),
                manufacturing_recycled_cathode_material_environment(process or "Direct"),
                manufacturing_recycled_cathode_material_costs(),
                manufacturing_module_component_masses(),
                manufacturing_pack_component_masses(),
                manufacturing_pack_environment_summary(),
                process or "Direct",
                text,
                user_table,
            )

    with tabs[3]:
        render_parameters_section(parameter_tables_for_scenario(scenario, process_key), reference_tables, text, user_table)

    with tabs[4]:
        render_export_section(scenario, export_tables_for_scenario(scenario, result_tables, text), text)
