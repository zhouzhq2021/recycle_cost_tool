from __future__ import annotations

from dataclasses import dataclass

import streamlit as st

from .app_services import fraction_float, nonnegative_float, recycling_process_key, scenario_from_inputs
from .i18n import TEXT
from .model import SCENARIO_PRESETS, Scenario


PAGE_KEYS = ("home", "global_parameters", "branch_select", "branch_parameters", "branch_flow", "module", "results")
BRANCH_KEYS = ("production", "recycling")


@dataclass(frozen=True)
class SidebarState:
    scenario: Scenario
    process: str | None
    text: dict[str, str]
    page: str
    branch: str | None


def render_sidebar(default_base: Scenario, options) -> SidebarState:
    _ensure_app_state(default_base)
    with st.sidebar:
        language_choice = st.radio("语言 / Language", ["中文", "English"], horizontal=True)
        lang = "zh" if language_choice == "中文" else "en"
        text = TEXT[lang]
        st.divider()
        _render_workflow_nav(text)
        st.divider()
        _render_sidebar_summary(text)

    scenario = scenario_from_inputs(**st.session_state.scenario_values)
    process = recycling_process_key(scenario.recycling_process)
    return SidebarState(
        scenario=scenario,
        process=process,
        text=text,
        page=st.session_state.page,
        branch=st.session_state.branch,
    )


def set_page(page: str, *, module: str | None = None, return_page: str | None = None) -> None:
    st.session_state.page = page
    if module is not None:
        st.session_state.active_module = module
    if return_page is not None:
        st.session_state.module_return_page = return_page
    st.rerun()


def set_branch(branch: str | None) -> None:
    st.session_state.branch = branch if branch in BRANCH_KEYS else None
    st.session_state.active_branch_parameter_section = None
    st.session_state.calculation_done = False
    st.session_state.page = "branch_parameters" if st.session_state.branch else "branch_select"
    st.rerun()


def run_calculation() -> None:
    if st.session_state.get("branch") not in BRANCH_KEYS:
        st.session_state.calculation_done = False
        st.session_state.page = "branch_select"
    else:
        st.session_state.calculation_done = True
        st.session_state.page = "results"
    st.rerun()


def set_scenario_values(values: dict[str, object]) -> None:
    if values != st.session_state.scenario_values:
        st.session_state.calculation_done = False
    merged = dict(values)
    merged.setdefault("recycling_flow_variant", st.session_state.get("recycling_flow_variant", "old"))
    st.session_state.scenario_values = merged


def preset_values(default_base: Scenario, preset_key: str) -> dict[str, object]:
    preset = SCENARIO_PRESETS[preset_key]
    distances = default_base.transport_distances
    return {
        "battery_manufactured": str(preset["battery_manufactured"]),
        "throughput_gwh_per_year": nonnegative_float(preset["throughput"]),
        "manufacturing_chemistry": str(preset["manufacturing_chemistry"]),
        "manufacturing_location": str(preset["manufacturing_location"]),
        "battery_collected": str(preset["battery_collected"]),
        "feedstock_chemistry": str(preset["feedstock_chemistry"]),
        "feedstock_type": str(preset["feedstock_type"]),
        "feedstock_tonnes_per_year": nonnegative_float(preset["feedstock_tonnes"]),
        "recycling_process": str(preset["recycling_process"]),
        "recycling_flow_variant": "old",
        "cathode_chemistry": str(preset["cathode_chemistry"]),
        "recycled_content": fraction_float(preset["recycled_content"]),
        "cathode_throughput_gwh_per_year": nonnegative_float(preset["cathode_throughput"]),
        "collection_to_disassembly": distances.collection_to_disassembly,
        "disassembly_to_preprocessor": distances.disassembly_to_preprocessor,
        "preprocessor_to_cm_recovery": distances.preprocessor_to_cm_recovery,
        "manufacturer_to_preprocessor_or_cm_recovery": distances.manufacturer_to_preprocessor_or_cm_recovery,
        "recycler_to_cathode_producer": distances.recycler_to_cathode_producer,
        "cathode_producer_to_manufacturer": distances.cathode_producer_to_manufacturer,
    }


