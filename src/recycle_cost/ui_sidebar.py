from __future__ import annotations

from dataclasses import dataclass

import streamlit as st

from .app_services import (
    fraction_float,
    nonnegative_float,
    option_index,
    recycling_process_key,
    scenario_defaults_from_json_bytes,
    scenario_from_inputs,
    scenario_validation_messages,
)
from .i18n import SIDEBAR_TAB_LABELS, TEXT
from .model import SCENARIO_PRESETS, Scenario, ScenarioOptions


@dataclass(frozen=True)
class SidebarState:
    scenario: Scenario
    process: str | None
    text: dict[str, str]


def render_sidebar(default_base: Scenario, options: ScenarioOptions) -> SidebarState:
    with st.sidebar:
        language_choice = st.radio("语言 / Language", ["中文", "English"], horizontal=True)
        lang = "zh" if language_choice == "中文" else "en"
        text = TEXT[lang]
        scenario_tab, production_tab, feedstock_tab, transport_tab = st.tabs(SIDEBAR_TAB_LABELS[lang])

        with scenario_tab:
            preset_labels = {key: text[value["label_key"]] for key, value in SCENARIO_PRESETS.items()}
            preset_key = st.selectbox(
                text["preset"],
                list(SCENARIO_PRESETS),
                format_func=lambda key: preset_labels[key],
                index=0,
            )
            preset = SCENARIO_PRESETS[preset_key]
            defaults = dict(preset)
            control_key = preset_key
            uploaded_scenario = st.file_uploader(
                text["scenario_file"],
                type=["json"],
                help=text["scenario_file_help"],
            )
            if uploaded_scenario is not None:
                try:
                    uploaded_bytes = uploaded_scenario.getvalue()
                    defaults = scenario_defaults_from_json_bytes(uploaded_bytes, preset)
                    control_key = f"{preset_key}_upload_{abs(hash(uploaded_bytes))}"
                    st.success(text["scenario_loaded"])
                except (UnicodeDecodeError, ValueError):
                    st.warning(text["scenario_invalid"])

        with production_tab:
            st.markdown(f"**{text['manufacturing']}**")
            battery_manufactured = st.selectbox(
                text["battery_manufactured"],
                options.battery_manufactured,
                index=option_index(options.battery_manufactured, str(defaults["battery_manufactured"])),
                key=f"{control_key}_battery_manufactured",
            )
            throughput = st.number_input(
                text["throughput"],
                min_value=0.0,
                value=nonnegative_float(defaults["throughput"]),
                key=f"{control_key}_throughput",
            )
            manufacturing_chemistry = st.selectbox(
                text["manufacturing_chemistry"],
                options.chemistries,
                index=option_index(options.chemistries, str(defaults["manufacturing_chemistry"])),
                key=f"{control_key}_manufacturing_chemistry",
            )
            manufacturing_location = st.selectbox(
                text["manufacturing_location"],
                options.locations,
                index=option_index(options.locations, str(defaults["manufacturing_location"])),
                key=f"{control_key}_manufacturing_location",
            )

            st.markdown(f"**{text['cathode']}**")
            cathode_chemistry = st.selectbox(
                text["cathode_chemistry"],
                options.cathode_chemistries,
                index=option_index(options.cathode_chemistries, str(defaults["cathode_chemistry"])),
                key=f"{control_key}_cathode_chemistry",
            )
            cathode_throughput = st.number_input(
                text["cathode_throughput"],
                min_value=0.0,
                value=nonnegative_float(defaults["cathode_throughput"]),
                key=f"{control_key}_cathode_throughput",
            )
            recycled_content = st.number_input(
                text["recycled_content"],
                min_value=0.0,
                max_value=1.0,
                step=0.05,
                value=fraction_float(defaults["recycled_content"]),
                key=f"{control_key}_recycled_content",
            )

        with feedstock_tab:
            st.markdown(f"**{text['feedstock']}**")
            battery_collected = st.selectbox(
                text["battery_collected"],
                options.battery_collected,
                index=option_index(options.battery_collected, str(defaults["battery_collected"])),
                key=f"{control_key}_battery_collected",
            )
            feedstock_chemistry = st.selectbox(
                text["feedstock_chemistry"],
                options.chemistries,
                index=option_index(options.chemistries, str(defaults["feedstock_chemistry"])),
                key=f"{control_key}_feedstock_chemistry",
            )
            feedstock_type = st.selectbox(
                text["feedstock_type"],
                options.feedstock_types,
                index=option_index(options.feedstock_types, str(defaults["feedstock_type"])),
                key=f"{control_key}_feedstock_type",
            )
            feedstock_tonnes = st.number_input(
                text["feedstock_tonnes"],
                min_value=0.0,
                value=nonnegative_float(defaults["feedstock_tonnes"]),
                key=f"{control_key}_feedstock_tonnes",
            )

            st.markdown(f"**{text['recycling_process']}**")
            recycling_process = st.selectbox(
                text["recycling_process"],
                options.recycling_processes,
                index=option_index(options.recycling_processes, str(defaults["recycling_process"])),
                key=f"{control_key}_recycling_process",
            )

        with transport_tab:
            d = default_base.transport_distances
            collection_to_disassembly = st.number_input(
                text["collection_to_disassembly"],
                min_value=0.0,
                value=nonnegative_float(defaults.get("collection_to_disassembly"), d.collection_to_disassembly),
                key=f"{control_key}_collection_to_disassembly",
            )
            disassembly_to_preprocessor = st.number_input(
                text["disassembly_to_preprocessor"],
                min_value=0.0,
                value=nonnegative_float(defaults.get("disassembly_to_preprocessor"), d.disassembly_to_preprocessor),
                key=f"{control_key}_disassembly_to_preprocessor",
            )
            preprocessor_to_cm_recovery = st.number_input(
                text["preprocessor_to_cm"],
                min_value=0.0,
                value=nonnegative_float(defaults.get("preprocessor_to_cm_recovery"), d.preprocessor_to_cm_recovery),
                key=f"{control_key}_preprocessor_to_cm_recovery",
            )
            manufacturer_to_preprocessor = st.number_input(
                text["manufacturer_to_preprocessor"],
                min_value=0.0,
                value=nonnegative_float(
                    defaults.get("manufacturer_to_preprocessor_or_cm_recovery"),
                    d.manufacturer_to_preprocessor_or_cm_recovery,
                ),
                key=f"{control_key}_manufacturer_to_preprocessor",
            )
            recycler_to_cathode = st.number_input(
                text["recycler_to_cathode"],
                min_value=0.0,
                value=nonnegative_float(defaults.get("recycler_to_cathode_producer"), d.recycler_to_cathode_producer),
                key=f"{control_key}_recycler_to_cathode",
            )
            cathode_to_manufacturer = st.number_input(
                text["cathode_to_manufacturer"],
                min_value=0.0,
                value=nonnegative_float(
                    defaults.get("cathode_producer_to_manufacturer"),
                    d.cathode_producer_to_manufacturer,
                ),
                key=f"{control_key}_cathode_to_manufacturer",
            )

        scenario = scenario_from_inputs(
            battery_manufactured=battery_manufactured,
            throughput_gwh_per_year=throughput,
            manufacturing_chemistry=manufacturing_chemistry,
            manufacturing_location=manufacturing_location,
            battery_collected=battery_collected,
            feedstock_chemistry=feedstock_chemistry,
            feedstock_type=feedstock_type,
            feedstock_tonnes_per_year=feedstock_tonnes,
            recycling_process=recycling_process,
            cathode_chemistry=cathode_chemistry,
            recycled_content=recycled_content,
            cathode_throughput_gwh_per_year=cathode_throughput,
            collection_to_disassembly=collection_to_disassembly,
            disassembly_to_preprocessor=disassembly_to_preprocessor,
            preprocessor_to_cm_recovery=preprocessor_to_cm_recovery,
            manufacturer_to_preprocessor_or_cm_recovery=manufacturer_to_preprocessor,
            recycler_to_cathode_producer=recycler_to_cathode,
            cathode_producer_to_manufacturer=cathode_to_manufacturer,
        )
        process = recycling_process_key(scenario.recycling_process)
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

    return SidebarState(scenario=scenario, process=process, text=text)
