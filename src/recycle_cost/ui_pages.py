from __future__ import annotations

import pandas as pd
import streamlit as st

from .app_services import (
    calculated_result_tables,
    export_tables_for_scenario,
    option_index,
    parameter_tables_for_scenario,
    recycling_process_key,
    scenario_from_inputs,
    scenario_validation_messages,
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
from .model import SCENARIO_PRESETS, Scenario
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
    render_branch_report_section,
    render_manufacturing_section,
    render_mat_conversion_section,
    render_preprocessing_section,
    render_transport_section,
)
from .ui_sidebar import (
    preset_values,
    run_calculation,
    scenario_values_from_record,
    set_branch,
    set_page,
    set_scenario_values,
)


def render_app_pages(
    scenario: Scenario,
    process: str | None,
    text: dict[str, str],
    reference_tables: dict,
    page: str = "home",
    default_base: Scenario | None = None,
    options=None,
) -> None:
    if page == "global_parameters":
        _render_global_parameter_page(scenario, process or "Hydro", reference_tables, text, default_base, options)
    elif page == "branch_select":
        _render_branch_select_page(text)
    elif page == "branch_parameters":
        _render_branch_parameter_page(scenario, process, text, options)
    elif page == "branch_flow":
        _render_branch_flow_page(scenario, process, text)
    elif page == "module":
        _render_module_page(scenario, process, text)
    elif page == "results":
        _render_results_page(scenario, process or "Hydro", text)
    else:
        _render_home_page(scenario, text)


def _render_home_page(scenario: Scenario, text: dict[str, str]) -> None:
    st.title(text["initial_screen"])
    with st.container(border=True):
        st.markdown(f"### {text['start_workflow_title']}")
        st.write(text["start_workflow_intro"])
        cols = st.columns(3)
        cols[0].metric(text["cathode_chemistry"], scenario.cathode_chemistry)
        cols[1].metric(text["feedstock_chemistry"], scenario.feedstock_chemistry)
        cols[2].metric(text["manufacturing_location"], scenario.manufacturing_location)
        action_cols = st.columns([1, 1])
        if action_cols[0].button(text["configure_global_parameters"], type="primary", width="stretch"):
            set_page("global_parameters")
        if action_cols[1].button(text["select_branch"], width="stretch"):
            set_page("branch_select")


def _render_global_parameter_page(
    scenario: Scenario,
    process_key: str,
    reference_tables: dict,
    text: dict[str, str],
    default_base: Scenario | None,
    options,
) -> None:
    if default_base is None or options is None:
        st.error(text["parameter_page_unavailable"])
        return

    st.title(text["global_parameters"])
    st.write(text["global_parameters_intro"])
    _render_parameter_set_manager(default_base, text)
    current_scenario = scenario_from_inputs(**st.session_state.scenario_values)
    current_process = recycling_process_key(current_scenario.recycling_process) or process_key
    _render_validation(current_scenario, text)
    _render_parameter_library_manager(current_scenario, current_process, reference_tables, text)
    _page_actions(text, previous_page="home", next_page="branch_select")


def _render_branch_select_page(text: dict[str, str]) -> None:
    st.title(text["select_branch"])
    st.write(text["select_branch_intro"])
    cols = st.columns(2, gap="large")
    with cols[0]:
        with st.container(border=True):
            st.markdown(f"### {text['normal_preparation']}")
            st.write(text["production_branch_desc"])
            if st.button(text["choose_production_branch"], type="primary", width="stretch"):
                set_branch("production")
    with cols[1]:
        with st.container(border=True):
            st.markdown(f"### {text['battery_recycling']}")
            st.write(text["recycling_branch_desc"])
            if st.button(text["choose_recycling_branch"], type="primary", width="stretch"):
                set_branch("recycling")
    _page_actions(text, previous_page="global_parameters", next_page="branch_parameters", disable_next=st.session_state.get("branch") is None)