def scenario_values_from_record(record: dict[str, object], default_base: Scenario) -> dict[str, object]:
    values = preset_values(default_base, "default")
    for key in values:
        if key in record and record[key] is not None:
            values[key] = record[key]
    feedstocks = record.get("feedstocks")
    if isinstance(feedstocks, list) and feedstocks and isinstance(feedstocks[0], dict):
        first = feedstocks[0]
        values["feedstock_chemistry"] = first.get("chemistry", values["feedstock_chemistry"])
        values["feedstock_type"] = first.get("feedstock_type", values["feedstock_type"])
        values["feedstock_tonnes_per_year"] = first.get("tonnes_per_year", values["feedstock_tonnes_per_year"])
    return _clean_values(values)


def _ensure_app_state(default_base: Scenario) -> None:
    if "scenario_values" not in st.session_state:
        st.session_state.scenario_values = preset_values(default_base, "default")
    if "preset_key" not in st.session_state:
        st.session_state.preset_key = "default"
    if "page" not in st.session_state or st.session_state.page not in PAGE_KEYS:
        st.session_state.page = "home"
    if "branch" not in st.session_state or st.session_state.branch not in (*BRANCH_KEYS, None):
        st.session_state.branch = None
    if "module_return_page" not in st.session_state:
        st.session_state.module_return_page = "branch_flow"
    if "active_branch_parameter_section" not in st.session_state:
        st.session_state.active_branch_parameter_section = None
    if "recycling_flow_variant" not in st.session_state:
        st.session_state.recycling_flow_variant = "old"
    if "calculation_done" not in st.session_state:
        st.session_state.calculation_done = False
    st.session_state.scenario_values["recycling_flow_variant"] = st.session_state.recycling_flow_variant


def _clean_values(values: dict[str, object]) -> dict[str, object]:
    numeric_keys = {
        "throughput_gwh_per_year",
        "feedstock_tonnes_per_year",
        "recycled_content",
        "cathode_throughput_gwh_per_year",
        "collection_to_disassembly",
        "disassembly_to_preprocessor",
        "preprocessor_to_cm_recovery",
        "manufacturer_to_preprocessor_or_cm_recovery",
        "recycler_to_cathode_producer",
        "cathode_producer_to_manufacturer",
    }
    cleaned = dict(values)
    for key in numeric_keys:
        cleaned[key] = fraction_float(cleaned.get(key)) if key == "recycled_content" else nonnegative_float(cleaned.get(key))
    return cleaned


def _render_workflow_nav(text: dict[str, str]) -> None:
    st.caption(text["workflow"])
    steps = [("home", text["start"]), ("global_parameters", text["global_parameters"]), ("branch_select", text["select_branch"])]
    if st.session_state.branch == "production":
        steps.extend(
            [
                ("branch_parameters", text["production_branch_parameters"]),
                ("branch_flow", text["normal_preparation"]),
                ("results", text["production_report"]),
            ]
        )
    elif st.session_state.branch == "recycling":
        steps.extend(
            [
                ("branch_parameters", text["recycling_branch_parameters"]),
                ("branch_flow", text["battery_recycling"]),
                ("results", text["recycling_report"]),
            ]
        )
    for page, label in steps:
        disabled = page in {"branch_parameters", "branch_flow", "results"} and st.session_state.branch is None
        button_type = "primary" if st.session_state.page == page else "secondary"
        if st.button(label, key=f"nav_{page}_{st.session_state.branch}", type=button_type, disabled=disabled, width="stretch"):
            set_page(page)
    if st.session_state.branch:
        if st.button(text["change_branch"], key="change_branch", width="stretch"):
            st.session_state.branch = None
            st.session_state.active_branch_parameter_section = None
            st.session_state.calculation_done = False
            set_page("branch_select")


def _render_sidebar_summary(text: dict[str, str]) -> None:
    values = st.session_state.scenario_values
    branch = st.session_state.branch
    branch_label = text["normal_preparation"] if branch == "production" else text["battery_recycling"] if branch == "recycling" else text["not_selected"]
    st.caption(text["current_scenario"])
    st.write(f"{text['selected_branch']}: **{branch_label}**")
    if branch == "recycling":
        flow_variant = text["new_recycling_flow"] if st.session_state.get("recycling_flow_variant") == "new" else text["old_recycling_flow"]
        st.write(f"{text['recycling_flow_version']}: **{flow_variant}**")
    st.write(f"{text['cathode_chemistry']}: **{values['cathode_chemistry']}**")
    st.write(f"{text['feedstock_chemistry']}: **{values['feedstock_chemistry']}**")
    st.write(f"{text['manufacturing_location']}: **{values['manufacturing_location']}**")
    if st.session_state.get("calculation_done", False):
        st.success(text["calculation_done"])
    else:
        st.info(text["calculation_pending"])
