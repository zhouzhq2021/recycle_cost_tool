from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .model import Scenario, scenario_recycling_process_key


@dataclass(frozen=True)
class NewFlowParameterSpec:
    key: str
    label_key: str
    unit: str
    default_value: float | None
    source_key: str
    required: bool = True


def new_flow_parameter_specs(process: str) -> list[NewFlowParameterSpec]:
    process_key = "Direct" if process == "Direct" else "Hydro"
    legacy_cm = {
        "Hydro": {
            "utilities": 4186847.709320695,
            "effluent": 110803.950386937,
            "raw_materials": 35463116.38281767,
            "feed_cost": 2.56,
        },
        "Direct": {
            "utilities": 853333.3333333333,
            "effluent": 43021.90496317933,
            "raw_materials": 49502460.679558605,
            "feed_cost": 3.14,
        },
    }[process_key]
    pre = {
        "nitrogen": 0.05,
        "diesel": 0.6,
        "natural_gas": 2.0,
        "electricity": 0.2,
        "process_water": 0.1,
        "wastewater": 0.1 * 3.78541,
    }
    specs = [
        NewFlowParameterSpec("preprocessing_nitrogen_kg_per_kg", "param_preprocessing_nitrogen", "kg/kg feedstock", pre["nitrogen"], "legacy_preprocessing"),
        NewFlowParameterSpec("preprocessing_diesel_mj_per_kg", "param_preprocessing_diesel", "MJ/kg feedstock", pre["diesel"], "legacy_preprocessing"),
        NewFlowParameterSpec("preprocessing_natural_gas_mj_per_kg", "param_preprocessing_natural_gas", "MJ/kg feedstock", pre["natural_gas"], "legacy_preprocessing"),
        NewFlowParameterSpec("preprocessing_electricity_mj_per_kg", "param_preprocessing_electricity", "MJ/kg feedstock", pre["electricity"], "legacy_preprocessing"),
        NewFlowParameterSpec("preprocessing_process_water_gal_per_kg", "param_preprocessing_water", "gal/kg feedstock", pre["process_water"], "legacy_preprocessing"),
        NewFlowParameterSpec("preprocessing_wastewater_gal_per_kg", "param_preprocessing_wastewater", "gal/kg feedstock", pre["wastewater"], "legacy_preprocessing"),
        NewFlowParameterSpec("cm_utilities_usd_per_year", "param_cm_utilities", "$/yr", legacy_cm["utilities"], "legacy_cm_recovery"),
        NewFlowParameterSpec("cm_effluent_usd_per_year", "param_cm_effluent", "$/yr", legacy_cm["effluent"], "legacy_cm_recovery"),
        NewFlowParameterSpec("cm_raw_materials_usd_per_year", "param_cm_raw_materials", "$/yr", legacy_cm["raw_materials"], "legacy_cm_recovery"),
        NewFlowParameterSpec("cm_feed_cost_usd_per_kg", "param_cm_feed_cost", "$/kg feed", legacy_cm["feed_cost"], "legacy_cm_recovery"),
        NewFlowParameterSpec("preprocessing_cathode_recovery", "param_preprocessing_cathode_recovery", "fraction", 0.95, "legacy_preprocessing"),
        NewFlowParameterSpec("preprocessing_anode_recovery", "param_preprocessing_anode_recovery", "fraction", 0.95, "legacy_preprocessing"),
        NewFlowParameterSpec("preprocessing_aluminum_recovery", "param_preprocessing_aluminum_recovery", "fraction", 0.9, "legacy_preprocessing"),
        NewFlowParameterSpec("preprocessing_copper_recovery", "param_preprocessing_copper_recovery", "fraction", 0.9, "legacy_preprocessing"),
        NewFlowParameterSpec("preprocessing_steel_recovery", "param_preprocessing_steel_recovery", "fraction", 0.9, "legacy_preprocessing"),
        NewFlowParameterSpec("preprocessing_carbon_black_to_anode", "param_preprocessing_carbon_black_to_anode", "fraction", None, "user_required"),
        NewFlowParameterSpec("preprocessing_plastics_recovery", "param_preprocessing_plastics_recovery", "fraction", None, "user_required"),
        NewFlowParameterSpec("preprocessing_electrolyte_lipf6_recovery", "param_preprocessing_electrolyte_lipf6_recovery", "fraction", None, "user_required"),
        NewFlowParameterSpec("preprocessing_electrolyte_solvent_recovery", "param_preprocessing_electrolyte_solvent_recovery", "fraction", None, "user_required"),
        NewFlowParameterSpec("preprocessing_residual_to_s_cathode", "param_preprocessing_residual_to_s_cathode", "fraction", None, "user_required"),
    ]
    if process_key == "Hydro":
        specs.extend(
            [
                NewFlowParameterSpec("hydro_ni_recovery", "param_hydro_ni_recovery", "fraction", None, "user_required"),
                NewFlowParameterSpec("hydro_co_recovery", "param_hydro_co_recovery", "fraction", None, "user_required"),
                NewFlowParameterSpec("hydro_mn_recovery", "param_hydro_mn_recovery", "fraction", None, "user_required"),
                NewFlowParameterSpec("hydro_li_recovery", "param_hydro_li_recovery", "fraction", None, "user_required"),
            ]
        )
    else:
        specs.append(
            NewFlowParameterSpec("direct_rejuvenated_cathode_recovery", "param_direct_rejuvenated_cathode_recovery", "fraction", None, "user_required")
        )
    return specs


def new_flow_parameter_value(
    scenario: Scenario,
    key: str,
    fallback: float | None = None,
) -> float:
    values = scenario.new_flow_parameters or {}
    if key in values:
        return float(values[key])
    for spec in new_flow_parameter_specs(scenario_recycling_process_key(scenario) or "Hydro"):
        if spec.key == key and spec.default_value is not None:
            return float(spec.default_value)
    return float(0.0 if fallback is None else fallback)


def is_new_flow_selected(scenario: Scenario) -> bool:
    return scenario.recycling_flow_variant == "new" and scenario_recycling_process_key(scenario) in {"Hydro", "Direct"}


def new_flow_parameter_table(
    scenario: Scenario,
    text: dict[str, str],
) -> pd.DataFrame:
    process = scenario_recycling_process_key(scenario) or "Hydro"
    values = scenario.new_flow_parameters or {}
    rows = []
    for spec in new_flow_parameter_specs(process):
        current = values.get(spec.key)
        rows.append(
            {
                "key": spec.key,
                text["new_flow_parameter"]: text[spec.label_key],
                text["unit"]: spec.unit,
                text["new_flow_value"]: current if current is not None else spec.default_value,
                text["new_flow_default_source"]: text[spec.source_key],
                text["new_flow_required"]: text["yes"] if spec.required else text["no"],
                text["new_flow_status"]: text["setup_ready"] if current is not None or spec.default_value is not None else text["setup_review"],
            }
        )
    return pd.DataFrame(rows)


def new_flow_parameters_complete(scenario: Scenario) -> bool:
    if not is_new_flow_selected(scenario):
        return True
    values = scenario.new_flow_parameters or {}
    for spec in new_flow_parameter_specs(scenario_recycling_process_key(scenario) or "Hydro"):
        if spec.required and spec.default_value is None and spec.key not in values:
            return False
    return True