def _render_branch_parameter_page(scenario: Scenario, process: str | None, text: dict[str, str], options) -> None:
    branch = st.session_state.get("branch")
    if branch not in {"production", "recycling"}:
        st.title(text["select_branch"])
        st.info(text["branch_required"])
        if st.button(text["select_branch"], type="primary", width="stretch"):
            set_page("branch_select")
        return
    st.title(text["production_branch_parameters"] if branch == "production" else text["recycling_branch_parameters"])
    st.write(text["branch_parameters_intro"])
    values = dict(st.session_state.scenario_values)

    section = st.session_state.get("active_branch_parameter_section")
    sections = _branch_parameter_sections(branch, text)
    active_section = next((item for item in sections if item[0] == section), None)
    if active_section is None:
        _render_branch_parameter_cards(sections, text)
    else:
        _render_branch_parameter_section(active_section, values, options, text)
        set_scenario_values(values)

    current_scenario = scenario_from_inputs(**values)
    _render_validation(current_scenario, text)
    _page_actions(text, previous_page="branch_select", next_page="branch_flow")


def _render_branch_flow_page(scenario: Scenario, process: str | None, text: dict[str, str]) -> None:
    branch = st.session_state.get("branch")
    if branch == "production":
        st.title(text["normal_preparation_workspace"])
        st.write(text["production_flow_intro"])
        _render_scenario_strip(scenario, process or "Direct", text)
        _render_step_cards(
            [
                ("Cath. Prod. Par.", text["cathode_parameters_desc"], "production_cathode"),
                ("Man Par. - cell", text["cell_manufacturing_desc"], "production_manufacturing"),
                ("Man Par. - pack", text["pack_manufacturing_desc"], "production_manufacturing"),
                ("Output", text["output_parameters_desc"], "results"),
            ],
            text,
            return_page="branch_flow",
            columns=4,
        )
    elif branch == "recycling":
        st.title(text["battery_recycling_workspace"])
        st.caption(text["custom_flow_hint"])
        _render_scenario_strip(scenario, process or "Hydro", text)
        _render_step_cards(
            [
                ("Col&Trans Par.", text["transport_parameters_desc"], "recycling_transport"),
                ("Disassembly", text["disassembly_parameters_desc"], "recycling_disassembly"),
                ("Preproc. Par.", text["preprocessing_parameters_desc"], "recycling_preprocessing"),
                ("CM Rec Par.", text["cm_recovery_parameters_desc"], "recycling_cm"),
                ("Cath. Prod. Par.", text["cathode_parameters_desc"], "recycling_cathode"),
                ("Man Par. - cell", text["cell_manufacturing_desc"], "recycling_manufacturing"),
                ("Man Par. - pack", text["pack_manufacturing_desc"], "recycling_manufacturing"),
                ("Mat. Conv Par.", text["mat_conversion_parameters_desc"], "recycling_matconv"),
                ("Output", text["output_parameters_desc"], "results"),
            ],
            text,
            return_page="branch_flow",
        )
    else:
        st.title(text["select_branch"])
        st.info(text["branch_required"])
        if st.button(text["select_branch"], type="primary", width="stretch"):
            set_page("branch_select")
        return
    _flow_actions(text, previous_page="branch_parameters")


def _render_module_page(scenario: Scenario, process: str | None, text: dict[str, str]) -> None:
    active = st.session_state.get("active_module", "recycling_transport")
    title = _module_title(active, text)
    st.title(title)
    _render_scenario_strip(scenario, process or "Hydro", text)
    return_page = st.session_state.get("module_return_page", "branch_flow")
    top_actions = st.columns([1, 1, 2])
    if top_actions[0].button(text["back_to_flow"], key="module_top_back_to_flow", width="stretch"):
        set_page(return_page)
    if top_actions[1].button(text["run_calculation"], key="module_top_run_calculation", width="stretch"):
        run_calculation()
    st.divider()
    if active.startswith("production_"):
        if active == "production_manufacturing":
            _render_manufacturing_section(process, text)
        else:
            _render_cathode_section(scenario, process, text)
    else:
        _render_recycling_module(active, scenario, process, text)
    _flow_actions(text, previous_page=return_page)


