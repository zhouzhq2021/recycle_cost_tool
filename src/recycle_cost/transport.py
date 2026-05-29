from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .model import Scenario
from .parameters import number, workbook_number, workbook_sheet, yes
from .schemas import AuditColumns, CommonColumns, TransportColumns


KG_TO_SHORT_TON = 0.0011


@dataclass(frozen=True)
class TransportRates:
    heavy_payload_ton: float
    medium_payload_ton: float
    rail_per_ton_mile: float
    ocean_tanker_per_ton_mile: float
    barge_per_ton_mile: float
    heavy_truck_nonhaz_per_mile: float
    heavy_truck_haz_per_mile: float
    medium_truck_nonhaz_per_mile: float
    medium_truck_haz_per_mile: float
    packaging_nonhaz_per_kg: float
    packaging_haz_per_kg: float


@dataclass(frozen=True)
class TransportSegment:
    name: str
    total_distance_miles: float
    rail_miles: float
    heavy_truck_miles: float
    medium_truck_miles: float
    ocean_tanker_miles: float
    barge_miles: float
    transported_weight_kg_per_kg_feedstock: float
    hazardous: bool
    packaging_rule: str
    workbook_row: int
    rail_outbound_miles: float = 0.0
    rail_backhaul_miles: float = 0.0
    heavy_truck_outbound_miles: float = 0.0
    heavy_truck_backhaul_miles: float = 0.0
    medium_truck_outbound_miles: float = 0.0
    medium_truck_backhaul_miles: float = 0.0
    ocean_tanker_outbound_miles: float = 0.0
    ocean_tanker_backhaul_miles: float = 0.0
    barge_outbound_miles: float = 0.0
    barge_backhaul_miles: float = 0.0


ENERGY_METRICS = [
    ("Total Energy", 81, 146, "upstream"),
    ("Fossil fuels", 82, 147, "upstream"),
    ("Coal", 83, 148, "factor"),
    ("Natural gas", 84, 149, "factor"),
    ("Petroleum", 85, 150, "upstream"),
    ("Water consumption", 86, 151, "water"),
]

EMISSION_METRICS = [
    ("VOC", 88, 131, 153),
    ("CO", 89, 132, 154),
    ("NOx", 90, 133, 155),
    ("PM10", 91, 134, 156),
    ("PM2.5", 92, 135, 157),
    ("SOx", 93, 136, 158),
    ("BC", 94, 137, 159),
    ("OC", 95, 138, 160),
    ("CH4", 96, 139, 161),
    ("N2O", 97, 140, 162),
    ("CO2", 98, 141, 163),
]


def _num(value) -> float:
    return number(value)


def _yes(value) -> bool:
    return yes(value)


def default_transport_rates() -> TransportRates:
    return TransportRates(
        heavy_payload_ton=workbook_number("Col&Trans Par.", "C35"),
        medium_payload_ton=workbook_number("Col&Trans Par.", "C36"),
        rail_per_ton_mile=workbook_number("Col&Trans Par.", "C41"),
        ocean_tanker_per_ton_mile=workbook_number("Col&Trans Par.", "C42"),
        barge_per_ton_mile=workbook_number("Col&Trans Par.", "C43"),
        heavy_truck_nonhaz_per_mile=workbook_number("Col&Trans Par.", "C46"),
        heavy_truck_haz_per_mile=workbook_number("Col&Trans Par.", "F46"),
        medium_truck_nonhaz_per_mile=workbook_number("Col&Trans Par.", "C47"),
        medium_truck_haz_per_mile=workbook_number("Col&Trans Par.", "F47"),
        packaging_nonhaz_per_kg=workbook_number("Col&Trans Par.", "C50"),
        packaging_haz_per_kg=workbook_number("Col&Trans Par.", "F50"),
    )


