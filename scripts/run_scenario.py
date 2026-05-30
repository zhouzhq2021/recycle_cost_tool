from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from recycle_cost.app_services import (  # noqa: E402
    calculated_result_tables,
    csv_bytes,
    parameter_tables_for_scenario,
    recycling_process_key,
    scenario_from_record,
    scenario_json_bytes,
)
from recycle_cost.model import SCENARIO_PRESETS, default_scenario, get_scenario_from_preset  # noqa: E402


RESULT_TABLES = (
    "stage_summary",
    "process_stage",
    "cost_breakdown",
    "recycling_revenue",
    "manufacturing_summary",
    "output_summary",
    "report_results",
)


def slugify(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "_", value.strip()).strip("_")
    return slug or "scenario"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run recycle-cost scenarios and export calculated result tables.")
    parser.add_argument(
        "--preset",
        action="append",
        choices=sorted(SCENARIO_PRESETS),
        help="Built-in scenario preset to run. May be provided multiple times.",
    )
    parser.add_argument(
        "--scenario-json",
        action="append",
        type=Path,
        default=[],
        help="Scenario JSON exported by the app. May be provided multiple times.",
    )
    parser.add_argument("--out-dir", type=Path, default=Path("scenario_runs"), help="Directory for exported runs.")
    parser.add_argument(
        "--process",
        choices=("Pyro", "Hydro", "Direct", "Custom"),
        help="Override the process used by process-specific result tables.",
    )
    parser.add_argument(
        "--include-parameters",
        action="store_true",
        help="Also export current model parameter tables for each scenario.",
    )
    return parser.parse_args()


def load_scenarios(args: argparse.Namespace):
    preset_names = args.preset or ["default"]
    for preset_name in preset_names:
        yield preset_name, get_scenario_from_preset(preset_name)

    fallback = default_scenario()
    for path in args.scenario_json:
        record = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(record, dict):
            raise ValueError(f"{path} must contain a JSON object")
        yield path.stem, scenario_from_record(record, fallback)


def output_metric(result_tables: dict[str, pd.DataFrame], metric: str, column: str) -> float | None:
    output = result_tables["output_summary"].set_index("metric")
    if metric not in output.index or column not in output.columns:
        return None
    value = output.loc[metric, column]
    if pd.isna(value):
        return None
    return float(value)


def scenario_summary(scenario, process: str, result_tables: dict[str, pd.DataFrame]) -> dict[str, object]:
    recycling_cost = output_metric(result_tables, "Recycling cost", process)
    recycling_revenue = output_metric(result_tables, "Recycling revenue", process)
    margin = (
        recycling_revenue - recycling_cost
        if recycling_revenue is not None and recycling_cost is not None
        else None
    )
    return {
        "battery_manufactured": scenario.battery_manufactured,
        "feedstock_chemistry": scenario.feedstock_chemistry,
        "feedstock_type": scenario.feedstock_type,
        "feedstock_tonnes_per_year": scenario.feedstock_tonnes_per_year,
        "recycling_process": scenario.recycling_process,
        "process_key": process,
        "cathode_chemistry": scenario.cathode_chemistry,
        "cathode_throughput_gwh_per_year": scenario.cathode_throughput_gwh_per_year,
        "recycled_content": scenario.recycled_content,
        "recycling_cost_per_kg_feedstock": recycling_cost,
        "recycling_revenue_per_kg_feedstock": recycling_revenue,
        "recycling_margin_per_kg_feedstock": margin,
        "recycling_energy_mj_per_kg_feedstock": output_metric(result_tables, "Recycling total energy", process),
        "recycling_water_gal_per_kg_feedstock": output_metric(result_tables, "Recycling water", process),
        "recycling_ghg_gco2e_per_kg_feedstock": output_metric(result_tables, "Recycling GHGs", process),
    }


def export_tables(run_dir: Path, tables: dict[str, pd.DataFrame]) -> None:
    for name, table in tables.items():
        run_dir.joinpath(f"{slugify(name)}.csv").write_bytes(csv_bytes(table))


def run_one(name: str, scenario, args: argparse.Namespace) -> dict[str, object]:
    process = args.process or recycling_process_key(scenario.recycling_process) or "Hydro"
    result_tables = calculated_result_tables(scenario, process)
    run_dir = args.out_dir / slugify(name)
    run_dir.mkdir(parents=True, exist_ok=True)

    run_dir.joinpath("scenario.json").write_bytes(scenario_json_bytes(scenario))
    export_tables(run_dir, {name: result_tables[name] for name in RESULT_TABLES})

    if args.include_parameters:
        parameter_dir = run_dir / "parameters"
        parameter_dir.mkdir(exist_ok=True)
        export_tables(parameter_dir, parameter_tables_for_scenario(scenario, process))

    summary = scenario_summary(scenario, process, result_tables)
    summary["output_dir"] = str(run_dir)
    run_dir.joinpath("summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def main() -> None:
    args = parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    summaries = [run_one(name, scenario, args) for name, scenario in load_scenarios(args)]
    print(json.dumps(summaries, indent=2))


if __name__ == "__main__":
    main()