def _render_results_page(scenario: Scenario, process_key: str, text: dict[str, str]) -> None:
    branch = st.session_state.get("branch")
    title = text["production_report"] if branch == "production" else text["recycling_report"] if branch == "recycling" else text["results_workspace"]
    st.title(title)
    if branch not in {"production", "recycling"}:
        st.info(text["branch_required_before_calculation"])
        if st.button(text["select_branch"], type="primary", width="stretch"):
            set_page("branch_select")
        _page_actions(text, previous_page="home", next_page="branch_select")
        return
    if not st.session_state.get("calculation_done", False):
        st.info(text["calculation_required"])
        if st.button(text["run_calculation"], width="stretch"):
            run_calculation()
        _page_actions(text, previous_page="branch_flow", next_page="home")
        return
    result_tables = calculated_result_tables(scenario, process_key)
    render_branch_report_section(
        scenario,
        result_tables,
        branch,
        process_key,
        text,
        user_table,
    )
    render_export_section(scenario, export_tables_for_scenario(scenario, result_tables, text), text)
    _page_actions(text, previous_page="branch_flow", next_page="home")


def _render_parameter_library_manager(
    scenario: Scenario,
    process_key: str,
    reference_tables: dict,
    text: dict[str, str],
) -> None:
    st.subheader(text["parameter_library_title"])
    st.write(text["parameter_library_intro"])

    libraries = _parameter_library_specs(scenario, process_key, reference_tables, text)
    active_key = st.session_state.get("active_parameter_library")
    active_spec = next((spec for spec in libraries if spec["key"] == active_key), None)
    if active_spec is None:
        st.caption(text["parameter_library_picker_hint"])
        _render_parameter_group_cards(libraries, text)
        return

    _render_parameter_group_editor(active_spec, text)


def _render_parameter_set_manager(default_base: Scenario, text: dict[str, str]) -> None:
    st.subheader(text["parameter_set_title"])
    st.write(text["parameter_set_intro"])
    preset_labels = {key: text[value["label_key"]] for key, value in SCENARIO_PRESETS.items()}
    cols = st.columns([1, 1, 1], gap="large")
    if cols[0].button(text["use_default_parameter_set"], width="stretch"):
        st.session_state.preset_key = "default"
        st.session_state.parameter_libraries = {}
        st.session_state.active_parameter_library = None
        set_scenario_values(preset_values(default_base, "default"))
        st.success(text["default_parameter_set_loaded"])
    selected_preset = cols[1].selectbox(
        text["preset"],
        list(SCENARIO_PRESETS),
        format_func=lambda key: preset_labels[key],
        index=option_index(tuple(SCENARIO_PRESETS), str(st.session_state.get("preset_key", "default"))),
        key="parameter_set_preset",
    )
    if cols[2].button(text["load_preset_parameter_set"], width="stretch"):
        st.session_state.preset_key = selected_preset
        st.session_state.parameter_libraries = {}
        st.session_state.active_parameter_library = None
        set_scenario_values(preset_values(default_base, selected_preset))
        st.success(text["preset_parameter_set_loaded"])

    uploaded_scenario = st.file_uploader(
        text["scenario_file"],
        type=["json"],
        help=text["scenario_file_help"],
    )
    if uploaded_scenario is not None:
        try:
            import json

            record = json.loads(uploaded_scenario.getvalue().decode("utf-8"))
            if not isinstance(record, dict):
                raise ValueError("Scenario JSON must be an object")
            set_scenario_values(scenario_values_from_record(record, default_base))
            st.session_state.parameter_libraries = {}
            st.session_state.active_parameter_library = None
            st.success(text["scenario_loaded"])
        except (UnicodeDecodeError, ValueError):
            st.warning(text["scenario_invalid"])


def _render_parameter_group_cards(libraries: list[dict[str, object]], text: dict[str, str]) -> None:
    for start in range(0, len(libraries), 3):
        cols = st.columns(3, gap="large")
        for col, spec in zip(cols, libraries[start : start + 3], strict=False):
            table_count = len(spec["tables"])
            with col:
                with st.container(border=True):
                    st.markdown(f"### {spec['label']}")
                    st.caption(spec["subtitle"])
                    st.write(spec["description"])
                    st.caption(f"{text['parameter_group_tables']}: {table_count}")
                    if st.button(text["edit_parameter_group"], key=f"open_parameter_group_{spec['key']}", width="stretch"):
                        st.session_state.active_parameter_library = spec["key"]
                        st.rerun()