def default_transport_segments() -> list[TransportSegment]:
    ws = workbook_sheet("Col&Trans Par.")
    rows = [
        (20, 21, 53, 61, "first_leg"),
        (22, 23, 54, 62, "after_first_haz"),
        (24, 25, 55, 63, "black_mass"),
        (26, 27, 56, 64, "always_if_distance"),
        (28, 29, 57, 65, "none"),
        (30, 31, 58, 66, "none"),
    ]
    segments = []
    for outbound_row, backhaul_row, hazard_row, weight_row, packaging_rule in rows:
        rail_out = _num(ws.cell(outbound_row, 4).value)
        rail_back = _num(ws.cell(backhaul_row, 4).value)
        heavy_out = _num(ws.cell(outbound_row, 5).value)
        heavy_back = _num(ws.cell(backhaul_row, 5).value)
        medium_out = _num(ws.cell(outbound_row, 6).value)
        medium_back = _num(ws.cell(backhaul_row, 6).value)
        ocean_out = _num(ws.cell(outbound_row, 7).value)
        ocean_back = _num(ws.cell(backhaul_row, 7).value)
        barge_out = _num(ws.cell(outbound_row, 8).value)
        barge_back = _num(ws.cell(backhaul_row, 8).value)
        distances = {
            "rail_miles": rail_out + rail_back,
            "heavy_truck_miles": heavy_out + heavy_back,
            "medium_truck_miles": medium_out + medium_back,
            "ocean_tanker_miles": ocean_out + ocean_back,
            "barge_miles": barge_out + barge_back,
        }
        segments.append(
            TransportSegment(
                name=str(ws.cell(outbound_row, 2).value),
                total_distance_miles=sum(distances.values()),
                transported_weight_kg_per_kg_feedstock=_num(ws.cell(weight_row, 3).value),
                hazardous=_yes(ws.cell(hazard_row, 3).value),
                packaging_rule=packaging_rule,
                workbook_row=weight_row,
                rail_outbound_miles=rail_out,
                rail_backhaul_miles=rail_back,
                heavy_truck_outbound_miles=heavy_out,
                heavy_truck_backhaul_miles=heavy_back,
                medium_truck_outbound_miles=medium_out,
                medium_truck_backhaul_miles=medium_back,
                ocean_tanker_outbound_miles=ocean_out,
                ocean_tanker_backhaul_miles=ocean_back,
                barge_outbound_miles=barge_out,
                barge_backhaul_miles=barge_back,
                **distances,
            )
        )
    return segments


def scenario_transport_segments(scenario: Scenario) -> list[TransportSegment]:
    default_segments = default_transport_segments()
    distances = [
        scenario.transport_distances.collection_to_disassembly,
        scenario.transport_distances.disassembly_to_preprocessor,
        scenario.transport_distances.preprocessor_to_cm_recovery,
        scenario.transport_distances.manufacturer_to_preprocessor_or_cm_recovery,
        scenario.transport_distances.recycler_to_cathode_producer,
        scenario.transport_distances.cathode_producer_to_manufacturer,
    ]
    weights = _scenario_transport_weights(scenario)

    segments = []
    for index, (template, distance, weight) in enumerate(zip(default_segments, distances, weights, strict=True)):
        rail = 0.0
        heavy = distance if distance > 100 else 0.0
        medium = distance if distance <= 100 else 0.0
        if index == 0 and scenario.battery_collected == "Cell":
            rail = heavy = medium = 0.0
            distance = 0.0
        segments.append(
            TransportSegment(
                name=template.name,
                total_distance_miles=rail + heavy + medium,
                rail_miles=rail,
                heavy_truck_miles=heavy,
                medium_truck_miles=medium,
                ocean_tanker_miles=0.0,
                barge_miles=0.0,
                transported_weight_kg_per_kg_feedstock=weight,
                hazardous=template.hazardous,
                packaging_rule=template.packaging_rule,
                workbook_row=template.workbook_row,
                heavy_truck_outbound_miles=heavy,
                medium_truck_outbound_miles=medium,
            )
        )
    return segments


