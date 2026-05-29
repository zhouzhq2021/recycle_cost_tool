from __future__ import annotations


class CommonColumns:
    METRIC = "metric"
    ITEM = "item"
    VALUE = "value"
    UNIT = "unit"
    PROCESS = "process"
    CHEMISTRY = "chemistry"
    CATEGORY = "category"
    MATERIAL = "material"
    COMPONENT = "component"
    REVENUE = "revenue"
    COST = "cost"


class OutputSummaryColumns:
    METRIC = CommonColumns.METRIC
    CATEGORY = CommonColumns.CATEGORY
    UNIT = CommonColumns.UNIT
    VIRGIN = "Virgin"
    PYRO = "Pyro"
    HYDRO = "Hydro"
    DIRECT = "Direct"
    CUSTOM = "Custom"

    ROUTES = [VIRGIN, PYRO, HYDRO, DIRECT, CUSTOM]
    ALL = [METRIC, CATEGORY, UNIT, *ROUTES]


class StageSummaryColumns:
    STAGE = "stage"
    BASIS = "basis"
    PROCESS = CommonColumns.PROCESS
    COST = CommonColumns.COST
    TOTAL_ENERGY = "total_energy"
    WATER = "water"
    GHG = "ghg"
    THROUGHPUT_TONNES_PER_YEAR = "throughput_tonnes_per_year"


class AuditColumns:
    ITEM = CommonColumns.ITEM
    PYTHON_VALUE = "python_value"
    WORKBOOK_VALUE = "workbook_value"
    DELTA = "delta"
    STATUS = "status"

    @staticmethod
    def calculated(col: str) -> str:
        return f"calculated_{col}"

    @staticmethod
    def workbook(col: str) -> str:
        return f"workbook_{col}"


class ManufacturingColumns:
    KG_PER_KG_CELL = "kg_per_kg_cell"
    COST_PER_KG_CELL = "cost_per_kg_cell"
    MATERIAL_INPUTS = "material_inputs"
    ENERGY_INPUTS = "energy_inputs"
    TOTAL = "total"
    KG_PER_KG_FEEDSTOCK = "kg_per_kg_feedstock"


class TransportColumns:
    SEGMENT = "segment"
    DISTANCE_MILES = "distance_miles"
    TRANSPORTED_WEIGHT = "transported_weight_kg_per_kg_feedstock"
    LINEHAUL_COST = "linehaul_cost_per_short_ton"
    PACKAGING_COST = "packaging_cost_per_kg_feedstock"
    CALCULATED_COST = "calculated_cost"
    WORKBOOK_COST = "workbook_cost"
    CALCULATED_TOTAL = "calculated_total"
    WORKBOOK_TOTAL = "workbook_total"


class CathodeColumns:
    ANNUAL = "annual"
    PER_KG = "per_kg"

    @staticmethod
    def annual_col(process: str) -> str:
        return f"{process.lower()}_annual"

    @staticmethod
    def per_kg_col(process: str) -> str:
        return f"{process.lower()}_per_kg"
