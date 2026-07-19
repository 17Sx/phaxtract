"""NuExtract photo/scan extraction path: image -> Statement.

This module holds the GPU-free glue:

* the **pure mapping** :func:`nuextract_to_statement` (raw NuExtract JSON ->
  :class:`~phaxtract.schema.Statement`) and :func:`parse_nuextract_output`, both
  unit-tested without torch;
* the **orchestrator** :func:`extract_statement_from_image`, which wires an
  :class:`~phaxtract.nuextract_engine.ExtractionEngine` to the mapping.

The **heavy inference** (loading NuExtract 3 and running it on an image) lives in
:mod:`phaxtract.nuextract_engine` behind the optional ``[ai]`` extra and is imported
lazily, so importing this module never pulls in torch.
"""

from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING, Any

from phaxtract.nuextract_template import STATEMENT_TEMPLATE
from phaxtract.schema import (
    DocumentMeta,
    Line,
    Pharmacy,
    Statement,
    ValidationResult,
)

if TYPE_CHECKING:
    from phaxtract.nuextract_engine import ExtractionEngine

_EAN_RE = re.compile(r"^\d{13}$")
_MONTH_RE = re.compile(r"^\d{4}-\d{2}$")
_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)


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


def parse_nuextract_output(text: str) -> dict[str, Any]:
    """Parse a NuExtract raw completion into a JSON object.

    Tolerates Markdown code fences and surrounding prose. Returns an empty dict
    when the text holds no JSON object (never raises), so downstream mapping stays
    defensive.
    """
    candidates = [text]
    fenced = _FENCE_RE.search(text)
    if fenced is not None:
        candidates.insert(0, fenced.group(1))
    start, end = text.find("{"), text.rfind("}")
    if 0 <= start < end:
        candidates.append(text[start : end + 1])

    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
        except (json.JSONDecodeError, ValueError):
            continue
        if isinstance(parsed, dict):
            return parsed
    return {}


def extract_statement_from_image(
    image: str | Path,
    *,
    source_file: str | None = None,
    engine: ExtractionEngine | None = None,
    template: str | None = None,
) -> Statement:
    """Extract a canonical :class:`Statement` from a photo/scan via NuExtract.

    ``engine`` defaults to a lazily-built :class:`~phaxtract.nuextract_engine.NuExtractEngine`
    (importing it here keeps this module torch-free at import time); inject a fake
    engine to exercise the mapping without a model. ``template`` defaults to the
    JSON-serialized :data:`~phaxtract.nuextract_template.STATEMENT_TEMPLATE`.
    """
    if engine is None:
        from phaxtract.nuextract_engine import NuExtractEngine

        engine = NuExtractEngine()
    if template is None:
        template = json.dumps(STATEMENT_TEMPLATE)

    raw = engine.extract(image, template)
    data = parse_nuextract_output(raw)
    return nuextract_to_statement(data, source_file or Path(image).name)
