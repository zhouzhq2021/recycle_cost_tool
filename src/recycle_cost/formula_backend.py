from __future__ import annotations

from dataclasses import dataclass
from functools import cached_property

import formulas

from .workbook import make_openpyxl_readable_copy


@dataclass
class FormulaWorkbook:
    """Experimental formulas-based backend for offline workbook calculations.

    This is intentionally not used by the Streamlit app yet. The EverBatt workbook
    creates a large formula graph, so individual output calculation needs more
    validation before becoming an interactive backend.
    """

    @cached_property
    def model(self):
        readable = make_openpyxl_readable_copy()
        return formulas.ExcelModel().loads(str(readable)).finish()

    @cached_property
    def book_name(self) -> str:
        return next(iter(self.model.books)).lower()

    def cell_key(self, sheet: str, cell: str) -> str:
        return f"'[{self.book_name}]{sheet.upper()}'!{cell.upper()}"

    def output_keys(self, sheet: str = "Output") -> list[str]:
        token = f"]{sheet.upper()}'!"
        return sorted(key for key in self.model.dsp.data_nodes if token in key)

