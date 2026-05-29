from __future__ import annotations

import json

import pandas as pd
import streamlit as st

from recycle_cost.app_services import (
    option_index,
    nonnegative_float,
    fraction_float,
    parameter_tables_for_scenario,
    scenario_defaults_from_record,
    scenario_record,
    user_table,
)
from recycle_cost.cathode import (
    cathode_chemistry_for_scenario,
    cathode_material_energy_demand,
    cathode_raw_material_cost_summary,
    cathode_virgin_environment_summary,
    cathode_cost_per_line_summary_calculated,
    cathode_cost_per_line_summary,
)
from recycle_cost.cm_recovery import (
    cm_recovery_capex_summary,
    cm_recovery_cost_summary,
    cm_recovery_equipment_table,
    cm_recovery_product_outputs,
)
from recycle_cost.disassembly import (
    disassembly_cost_breakdown,
    disassembly_feedstock_table,
    disassembly_material_recovery,
    disassembly_revenue_summary,
    disassembly_weight_summary,
)
from recycle_cost.extractors import available_reference_tables
from recycle_cost.mat_conv import (
    mat_conv_allocation_factors_calculated,
    mat_conv_available_precursors,
    mat_conv_conversion_costs,
    mat_conv_recovered_materials,
    mat_conv_recycling_economics_calculated,
    mat_conv_recycling_environment_summary_calculated,
    mat_conv_total_summary_calculated,
)
from recycle_cost.manufacturing import (
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
from recycle_cost.model import (
    FeedstockInput,
    Scenario,
    TransportDistances,
    default_scenario,
    scenario_options,
)
from recycle_cost.preprocessing import (
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
from recycle_cost.reporting import (
    python_ported_manufacturing_output_summary,
    python_ported_output_cost_breakdown,
    python_ported_output_recycling_revenue_table,
    python_ported_output_summary_table,
    python_ported_process_stage_output_summary,
    python_ported_report_comparison,
    python_ported_stage_summary,
)
from recycle_cost.transport import scenario_transport_segments, transport_cost_breakdown, transport_environment_breakdown
from recycle_cost.ui_sections import (
    render_overview_section,
    render_transport_section,
    render_disassembly_section,
    render_preprocessing_section,
    render_cm_recovery_section,
    render_mat_conversion_section,
    render_cathode_section,
    render_manufacturing_section,
    render_parameters_section,
    render_export_section,
)


st.set_page_config(
    page_title="EverBatt Replica",
    page_icon="",
    layout="wide",
)


@st.cache_data(show_spinner=False)
def cached_default_scenario():
    return default_scenario()


@st.cache_data(show_spinner=False)
def cached_scenario_options():
    return scenario_options()


@st.cache_data(show_spinner=False)
def cached_reference_tables():
    return available_reference_tables()


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


TEXT = {
    "zh": {
        "language": "语言 / Language",
        "app_title": "EverBatt 电池回收成本与环境工具",
        "preset": "场景预设",
        "preset_default": "默认：黑粉湿法回收",
        "preset_pack_pyro": "NMC622 电池包火法回收",
        "preset_pack_hydro": "NMC622 电池包湿法回收",
        "preset_pack_direct": "NMC622 电池包直接回收",
        "preset_scrap_direct": "NMC622 制造废料直接回收",
        "scenario_file": "导入场景 JSON",
        "scenario_file_help": "可上传本工具导出的 everbatt_scenario.json 来恢复场景输入。",
        "scenario_loaded": "已载入上传场景。",
        "scenario_invalid": "无法解析上传的场景 JSON，已继续使用所选预设。",
        "production": "生产场景",
        "battery_manufactured": "生产的电池类型",
        "throughput": "制造产能 (GWh/年)",
        "manufacturing_chemistry": "制造电池化学体系",
        "manufacturing_location": "制造地点",
        "feedstock": "回收物料",
        "battery_collected": "收集的电池形态",
        "feedstock_chemistry": "回收物料化学体系",
        "feedstock_type": "回收物料类型",
        "feedstock_tonnes": "回收物料规模 (吨/年)",
        "recycling_process": "回收工艺",
        "cathode": "正极生产",
        "cathode_chemistry": "正极化学体系",
        "chemistry": "化学体系",
        "cathode_throughput": "正极产能 (GWh/年)",
        "recycled_content": "正极再生成分比例",
        "transport": "运输距离",
        "collection_to_disassembly": "收集点到拆解厂",
        "disassembly_to_preprocessor": "拆解厂到预处理厂",
        "preprocessor_to_cm": "预处理厂到黑粉回收厂",
        "manufacturer_to_preprocessor": "制造厂到预处理/回收厂",
        "recycler_to_cathode": "回收厂到正极厂",
        "cathode_to_manufacturer": "正极厂到制造厂",
        "overview": "结果总览",
        "process_flow": "回收流程",
        "cathode_manufacturing": "正极与制造",
        "parameters": "参数表",
        "export": "导出",
        "virgin_cost": "原生电池成本",
        "virgin_energy": "原生电池能耗",
        "pyro_cost": "火法回收成本",
        "hydro_cost": "湿法回收成本",
        "stage_summary": "流程成本与环境汇总",
        "metric": "指标",
        "report_results": "综合结果",
        "transport_cost": "运输成本",
        "transport_env": "运输环境影响",
        "disassembly": "拆解",
        "preprocessing": "预处理",
        "cm_recovery": "黑粉回收",
        "mat_conversion": "材料转换",
        "no_disassembly": "当前场景没有需要拆解的模组/电芯物料，拆解流程为零流量。",
        "select_recycling_process": "请选择火法、湿法或直接回收工艺以计算该模块。",
        "conversion_hint": "材料转换结果随所选回收工艺更新。",
        "materials": "物料",
        "cost": "成本",
        "environment": "环境影响",
        "equipment_capex_opex": "设备、CAPEX 与 OPEX",
        "equipment": "设备",
        "capex": "CAPEX",
        "opex": "OPEX",
        "products": "产品",
        "cost_summary": "成本汇总",
        "environment_summary": "环境汇总",
        "feedstock_streams": "进料流",
        "feedstock_composition": "进料组成",
        "product_outputs": "产品输出",
        "black_mass_composition": "黑粉组成",
        "material_recovery": "材料回收",
        "economics": "经济性",
        "allocation": "分配因子",
        "conversion_costs": "转换成本",
        "recovered_materials": "回收材料",
        "raw_material_costs": "原料成本",
        "required_precursors": "所需前驱体",
        "cathode_demand": "正极物料与能耗",
        "cathode_cost": "正极成本",
        "manufacturing": "电芯与电池包制造",
        "reference_table": "参考参数表",
        "model_parameters": "当前模型参数",
        "parameter_table": "参数表",
        "download": "下载 CSV",
        "export_results": "结果表导出",
        "current_scenario": "当前场景",
        "scenario_inputs": "场景输入",
        "download_scenario": "下载当前场景 JSON",
        "download_bundle": "下载完整结果包 ZIP",
        "field": "字段",
        "value": "值",
        "output_summary": "输出汇总",
        "cost_breakdown": "成本拆分",
        "recycling_revenue": "回收收入",
        "manufacturing_summary": "制造汇总",
        "process_stage": "流程阶段",
        "preprocessing_cost": "预处理成本",
        "cm_cost": "黑粉回收成本",
        "cathode_raw_cost": "正极材料成本",
        "cell_cost": "电芯制造成本",
        "feedstock_label": "进料",
        "pack_weight": "电池包重量",
        "revenue": "收入",
        "throughput_label": "处理量",
        "black_mass": "黑粉",
        "fixed_capital": "固定资本",
        "water": "水耗",
        "cell": "电芯",
        "recycled_cell": "再生材料电芯",
        "pack": "电池包",
        "recycled_energy": "再生电芯能耗",
        "virgin_ghgs": "原生电芯 GHGs",
        "pack_mass": "电池包质量",
        "validation": "输入提示",
        "zero_feedstock": "回收物料规模为 0，回收流程将返回零流量。",
        "black_mass_no_disassembly": "回收物料为黑粉时，拆解和预处理通常不产生进料流量；可切换为电池包/模组/电芯查看完整前处理流程。",
        "select_process_warning": "请选择火法、湿法或直接回收工艺以获得完整回收结果。",
        "cathode_zero": "正极产能为 0 时，部分正极生产成本会按 Excel 默认逻辑显示为 0。",
        "scenario_ready": "当前场景可以计算。",
    },
    "en": {
        "language": "Language / 语言",
        "app_title": "EverBatt Battery Recycling Cost and Environment Tool",
        "preset": "Scenario preset",
        "preset_default": "Default: black mass hydro recovery",
        "preset_pack_pyro": "NMC622 pack pyro recovery",
        "preset_pack_hydro": "NMC622 pack hydro recovery",
        "preset_pack_direct": "NMC622 pack direct recovery",
        "preset_scrap_direct": "NMC622 manufacturing scrap direct recovery",
        "scenario_file": "Import scenario JSON",
        "scenario_file_help": "Upload an everbatt_scenario.json exported from this tool to restore scenario inputs.",
        "scenario_loaded": "Uploaded scenario loaded.",
        "scenario_invalid": "Could not parse the uploaded scenario JSON. The selected preset is still used.",
        "production": "Production Scenario",
        "battery_manufactured": "Battery manufactured at plant",
        "throughput": "Manufacturing throughput (GWh/yr)",
        "manufacturing_chemistry": "Manufacturing chemistry",
        "manufacturing_location": "Manufacturing location",
        "feedstock": "Recycling Feedstock",
        "battery_collected": "Battery collected",
        "feedstock_chemistry": "Feedstock chemistry",
        "feedstock_type": "Feedstock type",
        "feedstock_tonnes": "Feedstock tonnage (tonne/yr)",
        "recycling_process": "Recycling process",
        "cathode": "Cathode Production",
        "cathode_chemistry": "Cathode chemistry",
        "chemistry": "Chemistry",
        "cathode_throughput": "Cathode production throughput (GWh/yr)",
        "recycled_content": "Cathode recycled content",
        "transport": "Transport Distances",
        "collection_to_disassembly": "Collection to disassembly",
        "disassembly_to_preprocessor": "Disassembly to preprocessor",
        "preprocessor_to_cm": "Preprocessor to CM recovery",
        "manufacturer_to_preprocessor": "Manufacturer to preprocessor/CM recovery",
        "recycler_to_cathode": "Recycler to cathode producer",
        "cathode_to_manufacturer": "Cathode producer to manufacturer",
        "overview": "Overview",
        "process_flow": "Recycling Process",
        "cathode_manufacturing": "Cathode and Manufacturing",
        "parameters": "Parameters",
        "export": "Export",
        "virgin_cost": "Virgin battery cost",
        "virgin_energy": "Virgin battery energy",
        "pyro_cost": "Pyro recycling cost",
        "hydro_cost": "Hydro recycling cost",
        "stage_summary": "Process Cost and Environment Summary",
        "metric": "Metric",
        "report_results": "Integrated Results",
        "transport_cost": "Transport Cost",
        "transport_env": "Transport Environmental Impacts",
        "disassembly": "Disassembly",
        "preprocessing": "Preprocessing",
        "cm_recovery": "CM Recovery",
        "mat_conversion": "Material Conversion",
        "no_disassembly": "The current scenario has no module/cell feedstock requiring disassembly, so this flow is zero.",
        "select_recycling_process": "Select Pyrometallurgical, Hydrometallurgical, or Direct to calculate this module.",
        "conversion_hint": "Material conversion output follows the selected recycling process.",
        "materials": "Materials",
        "cost": "Cost",
        "environment": "Environmental impacts",
        "equipment_capex_opex": "Equipment, CAPEX, and OPEX",
        "equipment": "Equipment",
        "capex": "CAPEX",
        "opex": "OPEX",
        "products": "Products",
        "cost_summary": "Cost summary",
        "environment_summary": "Environmental summary",
        "feedstock_streams": "Feedstock streams",
        "feedstock_composition": "Feedstock composition",
        "product_outputs": "Product outputs",
        "black_mass_composition": "Black mass composition",
        "material_recovery": "Material recovery",
        "economics": "Economics",
        "allocation": "Allocation factors",
        "conversion_costs": "Conversion costs",
        "recovered_materials": "Recovered materials",
        "raw_material_costs": "Raw material costs",
        "required_precursors": "Required precursors",
        "cathode_demand": "Cathode material and energy demand",
        "cathode_cost": "Cathode cost",
        "manufacturing": "Cell and Pack Manufacturing",
        "reference_table": "Reference table",
        "model_parameters": "Current model parameters",
        "parameter_table": "Parameter table",
        "download": "Download CSV",
        "export_results": "Export Result Tables",
        "current_scenario": "Current scenario",
        "scenario_inputs": "Scenario inputs",
        "download_scenario": "Download current scenario JSON",
        "download_bundle": "Download full result package ZIP",
        "field": "Field",
        "value": "Value",
        "output_summary": "Output summary",
        "cost_breakdown": "Cost breakdown",
        "recycling_revenue": "Recycling revenue",
        "manufacturing_summary": "Manufacturing summary",
        "process_stage": "Process stage",
        "preprocessing_cost": "Preprocessing cost",
        "cm_cost": "CM recovery cost",
        "cathode_raw_cost": "Cathode material cost",
        "cell_cost": "Cell manufacturing cost",
        "feedstock_label": "Feedstock",
        "pack_weight": "Pack weight",
        "revenue": "Revenue",
        "throughput_label": "Throughput",
        "black_mass": "Black mass",
        "fixed_capital": "Fixed capital",
        "water": "Water",
        "cell": "Cell",
        "recycled_cell": "Recycled cell",
        "pack": "Pack",
        "recycled_energy": "Recycled energy",
        "virgin_ghgs": "Virgin GHGs",
        "pack_mass": "Pack mass",
        "validation": "Input Guidance",
        "zero_feedstock": "Feedstock tonnage is 0, so the recycling process will return zero flow.",
        "black_mass_no_disassembly": "Black mass feedstock usually bypasses disassembly and generic preprocessing. Switch to pack/module/cell feedstock to inspect the full front-end flow.",
        "select_process_warning": "Select Pyrometallurgical, Hydrometallurgical, or Direct to calculate full recycling results.",
        "cathode_zero": "Cathode throughput is 0, so some cathode production costs follow the Excel default behavior and display as 0.",
        "scenario_ready": "Current scenario is ready to calculate.",
    },
}


SCENARIO_PRESETS = {
    "default": {
        "label_key": "preset_default",
        "battery_manufactured": "Pack",
        "throughput": 50.0,
        "manufacturing_chemistry": "NMC(622)",
        "manufacturing_location": "U.S.",
        "battery_collected": "Select Battery",
        "feedstock_chemistry": "NMC(622)",
        "feedstock_type": "Black mass",
        "feedstock_tonnes": 10000.0,
        "recycling_process": "Hydrometallurgical",
        "cathode_chemistry": "NMC(622)",
        "cathode_throughput": 0.0,
        "recycled_content": 0.0,
    },
    "pack_pyro": {
        "label_key": "preset_pack_pyro",
        "battery_manufactured": "Pack",
        "throughput": 50.0,
        "manufacturing_chemistry": "NMC(622)",
        "manufacturing_location": "U.S.",
        "battery_collected": "Module",
        "feedstock_chemistry": "NMC(622)",
        "feedstock_type": "End-of-life battery: pack",
        "feedstock_tonnes": 10000.0,
        "recycling_process": "Pyrometallurgical",
        "cathode_chemistry": "NMC(622)",
        "cathode_throughput": 10.0,
        "recycled_content": 0.2,
    },
    "pack_hydro": {
        "label_key": "preset_pack_hydro",
        "battery_manufactured": "Pack",
        "throughput": 50.0,
        "manufacturing_chemistry": "NMC(622)",
        "manufacturing_location": "U.S.",
        "battery_collected": "Module",
        "feedstock_chemistry": "NMC(622)",
        "feedstock_type": "End-of-life battery: pack",
        "feedstock_tonnes": 10000.0,
        "recycling_process": "Hydrometallurgical",
        "cathode_chemistry": "NMC(622)",
        "cathode_throughput": 10.0,
        "recycled_content": 0.2,
    },
    "pack_direct": {
        "label_key": "preset_pack_direct",
        "battery_manufactured": "Pack",
        "throughput": 50.0,
        "manufacturing_chemistry": "NMC(622)",
        "manufacturing_location": "U.S.",
        "battery_collected": "Module",
        "feedstock_chemistry": "NMC(622)",
        "feedstock_type": "End-of-life battery: pack",
        "feedstock_tonnes": 10000.0,
        "recycling_process": "Direct",
        "cathode_chemistry": "NMC(622)",
        "cathode_throughput": 10.0,
        "recycled_content": 0.2,
    },
    "scrap_direct": {
        "label_key": "preset_scrap_direct",
        "battery_manufactured": "Cell",
        "throughput": 50.0,
        "manufacturing_chemistry": "NMC(622)",
        "manufacturing_location": "U.S.",
        "battery_collected": "Cell",
        "feedstock_chemistry": "NMC(622)",
        "feedstock_type": "Manufacturing scrap: electrode",
        "feedstock_tonnes": 5000.0,
        "recycling_process": "Direct",
        "cathode_chemistry": "NMC(622)",
        "cathode_throughput": 10.0,
        "recycled_content": 0.2,
    },
}


default_base = cached_default_scenario()
options = cached_scenario_options()

with st.sidebar:
    language_choice = st.radio("语言 / Language", ["中文", "English"], horizontal=True)
    lang = "zh" if language_choice == "中文" else "en"
    text = TEXT[lang]
    sidebar_tab_labels = ["场景", "生产", "回收", "运输"] if lang == "zh" else ["Scenario", "Build", "Recycle", "Transport"]
    scenario_tab, production_tab, feedstock_tab, transport_tab = st.tabs(sidebar_tab_labels)

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
                uploaded_record = json.loads(uploaded_bytes.decode("utf-8"))
                if not isinstance(uploaded_record, dict):
                    raise ValueError("Scenario JSON must be an object")
                defaults = scenario_defaults_from_record(uploaded_record, preset)
                control_key = f"{preset_key}_upload_{abs(hash(uploaded_bytes))}"
                st.success(text["scenario_loaded"])
            except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
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
            value=nonnegative_float(defaults.get("cathode_producer_to_manufacturer"), d.cathode_producer_to_manufacturer),
            key=f"{control_key}_cathode_to_manufacturer",
        )

st.title(text["app_title"])

scenario = Scenario(
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
    transport_distances=TransportDistances(
        collection_to_disassembly=collection_to_disassembly,
        disassembly_to_preprocessor=disassembly_to_preprocessor,
        preprocessor_to_cm_recovery=preprocessor_to_cm_recovery,
        manufacturer_to_preprocessor_or_cm_recovery=manufacturer_to_preprocessor,
        recycler_to_cathode_producer=recycler_to_cathode,
        cathode_producer_to_manufacturer=cathode_to_manufacturer,
    ),
    feedstocks=(FeedstockInput(feedstock_chemistry, feedstock_type, feedstock_tonnes),),
)
process = recycling_process_key(scenario.recycling_process)
validation_messages = []
if feedstock_tonnes <= 0:
    validation_messages.append(("warning", text["zero_feedstock"]))
if feedstock_type == "Black mass":
    validation_messages.append(("info", text["black_mass_no_disassembly"]))
if process not in {"Pyro", "Hydro", "Direct"}:
    validation_messages.append(("warning", text["select_process_warning"]))
if cathode_throughput <= 0:
    validation_messages.append(("info", text["cathode_zero"]))

with st.sidebar:
    with st.expander(text["validation"], expanded=bool(validation_messages)):
        if validation_messages:
            for level, message in validation_messages:
                if level == "warning":
                    st.warning(message)
                else:
                    st.info(message)
        else:
            st.success(text["scenario_ready"])

stage_summary = python_ported_stage_summary(scenario, process or "Hydro")
manufacturing_summary = python_ported_manufacturing_output_summary(include_workbook=False)
process_stage = python_ported_process_stage_output_summary(scenario, include_workbook=False)
cost_breakdown = python_ported_output_cost_breakdown(include_workbook=False)
recycling_revenue = python_ported_output_recycling_revenue_table(scenario, include_workbook=False)
report_results = python_ported_report_comparison(scenario, include_workbook=False)
summary = python_ported_output_summary_table(scenario)

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
    render_overview_section(scenario, summary, stage_summary, manufacturing_summary, report_results, text, user_table)

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
        render_cathode_section(
            scenario,
            process or "Direct",
            cathode_material_energy_demand(),
            cathode_virgin_environment_summary(cathode_chemistry_for_scenario(scenario)),
            cathode_raw_material_cost_summary(scenario, cathode_chemistry_for_scenario(scenario)),
            cathode_cost_per_line_summary_calculated(cathode_chemistry_for_scenario(scenario)),
            cathode_cost_per_line_summary(cathode_chemistry_for_scenario(scenario)),
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
    render_parameters_section(parameter_tables_for_scenario(scenario, process or "Hydro"), cached_reference_tables(), text, user_table)

with tabs[4]:
    export_tables = {
        text["current_scenario"]: pd.DataFrame([scenario_record(scenario)]),
        text["stage_summary"]: stage_summary,
        text["process_stage"]: process_stage,
        text["cost_breakdown"]: cost_breakdown,
        text["recycling_revenue"]: recycling_revenue,
        text["manufacturing_summary"]: manufacturing_summary,
        text["output_summary"]: summary,
        text["report_results"]: report_results,
    }
    render_export_section(scenario, export_tables, text)
