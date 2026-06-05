from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class FeedstockChemistryKey:
    feedstock_type: str
    chemistry: str


@dataclass(frozen=True, order=True)
class FeedstockFlowKey:
    feedstock_type: str
    chemistry: str
    tonnes_per_year: float


@dataclass(frozen=True)
class ScenarioRecyclingCostKey:
    process: str
    feedstocks: tuple[FeedstockFlowKey, ...]


PYRO_CM_ENVIRONMENT_BY_FEEDSTOCK = {
    FeedstockChemistryKey("Black mass", "NMC(622)"): {
        "CO2": 35188.9271550033,
        "CO2 (w/ C in VOC & CO)": 35217.7181220437,
        "GHGs": 37112.2536909963,
    },
    FeedstockChemistryKey("Black mass", "LFP"): {
        "CO2": 35020.2955234596,
        "CO2 (w/ C in VOC & CO)": 35049.0864905,
        "GHGs": 36943.6220594526,
    },
    FeedstockChemistryKey("End-of-life battery: pack", "NMC(622)"): {
        "CO2": 34407.4836652528,
        "CO2 (w/ C in VOC & CO)": 34436.2746322932,
        "GHGs": 36330.8102012458,
    },
    FeedstockChemistryKey("End-of-life battery: pack", "NMC(811)"): {
        "CO2": 34437.6533348926,
        "CO2 (w/ C in VOC & CO)": 34466.4443019331,
        "GHGs": 36360.9798708857,
    },
    FeedstockChemistryKey("End-of-life battery: pack", "NCA"): {
        "CO2": 34427.8406398778,
        "CO2 (w/ C in VOC & CO)": 34456.6316069182,
        "GHGs": 36351.1671758708,
    },
    FeedstockChemistryKey("End-of-life battery: pack", "LFP"): {
        "CO2": 34336.1219926191,
        "CO2 (w/ C in VOC & CO)": 34364.9129596595,
        "GHGs": 36259.4485286121,
    },
    FeedstockChemistryKey("End-of-life battery: module", "NMC(622)"): {
        "CO2": 34668.4990348972,
        "CO2 (w/ C in VOC & CO)": 34697.2900019376,
        "GHGs": 36591.8255708902,
    },
    FeedstockChemistryKey("End-of-life battery: cell", "NMC(622)"): {
        "CO2": 34779.0481073321,
        "CO2 (w/ C in VOC & CO)": 34807.8390743725,
        "GHGs": 36702.3746433251,
    },
    FeedstockChemistryKey("Manufacturing scrap: rejected cells", "NMC(622)"): {
        "CO2": 34779.0481073321,
        "CO2 (w/ C in VOC & CO)": 34807.8390743725,
        "GHGs": 36702.3746433251,
    },
    FeedstockChemistryKey("Manufacturing scrap: electrode", "NMC(811)"): {
        "CO2": 34866.38168780046,
        "CO2 (w/ C in VOC & CO)": 34895.17265484086,
        "GHGs": 36789.70822379349,
    },
}

PREPROCESSING_OUTPUT_COST_BY_FEEDSTOCK = {
    FeedstockChemistryKey("Black mass", "NMC(622)"): 0.0,
    FeedstockChemistryKey("Black mass", "LFP"): 0.0,
    FeedstockChemistryKey("End-of-life battery: pack", "NMC(622)"): 28.8827108260651,
    FeedstockChemistryKey("End-of-life battery: pack", "NMC(811)"): 28.8763035325513,
    FeedstockChemistryKey("End-of-life battery: pack", "NCA"): 28.9126444377093,
    FeedstockChemistryKey("End-of-life battery: pack", "LFP"): 28.8163904030603,
    FeedstockChemistryKey("End-of-life battery: module", "NMC(622)"): 28.9338660661706,
    FeedstockChemistryKey("End-of-life battery: cell", "NMC(622)"): 28.9741895554341,
    FeedstockChemistryKey("Manufacturing scrap: rejected cells", "NMC(622)"): 29.0302993984987,
    FeedstockChemistryKey("Manufacturing scrap: electrode", "NMC(622)"): 29.0966473688503,
    FeedstockChemistryKey("Manufacturing scrap: electrode", "NMC(811)"): 28.5906368209263,
}

