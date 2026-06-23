from __future__ import annotations

from typing import Protocol


CUSTOM_NMC_LABEL = "Custom NMC"
CUSTOM_NMC_BASE = "NMC(622)"
NMC_CATHODE_MATERIALS = ("LCO", "NMC(111)", "NMC(532)", "NMC(622)", "NMC(811)", "NCA", "LMO", "LFP", CUSTOM_NMC_LABEL)


class CustomNMCHost(Protocol):
    custom_nmc_ni: float | None
    custom_nmc_co: float | None
    custom_nmc_mn: float | None
    custom_feedstock_composition: dict[str, float] | None
    custom_feedstock_composition_feedstock_type: str | None


def is_custom_nmc(label: str | None) -> bool:
    return str(label or "").strip() == CUSTOM_NMC_LABEL


def workbook_chemistry(label: str | None) -> str:
    return CUSTOM_NMC_BASE if is_custom_nmc(label) else str(label or CUSTOM_NMC_BASE)


def custom_nmc_ratio(host: CustomNMCHost) -> tuple[float, float, float]:
    ni = _positive(host.custom_nmc_ni, 6.0)
    co = _positive(host.custom_nmc_co, 2.0)
    mn = _positive(host.custom_nmc_mn, 2.0)
    total = ni + co + mn
    if total <= 0:
        return 0.6, 0.2, 0.2
    return ni / total, co / total, mn / total


def custom_nmc_elemental_mass(host: CustomNMCHost) -> dict[str, float]:
    ni, co, mn = custom_nmc_ratio(host)
    values = {
        "Li": 6.94,
        "Co": 58.933 * co,
        "Ni": 58.693 * ni,
        "Mn": 54.938 * mn,
        "O": 31.998,
        "P": 0.0,
        "F": 0.0,
        "Al": 0.0,
        "Fe": 0.0,
    }
    values["Total"] = sum(values.values())
    return values


def custom_feedstock_composition(host: CustomNMCHost) -> dict[str, float]:
    values = getattr(host, "custom_feedstock_composition", None)
    return dict(values) if isinstance(values, dict) else {}


def _positive(value: float | None, fallback: float) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return fallback
    return parsed if parsed > 0 else fallback