def _render_parameter_group_editor(spec: dict[str, object], text: dict[str, str]) -> None:
    top_cols = st.columns([1, 2])
    if top_cols[0].button(text["back_to_parameter_groups"], width="stretch"):
        st.session_state.active_parameter_library = None
        st.rerun()
    top_cols[1].markdown(f"### {spec['label']}")
    st.caption(spec["description"])

    table_names = list(spec["tables"])
    selected_table = st.selectbox(
        text["library_table"],
        table_names,
        key=f"library_table_{spec['key']}",
    )
    table_key = f"{spec['key']}::{selected_table}"
    source_table = spec["tables"][selected_table]
    stored_tables = st.session_state.setdefault("parameter_libraries", {})
    current_table = stored_tables.get(table_key, user_table(source_table))
    current_table = current_table.copy().reset_index(drop=True)
    search = st.text_input(
        text["search_parameter"],
        key=f"library_search_{spec['key']}_{selected_table}",
        help=text["search_parameter_help"],
    )
    edited_table = _render_searchable_parameter_editor(current_table, search, spec["key"], selected_table, text)
    if not edited_table.equals(current_table):
        stored_tables[table_key] = edited_table
        st.session_state.calculation_done = False
        _sync_parameter_table_to_scenario_values(selected_table, edited_table, text)
        st.success(text["parameter_library_saved"])


def _render_searchable_parameter_editor(
    table: pd.DataFrame,
    search: str,
    library_key: str,
    table_name: str,
    text: dict[str, str],
) -> pd.DataFrame:
    if search.strip():
        mask = table.astype(str).agg(" ".join, axis=1).str.contains(search.strip(), case=False, na=False)
        visible_table = table.loc[mask].copy()
        st.caption(f"{text['filtered_table_editing']} · {len(visible_table)} / {len(table)}")
        edited_visible = st.data_editor(
            visible_table,
            key=f"library_editor_filtered_{library_key}_{table_name}_{search}",
            width="stretch",
            height=420,
            num_rows="fixed",
        )
        edited_table = table.copy()
        edited_table.loc[edited_visible.index, edited_visible.columns] = edited_visible
        return edited_table

    st.caption(f"{text['full_table_editing']} · {len(table)} {text['table_rows_shown']}")
    return st.data_editor(
        table,
        key=f"library_editor_full_{library_key}_{table_name}",
        width="stretch",
        height=420,
        num_rows="dynamic",
    )


def _sync_parameter_table_to_scenario_values(table_name: str, table: pd.DataFrame, text: dict[str, str]) -> None:
    values = dict(st.session_state.scenario_values)
    updated = False
    if table_name == "Scenario inputs" and {"parameter", "value"}.issubset(table.columns):
        for row in table[["parameter", "value"]].to_dict("records"):
            key = str(row["parameter"])
            if key in values:
                values[key] = _coerce_scenario_value(row["value"], values[key])
                updated = True
    elif table_name == "Transport distances" and {"route", "distance_miles"}.issubset(table.columns):
        for row in table[["route", "distance_miles"]].to_dict("records"):
            key = str(row["route"])
            if key in values:
                values[key] = _coerce_scenario_value(row["distance_miles"], values[key])
                updated = True
    if updated:
        set_scenario_values(values)
        st.info(text["scenario_table_synced"])


def _coerce_scenario_value(value: object, existing: object) -> object:
    if isinstance(existing, (int, float)) and not isinstance(existing, bool):
        try:
            return float(value)
        except (TypeError, ValueError):
            return existing
    return "" if value is None else str(value)


