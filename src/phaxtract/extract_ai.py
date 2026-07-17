"""NuExtract photo/scan extraction path: image -> Statement.

This module has two layers:

* the **pure mapping** :func:`nuextract_to_statement` (raw NuExtract JSON ->
  :class:`~phaxtract.schema.Statement`) has no GPU/torch dependency and is
  unit-tested;
* the **heavy inference** (loading NuExtract 3 and running it on an image) lives
  behind the optional ``[ai]`` extra and is added later — it is not imported at
  module load, so importing this module never pulls in torch.
"""

from __future__ import annotations

import re
from datetime import date
from typing import Any

from phaxtract.schema import (
    DocumentMeta,
    Line,
    Pharmacy,
    Statement,
    ValidationResult,
)

_EAN_RE = re.compile(r"^\d{13}$")
_MONTH_RE = re.compile(r"^\d{4}-\d{2}$")


def _text(value: Any) -> str:
    return "" if value is None else str(value)


def _report_date(value: Any) -> date | None:
    text = _text(value)[:10]
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def _line_quantities(sales: Any) -> dict[str, int | float]:
    quantities: dict[str, int | float] = {}
    if not isinstance(sales, list):
        return quantities
    for sale in sales:
        if not isinstance(sale, dict):
            continue
        month = _text(sale.get("month"))[:7]
        if not _MONTH_RE.match(month):
            continue
        try:
            qty = int(float(_text(sale.get("quantity"))))
        except ValueError:
            continue
        quantities[month] = quantities.get(month, 0) + qty
    return quantities


def nuextract_to_statement(raw: dict[str, Any], source_file: str) -> Statement:
    """Map a filled NuExtract template (raw JSON) to a canonical Statement.

    Products whose code does not normalize to a 13-digit EAN/CIP-13 are skipped.
    Defensive against missing keys and wrong types in the model output.
    """
    products = raw.get("products")
    lines: list[Line] = []
    if isinstance(products, list):
        for product in products:
            if not isinstance(product, dict):
                continue
            code = re.sub(r"\D", "", _text(product.get("code_produit")))
            if not _EAN_RE.match(code):
                continue
            lines.append(
                Line(
                    code_produit=code,
                    designation=_text(product.get("designation")),
                    quantities=_line_quantities(product.get("sales")),
                )
            )

    pharmacy_raw = raw.get("pharmacy")
    pharmacy_raw = pharmacy_raw if isinstance(pharmacy_raw, dict) else {}
    months = sorted({month for line in lines for month in line.quantities})
    document = DocumentMeta(
        source_file=source_file,
        lgo="",
        statement_type="monthly",
        pharmacy=Pharmacy(
            name=_text(pharmacy_raw.get("name")),
            id=_text(pharmacy_raw.get("id")),
        ),
        supplier=_text(raw.get("supplier")),
        months=months,
        generated_at=_report_date(raw.get("report_date")),
    )
    return Statement(
        document=document,
        lines=lines,
        validation=ValidationResult(row_count=len(lines)),
    )