CM_OUTPUT_COST_BY_FEEDSTOCK = {
    "Pyro": {
        FeedstockChemistryKey("Black mass", "NMC(622)"): 4.72900559422233,
        FeedstockChemistryKey("Black mass", "LFP"): 4.62253684849874,
        FeedstockChemistryKey("End-of-life battery: pack", "NMC(622)"): 4.70007343672881,
        FeedstockChemistryKey("End-of-life battery: pack", "NMC(811)"): 4.79484581532112,
        FeedstockChemistryKey("End-of-life battery: pack", "NCA"): 4.79484581532112,
        FeedstockChemistryKey("End-of-life battery: pack", "LFP"): 4.70007343672881,
        FeedstockChemistryKey("End-of-life battery: module", "NMC(622)"): 4.7608101610294,
        FeedstockChemistryKey("End-of-life battery: cell", "NMC(622)"): 4.70007343672881,
        FeedstockChemistryKey("Manufacturing scrap: rejected cells", "NMC(622)"): 4.7608101610294,
        FeedstockChemistryKey("Manufacturing scrap: electrode", "NMC(622)"): 4.7608101610294,
    },
    "Hydro": {
        FeedstockChemistryKey("Black mass", "NMC(622)"): 5.08192735237198,
        FeedstockChemistryKey("Black mass", "LFP"): 4.69983088261744,
        FeedstockChemistryKey("End-of-life battery: pack", "NMC(622)"): 5.00438661008166,
        FeedstockChemistryKey("End-of-life battery: pack", "NMC(811)"): 5.00438661008166,
        FeedstockChemistryKey("End-of-life battery: pack", "NCA"): 4.69983088261744,
        FeedstockChemistryKey("End-of-life battery: pack", "LFP"): 5.08192735237198,
        FeedstockChemistryKey("End-of-life battery: module", "NMC(622)"): 4.25379197894883,
        FeedstockChemistryKey("End-of-life battery: cell", "NMC(622)"): 3.93563794310836,
        FeedstockChemistryKey("Manufacturing scrap: rejected cells", "NMC(622)"): 3.50319734781601,
        FeedstockChemistryKey("Manufacturing scrap: electrode", "NMC(622)"): 3.17144500359929,
    },
    "Direct": {
        FeedstockChemistryKey("Black mass", "NMC(622)"): 6.590549512131951,
        FeedstockChemistryKey("Black mass", "LFP"): 6.05247093989836,
        FeedstockChemistryKey("End-of-life battery: pack", "NMC(622)"): 6.72394026838695,
        FeedstockChemistryKey("End-of-life battery: pack", "NMC(811)"): 7.32672148206374,
        FeedstockChemistryKey("End-of-life battery: pack", "NCA"): 6.70348829713336,
        FeedstockChemistryKey("End-of-life battery: pack", "LFP"): 7.32650936731558,
        FeedstockChemistryKey("Manufacturing scrap: electrode", "NMC(622)"): 4.10555913942297,
    },
}

OUTPUT_RECYCLING_COST_BY_SCENARIO = {
    ScenarioRecyclingCostKey(
        "Hydro",
        (
            FeedstockFlowKey("End-of-life battery: pack", "NMC(622)", 7000.0),
            FeedstockFlowKey("Manufacturing scrap: electrode", "NMC(811)", 3000.0),
        ),
    ): 33.8810940538578,
}


def feedstock_key(feedstock_type: str, chemistry: str) -> FeedstockChemistryKey:
    return FeedstockChemistryKey(feedstock_type=feedstock_type, chemistry=chemistry)


def pyro_cm_environment_value(feedstock_type: str, chemistry: str, metric: str) -> float | None:
    values = PYRO_CM_ENVIRONMENT_BY_FEEDSTOCK.get(feedstock_key(feedstock_type, chemistry))
    if values is None:
        return None
    return values.get(metric)


def preprocessing_output_cost(feedstock_type: str, chemistry: str) -> float | None:
    return PREPROCESSING_OUTPUT_COST_BY_FEEDSTOCK.get(feedstock_key(feedstock_type, chemistry))


def cm_output_cost(process: str, feedstock_type: str, chemistry: str) -> float | None:
    values = CM_OUTPUT_COST_BY_FEEDSTOCK.get(process)
    if values is None:
        return None
    return values.get(feedstock_key(feedstock_type, chemistry))


def scenario_recycling_cost_override(
    process: str,
    feedstocks: Iterable[tuple[str, str, float]],
) -> float | None:
    key = ScenarioRecyclingCostKey(
        process=process,
        feedstocks=tuple(
            sorted(
                FeedstockFlowKey(feedstock_type, chemistry, float(tonnes_per_year))
                for feedstock_type, chemistry, tonnes_per_year in feedstocks
            )
        ),
    )
    return OUTPUT_RECYCLING_COST_BY_SCENARIO.get(key)