def _parameter_library_specs(
    scenario: Scenario,
    process_key: str,
    reference_tables: dict,
    text: dict[str, str],
) -> list[dict[str, object]]:
    parameter_tables = parameter_tables_for_scenario(scenario, process_key)
    return [
        {
            "key": "unit_ops",
            "label": "Unit Ops",
            "subtitle": text["unit_ops_card"],
            "description": text["unit_ops_desc"],
            "tables": {
                "Scenario inputs": parameter_tables["Scenario inputs"],
                "Transport distances": parameter_tables["Transport distances"],
                "Preprocessing product yields": parameter_tables["Preprocessing product yields"],
                "CM recovery product yields": parameter_tables["CM recovery product yields"],
                "Cathode conversion costs": parameter_tables["Cathode conversion costs"],
            },
        },
        {
            "key": "materials",
            "label": "Materials",
            "subtitle": text["materials_card"],
            "description": text["materials_desc"],
            "tables": {
                "Material prices": reference_tables["Material prices"],
                "Cathode required precursors": parameter_tables["Cathode required precursors"],
                "Cathode chemical prices": parameter_tables["Cathode chemical prices"],
                "Cathode utility prices": parameter_tables["Cathode utility prices"],
                "CM recovery product prices": parameter_tables["CM recovery product prices"],
            },
        },
        {
            "key": "geographic",
            "label": "Geographic Par.",
            "subtitle": text["geographic_card"],
            "description": text["geographic_desc"],
            "tables": {
                "Geographic parameters": reference_tables["Geographic parameters"],
            },
        },
        {
            "key": "batpac",
            "label": "BatPaC IO",
            "subtitle": text["batpac_card"],
            "description": text["batpac_desc"],
            "tables": {
                "BatPaC material costs": reference_tables["BatPaC material costs"],
            },
        },
        {
            "key": "greet",
            "label": "GREET IO",
            "subtitle": text["greet_card"],
            "description": text["greet_desc"],
            "tables": {
                "GREET combustion factors": reference_tables["GREET combustion factors"],
                "Material conversion recycling environment": parameter_tables["Material conversion recycling environment"],
                "Material conversion cathode-only environment": parameter_tables[
                    "Material conversion cathode-only environment"
                ],
            },
        },
    ]


def _render_step_cards(
    cards: list[tuple[str, str, str]],
    text: dict[str, str],
    *,
    return_page: str,
    columns: int = 3,
) -> None:
    for start in range(0, len(cards), columns):
        cols = st.columns(columns, gap="large")
        for offset, (col, (title, desc, target)) in enumerate(zip(cols, cards[start : start + columns], strict=False)):
            step_no = start + offset + 1
            with col:
                with st.container(border=True):
                    st.caption(f"{step_no:02d} · {text['calculated_module'] if target == 'results' else text['editable_module']}")
                    st.markdown(f"**{title}**")
                    st.write(desc)
                    if st.button(text["click_to_enter"], key=f"enter_{start + offset}_{target}", width="stretch"):
                        if target == "results":
                            set_page("results")
                        else:
                            set_page("module", module=target, return_page=return_page)


def _branch_parameter_sections(branch: str, text: dict[str, str]) -> list[tuple[str, str, str]]:
    if branch == "production":
        return [
            ("production_product", text["production_product_parameters"], text["production_product_parameters_desc"]),
            ("production_capacity", text["production_capacity_parameters"], text["production_capacity_parameters_desc"]),
            ("production_cathode", text["production_cathode_parameters"], text["production_cathode_parameters_desc"]),
        ]
    return [
        ("recycling_feedstock", text["recycling_feedstock_parameters"], text["recycling_feedstock_parameters_desc"]),
        ("recycling_process", text["recycling_process_parameters"], text["recycling_process_parameters_desc"]),
        ("recycling_transport", text["recycling_transport_parameters"], text["recycling_transport_parameters_desc"]),
    ]


def _render_branch_parameter_cards(sections: list[tuple[str, str, str]], text: dict[str, str]) -> None:
    st.caption(text["branch_parameter_picker_hint"])
    cols = st.columns(len(sections), gap="large")
    for index, (col, (section_key, title, desc)) in enumerate(zip(cols, sections, strict=True), start=1):
        with col:
            with st.container(border=True):
                st.caption(f"{index:02d} · {text['branch_specific_parameter_group']}")
                st.markdown(f"### {title}")
                st.write(desc)
                if st.button(text["edit_parameter_group"], key=f"open_branch_parameter_{section_key}", width="stretch"):
                    st.session_state.active_branch_parameter_section = section_key
                    st.rerun()


