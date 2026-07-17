"""Convert Google Document AI entity JSON into canonical Statement gold."""

from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path
from typing import Any, NamedTuple

from phaxtract.fingerprint import identify_lgo
from phaxtract.schema import (
    DocumentMeta,
    Line,
    Pharmacy,
    Statement,
    ValidationResult,
)

_EAN_RE = re.compile(r"^\d{13}$")


class SkippedLine(NamedTuple):
    reason: str
    raw_code: str


class ConversionResult(NamedTuple):
    statement: Statement
    skipped: list[SkippedLine]


def _props_by_type(entity: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for prop in entity.get("properties", []):
        grouped.setdefault(prop.get("type", ""), []).append(prop)
    return grouped


def _norm_text(prop: dict[str, Any]) -> str:
    normalized = prop.get("normalizedValue")
    if isinstance(normalized, dict):
        text = normalized.get("text")
        if isinstance(text, str):
            return text
    return str(prop.get("mentionText", ""))


def _first_report_date(entities: list[dict[str, Any]]) -> date | None:
    for entity in entities:
        if entity.get("type") == "report_date":
            text = _norm_text(entity)[:10]
            try:
                return date.fromisoformat(text)
            except ValueError:
                return None
    return None


def _line_quantities(props: dict[str, list[dict[str, Any]]]) -> dict[str, int | float]:
    quantities: dict[str, int | float] = {}
    for sales in props.get("sales_by_month", []):
        sales_props = _props_by_type(sales)
        month_props = sales_props.get("month_period_normalized")
        qty_props = sales_props.get("sales_quantity")
        if not month_props or not qty_props:
            continue
        month = _norm_text(month_props[0])[:7]
        try:
            qty = int(_norm_text(qty_props[0]))
        except ValueError:
            continue
        quantities[month] = quantities.get(month, 0) + qty
    return quantities


def _total_line_quantities(entities: list[dict[str, Any]]) -> dict[str, int | float] | None:
    for entity in entities:
        if entity.get("type") == "total_line":
            return _line_quantities(_props_by_type(entity))
    return None


def _reconcile(lines: list[Line], printed_totals: dict[str, int | float] | None) -> bool:
    if not printed_totals:
        return False
    sums: dict[str, float] = {}
    for line in lines:
        for month, qty in line.quantities.items():
            sums[month] = sums.get(month, 0.0) + float(qty)
    return all(
        sums.get(month, 0.0) == float(expected)
        for month, expected in printed_totals.items()
    )


def docai_to_statement(docai: dict[str, Any], source_file: str) -> ConversionResult:
    """Map one Doc AI entity JSON to a canonical Statement plus a skipped-line report."""
    entities = docai.get("entities", [])
    lines: list[Line] = []
    skipped: list[SkippedLine] = []

    for entity in entities:
        if entity.get("type") != "product_line":
            continue
        props = _props_by_type(entity)
        ean_props = props.get("product_ean")
        raw_code = _norm_text(ean_props[0]) if ean_props else ""
        code = re.sub(r"\D", "", raw_code)
        if not _EAN_RE.match(code):
            skipped.append(SkippedLine(reason="non-13-digit code", raw_code=raw_code))
            continue
        designation_props = props.get("product_designation")
        designation = _norm_text(designation_props[0]) if designation_props else ""
        confidence = entity.get("confidence")
        lines.append(
            Line(
                code_produit=code,
                designation=designation,
                quantities=_line_quantities(props),
                confidence=float(confidence) if confidence is not None else 1.0,
            )
        )

    months = sorted({month for line in lines for month in line.quantities})
    document = DocumentMeta(
        source_file=source_file,
        lgo=identify_lgo(str(docai.get("text", ""))) or "",
        statement_type="monthly",
        pharmacy=Pharmacy(name=""),
        months=months,
        generated_at=_first_report_date(entities),
    )
    reconciled = _reconcile(lines, _total_line_quantities(entities))
    statement = Statement(
        document=document,
        lines=lines,
        validation=ValidationResult(row_count=len(lines), totals_reconciled=reconciled),
    )
    return ConversionResult(statement=statement, skipped=skipped)


def convert_docai_file(json_path: Path, out_dir: Path) -> tuple[Path, ConversionResult]:
    """Convert one Doc AI ``*.json`` and write ``<stem>.expected.json`` into out_dir."""
    docai = json.loads(json_path.read_text(encoding="utf-8"))
    result = docai_to_statement(docai, json_path.name)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{json_path.stem}.expected.json"
    out_path.write_text(
        json.dumps(result.statement.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return out_path, result