def _scenario_transport_weights(scenario: Scenario) -> list[float]:
    total = sum(item.tonnes_per_year for item in scenario.feedstocks)
    if total <= 0:
        return [0.0] * 6

    battery = sum(
        item.tonnes_per_year
        for item in scenario.feedstocks
        if "battery" in item.feedstock_type.casefold()
    )
    black_mass = sum(
        item.tonnes_per_year
        for item in scenario.feedstocks
        if "black mass" in item.feedstock_type.casefold()
    )
    scrap = sum(
        item.tonnes_per_year
        for item in scenario.feedstocks
        if "scrap" in item.feedstock_type.casefold()
    )

    default = default_transport_segments()
    collection_to_disassembly = battery / total * 1.1
    recovered_to_cathode = default[4].transported_weight_kg_per_kg_feedstock
    cathode_to_manufacturer = default[5].transported_weight_kg_per_kg_feedstock

    return [
        collection_to_disassembly if scenario.battery_collected != "Cell" else 0.0,
        battery / total * 1.1,
        black_mass / total * 1.1,
        scrap / total * 1.1,
        recovered_to_cathode,
        cathode_to_manufacturer,
    ]


def _segment_row(index: int) -> tuple[int, int]:
    outbound = 20 + index * 2
    return outbound, outbound + 1


def _linehaul_cost(segment: TransportSegment, rates: TransportRates) -> float:
    heavy_rate = rates.heavy_truck_haz_per_mile if segment.hazardous else rates.heavy_truck_nonhaz_per_mile
    medium_rate = rates.medium_truck_haz_per_mile if segment.hazardous else rates.medium_truck_nonhaz_per_mile
    return (
        segment.rail_miles * rates.rail_per_ton_mile
        + segment.heavy_truck_miles * heavy_rate / rates.heavy_payload_ton
        + segment.medium_truck_miles * medium_rate / rates.medium_payload_ton
        + segment.ocean_tanker_miles * rates.ocean_tanker_per_ton_mile
        + segment.barge_miles * rates.barge_per_ton_mile
    )


def _packaging_cost(
    segment: TransportSegment,
    segments: list[TransportSegment],
    rates: TransportRates,
) -> float:
    if segment.total_distance_miles == 0:
        return 0.0

    packaging = rates.packaging_haz_per_kg if segment.hazardous else rates.packaging_nonhaz_per_kg
    first = segments[0]
    second = segments[1]

    if segment.packaging_rule == "first_leg":
        return packaging * segment.transported_weight_kg_per_kg_feedstock / 1.1
    if segment.packaging_rule == "after_first_haz":
        if first.total_distance_miles != 0 and first.hazardous:
            return 0.0
        return packaging * segment.transported_weight_kg_per_kg_feedstock / 1.1
    if segment.packaging_rule == "black_mass":
        if first.total_distance_miles != 0 and first.hazardous and (
            second.total_distance_miles == 0 or segment.total_distance_miles == 0
        ):
            return 0.0
        return packaging
    if segment.packaging_rule == "always_if_distance":
        return packaging * segment.transported_weight_kg_per_kg_feedstock
    return 0.0


def transport_cost_breakdown(
    segments: list[TransportSegment] | None = None,
    rates: TransportRates | None = None,
) -> pd.DataFrame:
    rates = rates or default_transport_rates()
    segments = segments or default_transport_segments()

    rows = []
    for segment in segments:
        linehaul = _linehaul_cost(segment, rates)
        packaging = _packaging_cost(segment, segments, rates)
        cost = linehaul * segment.transported_weight_kg_per_kg_feedstock * KG_TO_SHORT_TON + packaging
        workbook_cost = workbook_number("Col&Trans Par.", f"C{segment.workbook_row + 9}")
        rows.append(
            {
                TransportColumns.SEGMENT: segment.name,
                "hazardous": segment.hazardous,
                TransportColumns.DISTANCE_MILES: segment.total_distance_miles,
                TransportColumns.TRANSPORTED_WEIGHT: segment.transported_weight_kg_per_kg_feedstock,
                TransportColumns.LINEHAUL_COST: linehaul,
                TransportColumns.PACKAGING_COST: packaging,
                TransportColumns.CALCULATED_COST: cost,
                TransportColumns.WORKBOOK_COST: workbook_cost,
                "delta": cost - workbook_cost,
            }
        )

    return pd.DataFrame(rows)