def _render_branch_parameter_section(
    section: tuple[str, str, str],
    values: dict[str, object],
    options,
    text: dict[str, str],
) -> None:
    section_key, title, desc = section
    header_cols = st.columns([1, 2])
    if header_cols[0].button(text["back_to_branch_parameter_groups"], width="stretch"):
        st.session_state.active_branch_parameter_section = None
        st.rerun()
    header_cols[1].markdown(f"### {title}")
    st.caption(desc)
    if section_key == "production_product":
        _render_production_product_parameters(values, options, text)
    elif section_key == "production_capacity":
        _render_production_capacity_parameters(values, options, text)
    elif section_key == "production_cathode":
        _render_production_cathode_parameters(values, options, text)
    elif section_key == "recycling_feedstock":
        _render_recycling_feedstock_parameters(values, options, text)
    elif section_key == "recycling_process":
        _render_recycling_process_parameters(values, options, text)
    elif section_key == "recycling_transport":
        _render_recycling_transport_parameters(values, text)


def _render_recycling_module(active: str, scenario: Scenario, process: str | None, text: dict[str, str]) -> None:
    if active == "recycling_disassembly":
        render_disassembly_section(
            disassembly_weight_summary(scenario),
            disassembly_cost_breakdown(scenario),
            disassembly_revenue_summary(scenario),
            disassembly_feedstock_table(scenario),
            disassembly_material_recovery(scenario),
            text,
            user_table,
        )
    elif active == "recycling_preprocessing":
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
    elif active == "recycling_cm":
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
    elif active == "recycling_matconv":
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
    elif active == "recycling_cathode":
        _render_cathode_section(scenario, process, text)
    elif active == "recycling_manufacturing":
        _render_manufacturing_section(process, text)
    else:
        transport_segments = scenario_transport_segments(scenario)
        render_transport_section(
            transport_cost_breakdown(segments=transport_segments),
            transport_environment_breakdown(segments=transport_segments),
            text,
            user_table,
        )


def _render_cathode_section(scenario: Scenario, process: str | None, text: dict[str, str]) -> None:
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


def _render_manufacturing_section(process: str | None, text: dict[str, str]) -> None:
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


def _page_actions(text: dict[str, str], *, previous_page: str, next_page: str, disable_next: bool = False) -> None:
    st.divider()
    cols = st.columns([1, 1, 1])
    if cols[0].button(text["back"], key=f"page_actions_back_{previous_page}_{next_page}", width="stretch"):
        set_page(previous_page)
    if cols[1].button(text["home"], key=f"page_actions_home_{previous_page}_{next_page}", width="stretch"):
        set_page("home")
    if cols[2].button(text["next_step"], key=f"page_actions_next_{previous_page}_{next_page}", disabled=disable_next, width="stretch"):
        set_page(next_page)


def _flow_actions(text: dict[str, str], *, previous_page: str) -> None:
    st.divider()
    cols = st.columns([1, 1, 1])
    if cols[0].button(text["back"], key=f"flow_actions_back_{previous_page}", width="stretch"):
        set_page(previous_page)
    if cols[1].button(text["home"], key=f"flow_actions_home_{previous_page}", width="stretch"):
        set_page("home")
    if cols[2].button(text["run_calculation"], key=f"flow_actions_run_{previous_page}", width="stretch"):
        run_calculation()


def _render_production_product_parameters(values: dict[str, object], options, text: dict[str, str]) -> None:
    values["battery_manufactured"] = st.selectbox(
        text["battery_manufactured"],
        options.battery_manufactured,
        index=option_index(options.battery_manufactured, str(values["battery_manufactured"])),
    )
    values["manufacturing_chemistry"] = st.selectbox(
        text["manufacturing_chemistry"],
        options.chemistries,
        index=option_index(options.chemistries, str(values["manufacturing_chemistry"])),
    )


def _render_production_capacity_parameters(values: dict[str, object], options, text: dict[str, str]) -> None:
    values["throughput_gwh_per_year"] = st.number_input(
        text["throughput"],
        min_value=0.0,
        value=float(values["throughput_gwh_per_year"]),
    )
    values["cathode_throughput_gwh_per_year"] = st.number_input(
        text["cathode_throughput"],
        min_value=0.0,
        value=float(values["cathode_throughput_gwh_per_year"]),
    )


def _render_production_cathode_parameters(values: dict[str, object], options, text: dict[str, str]) -> None:
    values["cathode_chemistry"] = st.selectbox(
        text["cathode_chemistry"],
        options.cathode_chemistries,
        index=option_index(options.cathode_chemistries, str(values["cathode_chemistry"])),
    )
    values["recycled_content"] = st.number_input(
        text["recycled_content"],
        min_value=0.0,
        max_value=1.0,
        step=0.05,
        value=float(values["recycled_content"]),
    )


def _render_recycling_feedstock_parameters(values: dict[str, object], options, text: dict[str, str]) -> None:
    values["battery_collected"] = st.selectbox(
        text["battery_collected"],
        options.battery_collected,
        index=option_index(options.battery_collected, str(values["battery_collected"])),
    )
    values["feedstock_chemistry"] = st.selectbox(
        text["feedstock_chemistry"],
        options.chemistries,
        index=option_index(options.chemistries, str(values["feedstock_chemistry"])),
    )
    values["feedstock_type"] = st.selectbox(
        text["feedstock_type"],
        options.feedstock_types,
        index=option_index(options.feedstock_types, str(values["feedstock_type"])),
    )
    values["feedstock_tonnes_per_year"] = st.number_input(
        text["feedstock_tonnes"],
        min_value=0.0,
        value=float(values["feedstock_tonnes_per_year"]),
    )


def _render_recycling_process_parameters(values: dict[str, object], options, text: dict[str, str]) -> None:
    values["recycling_process"] = st.selectbox(
        text["recycling_process"],
        options.recycling_processes,
        index=option_index(options.recycling_processes, str(values["recycling_process"])),
    )


def _render_recycling_transport_parameters(values: dict[str, object], text: dict[str, str]) -> None:
    left, right = st.columns(2, gap="large")
    with left:
        values["collection_to_disassembly"] = st.number_input(
            text["collection_to_disassembly"],
            min_value=0.0,
            value=float(values["collection_to_disassembly"]),
        )
        values["disassembly_to_preprocessor"] = st.number_input(
            text["disassembly_to_preprocessor"],
            min_value=0.0,
            value=float(values["disassembly_to_preprocessor"]),
        )
        values["preprocessor_to_cm_recovery"] = st.number_input(
            text["preprocessor_to_cm"],
            min_value=0.0,
            value=float(values["preprocessor_to_cm_recovery"]),
        )
    with right:
        values["manufacturer_to_preprocessor_or_cm_recovery"] = st.number_input(
            text["manufacturer_to_preprocessor"],
            min_value=0.0,
            value=float(values["manufacturer_to_preprocessor_or_cm_recovery"]),
        )
        values["recycler_to_cathode_producer"] = st.number_input(
            text["recycler_to_cathode"],
            min_value=0.0,
            value=float(values["recycler_to_cathode_producer"]),
        )
        values["cathode_producer_to_manufacturer"] = st.number_input(
            text["cathode_to_manufacturer"],
            min_value=0.0,
            value=float(values["cathode_producer_to_manufacturer"]),
        )


def _render_validation(scenario: Scenario, text: dict[str, str]) -> None:
    validation_messages = scenario_validation_messages(scenario, text)
    with st.expander(text["validation"], expanded=bool(validation_messages)):
        if validation_messages:
            for level, message in validation_messages:
                if level == "warning":
                    st.warning(message)
                else:
                    st.info(message)
        else:
            st.success(text["scenario_ready"])


def _module_title(module: str, text: dict[str, str]) -> str:
    labels = {
        "production_cathode": "Cath. Prod. Par.",
        "production_manufacturing": "Man Par.",
        "recycling_transport": "Col&Trans Par.",
        "recycling_disassembly": text["disassembly"],
        "recycling_preprocessing": "Preproc. Par.",
        "recycling_cm": "CM Rec Par.",
        "recycling_cathode": "Cath. Prod. Par.",
        "recycling_manufacturing": "Man Par.",
        "recycling_matconv": "Mat. Conv Par.",
    }
    return labels.get(module, text["process_flow"])


def _render_scenario_strip(scenario: Scenario, process_key: str, text: dict[str, str]) -> None:
    cols = st.columns(4)
    cols[0].metric(text["cathode_chemistry"], scenario.cathode_chemistry)
    cols[1].metric(text["recycling_process"], process_key)
    cols[2].metric(text["manufacturing_location"], scenario.manufacturing_location)
    cols[3].metric(text["feedstock_label"], f"{scenario.feedstock_tonnes_per_year:,.0f} t/yr")