def transport_total_cost() -> float:
    return float(transport_cost_breakdown()[TransportColumns.CALCULATED_COST].sum())


def _greet(row: int, col: int) -> float:
    ws = workbook_sheet("GREET IO")
    return _num(ws.cell(row, col).value)


def _truck_rail_direct(segment: TransportSegment, index: int, rates: TransportRates) -> float:
    rail_out = segment.rail_outbound_miles
    rail_back = segment.rail_backhaul_miles
    heavy_out = segment.heavy_truck_outbound_miles
    heavy_back = segment.heavy_truck_backhaul_miles
    medium_out = segment.medium_truck_outbound_miles
    medium_back = segment.medium_truck_backhaul_miles
    return (
        _greet(125, 4) * rail_out
        + _greet(126, 4) * rail_back
        + _greet(125, 2) / rates.heavy_payload_ton * heavy_out
        + _greet(126, 2) / rates.heavy_payload_ton * heavy_back
        + _greet(125, 3) / rates.medium_payload_ton * medium_out
        + _greet(126, 3) / rates.medium_payload_ton * medium_back
    )


def _water_direct(segment: TransportSegment) -> float:
    ocean_out = segment.ocean_tanker_outbound_miles
    ocean_back = segment.ocean_tanker_backhaul_miles
    barge_out = segment.barge_outbound_miles
    barge_back = segment.barge_backhaul_miles
    return (
        _greet(125, 5) * ocean_out
        + _greet(126, 5) * ocean_back
        + _greet(125, 6) * barge_out
        + _greet(126, 6) * barge_back
    )


def _scale(segment: TransportSegment) -> float:
    return segment.transported_weight_kg_per_kg_feedstock * KG_TO_SHORT_TON


def _metric_energy_value(segment: TransportSegment, index: int, metric_row: int, mode: str, rates: TransportRates) -> float:
    truck_rail = _truck_rail_direct(segment, index, rates)
    water = _water_direct(segment)
    factor_truck_rail = _greet(metric_row, 2)
    factor_water = _greet(metric_row, 3)

    if mode == "upstream":
        value = truck_rail * (1 + factor_truck_rail) + water * (1 + factor_water)
    elif mode == "factor":
        value = truck_rail * factor_truck_rail + water * factor_water
    elif mode == "water":
        value = truck_rail / 1_000_000 * factor_truck_rail + water / 1_000_000 * factor_water
        return value * _scale(segment)
    else:
        raise ValueError(f"Unknown metric mode: {mode}")

    return value / 1_000_000 * _scale(segment)


def _metric_emission_value(
    segment: TransportSegment,
    index: int,
    direct_row: int,
    upstream_row: int,
    rates: TransportRates,
) -> float:
    rail_out = segment.rail_outbound_miles
    rail_back = segment.rail_backhaul_miles
    heavy_out = segment.heavy_truck_outbound_miles
    heavy_back = segment.heavy_truck_backhaul_miles
    medium_out = segment.medium_truck_outbound_miles
    medium_back = segment.medium_truck_backhaul_miles
    ocean_out = segment.ocean_tanker_outbound_miles
    ocean_back = segment.ocean_tanker_backhaul_miles
    barge_out = segment.barge_outbound_miles
    barge_back = segment.barge_backhaul_miles

    upstream_truck_rail = _greet(upstream_row, 2)
    upstream_water = _greet(upstream_row, 3)

    value = (
        _greet(125, 4) * rail_out * (_greet(direct_row, 6) + upstream_truck_rail)
        + _greet(126, 4) * rail_back * (_greet(direct_row, 7) + upstream_truck_rail)
        + _greet(125, 2) / rates.heavy_payload_ton * heavy_out * (_greet(direct_row, 2) + upstream_truck_rail)
        + _greet(126, 2) / rates.heavy_payload_ton * heavy_back * (_greet(direct_row, 3) + upstream_truck_rail)
        + _greet(125, 3) / rates.medium_payload_ton * medium_out * (_greet(direct_row, 4) + upstream_truck_rail)
        + _greet(126, 3) / rates.medium_payload_ton * medium_back * (_greet(direct_row, 5) + upstream_truck_rail)
        + _greet(125, 5) * ocean_out * (_greet(direct_row, 8) + upstream_water)
        + _greet(126, 5) * ocean_back * (_greet(direct_row, 9) + upstream_water)
        + _greet(125, 6) * barge_out * (_greet(direct_row, 10) + upstream_water)
        + _greet(126, 6) * barge_back * (_greet(direct_row, 11) + upstream_water)
    )
    return value / 1_000_000 * _scale(segment)


def transport_environment_breakdown(
    segments: list[TransportSegment] | None = None,
    rates: TransportRates | None = None,
) -> pd.DataFrame:
    rates = rates or default_transport_rates()
    segments = segments or default_transport_segments()
    ws = workbook_sheet("Col&Trans Par.")

    records = []
    for metric, workbook_row, factor_row, mode in ENERGY_METRICS:
        values = [
            _metric_energy_value(segment, index, factor_row, mode, rates)
            for index, segment in enumerate(segments)
        ]
        records.append(_environment_record(metric, workbook_row, values, ws))

    emissions_by_metric = {}
    for metric, workbook_row, direct_row, upstream_row in EMISSION_METRICS:
        values = [
            _metric_emission_value(segment, index, direct_row, upstream_row, rates)
            for index, segment in enumerate(segments)
        ]
        emissions_by_metric[metric] = values
        records.append(_environment_record(metric, workbook_row, values, ws))

    co2_with_carbon = [
        co2
        + voc * _greet(118, 2) / _greet(120, 2)
        + co * _greet(119, 2) / _greet(120, 2)
        for co2, voc, co in zip(
            emissions_by_metric["CO2"],
            emissions_by_metric["VOC"],
            emissions_by_metric["CO"],
            strict=True,
        )
    ]
    records.append(_environment_record("CO2 (w/ C in VOC & CO)", 99, co2_with_carbon, ws))

    ghgs = [
        co2 + ch4 * _greet(114, 2) + n2o * _greet(115, 2)
        for co2, ch4, n2o in zip(
            co2_with_carbon,
            emissions_by_metric["CH4"],
            emissions_by_metric["N2O"],
            strict=True,
        )
    ]
    records.append(_environment_record("GHGs", 100, ghgs, ws))

    return pd.DataFrame(records)


def _environment_record(metric: str, workbook_row: int, values: list[float], ws) -> dict:
    record = {CommonColumns.METRIC: metric, "workbook_row": workbook_row}
    for idx, value in enumerate(values, start=1):
        record[f"segment_{idx}"] = value
        record[f"workbook_segment_{idx}"] = _num(ws.cell(workbook_row, idx + 2).value)
    record[TransportColumns.CALCULATED_TOTAL] = sum(values)
    record[TransportColumns.WORKBOOK_TOTAL] = _num(ws.cell(workbook_row, 9).value)
    record["delta"] = record[TransportColumns.CALCULATED_TOTAL] - record[TransportColumns.WORKBOOK_TOTAL]
    return record
