"""Native PDF extraction path: pdfplumber tables -> canonical Statement.

Mirrors :mod:`phaxtract.extract_ai`: the **pure mapping** here
(:func:`native_to_statement` and the ``assemble_*`` helpers) is unit-tested with
hand-built tables and imports no PDF library; the **orchestrator**
:func:`extract_statement_from_pdf` wires pdfplumber to it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from phaxtract.fingerprint import identify_lgo
from phaxtract.normalize import normalize_column, normalize_month, parse_french_decimal
from phaxtract.schema import DocumentMeta, Line, Pharmacy, Prices, Statement, ValidationResult
from phaxtract.validate import reconcile_quantities

_EAN_RE = re.compile(r"^\d{13}$")
_MONTH_RE = re.compile(r"^\d{4}-\d{2}$")
_YEAR_RE = re.compile(r"20\d{2}")
_FIXED_COLUMNS = frozenset({"code_produit", "designation", "pa_cat", "pa_cat_net", "pv_ttc"})


@dataclass
class RawPage:
    """One PDF page's extracted content: its tables and its full text."""

    tables: list[list[list[str | None]]] = field(default_factory=list)
    text: str = ""


def _cell(value: str | None) -> str:
    return "" if value is None else str(value).strip()


def _at(row: list[str], index: int | None) -> str:
    if index is None or index >= len(row):
        return ""
    return row[index]


def _parse_int(text: str) -> int | float | None:
    text = text.strip()
    if not text:
        return None
    try:
        number = float(text.replace(" ", "").replace(",", "."))
    except ValueError:
        return None
    return int(number) if number.is_integer() else number


def _parse_dec(text: str) -> float | None:
    if not text.strip():
        return None
    try:
        return parse_french_decimal(text)
    except ValueError:
        return None


def _reference_year(text: str) -> int:
    years = _YEAR_RE.findall(text)
    return max(int(year) for year in years) if years else 2000


def detect_statement_type(header: list[str]) -> str:
    """Return ``"period"`` when the header has a date column, else ``"monthly"``."""
    if any(normalize_column(cell) == "date" for cell in header):
        return "period"
    return "monthly"


def assemble_monthly(
    header: list[str],
    rows: list[list[str]],
    *,
    reference_year: int,
) -> tuple[list[Line], dict[str, int | float]]:
    """Assemble monthly grid rows into Lines plus the printed per-month totals.

    Fixed columns are classified by :func:`normalize_column`; every other header
    that parses as a month becomes a month column. A row whose code column is not
    an EAN-13 but that carries month quantities is treated as the printed TOTAL row.
    """
    fixed: dict[str, int] = {}
    months: dict[int, str] = {}
    for index, cell in enumerate(header):
        canonical = normalize_column(cell)
        if canonical in _FIXED_COLUMNS:
            fixed[canonical] = index
            continue
        try:
            months[index] = normalize_month(cell, reference_year)
        except ValueError:
            continue

    lines: list[Line] = []
    printed_totals: dict[str, int | float] = {}
    for row in rows:
        quantities: dict[str, int | float] = {}
        for index, month in months.items():
            value = _parse_int(_at(row, index))
            if value is not None:
                quantities[month] = value
        code = re.sub(r"\D", "", _at(row, fixed.get("code_produit")))
        if _EAN_RE.match(code):
            lines.append(
                Line(
                    code_produit=code,
                    designation=_at(row, fixed.get("designation")),
                    prices=Prices(
                        pa_cat=_parse_dec(_at(row, fixed.get("pa_cat"))),
                        pa_cat_net=_parse_dec(_at(row, fixed.get("pa_cat_net"))),
                        pv_ttc=_parse_dec(_at(row, fixed.get("pv_ttc"))),
                    ),
                    quantities=quantities,
                )
            )
        elif quantities:
            printed_totals = quantities
    return lines, printed_totals


def assemble_period(header: list[str], rows: list[list[str]]) -> list[Line]:
    """Placeholder — implemented in a later task."""
    return []


def native_to_statement(pages: list[RawPage], source_file: str) -> Statement:
    """Map extracted PDF pages to a canonical Statement via the deterministic layer."""
    text = "\n".join(page.text for page in pages)
    tables = [
        [[_cell(cell) for cell in row] for row in table]
        for page in pages
        for table in page.tables
        if table
    ]

    statement_type = "monthly"
    lines: list[Line] = []
    printed_totals: dict[str, int | float] = {}
    if tables:
        statement_type = detect_statement_type(tables[0][0])
        reference_year = _reference_year(text)
        for table in tables:
            header, body = table[0], table[1:]
            if statement_type == "period":
                lines.extend(assemble_period(header, body))
            else:
                table_lines, table_totals = assemble_monthly(
                    header, body, reference_year=reference_year
                )
                lines.extend(table_lines)
                if table_totals:
                    printed_totals = table_totals

    if statement_type == "monthly" and printed_totals:
        validation = reconcile_quantities([line.quantities for line in lines], printed_totals)
    else:
        validation = ValidationResult(row_count=len(lines))

    pharmacy, supplier = _parse_header_meta(text)
    months = sorted({month for line in lines for month in line.quantities}, reverse=True)
    document = DocumentMeta(
        source_file=source_file,
        lgo=identify_lgo(text) or "",
        statement_type="period" if statement_type == "period" else "monthly",
        pharmacy=pharmacy,
        supplier=supplier,
        months=months,
        page_count=max(len(pages), 1),
    )
    return Statement(document=document, lines=lines, validation=validation)


def _parse_header_meta(text: str) -> tuple[Pharmacy, str]:
    """Best-effort pharmacy/supplier recovery from the page text (not benchmarked)."""
    supplier = ""
    pharmacy_id = ""
    body: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        low = line.lower()
        if low.startswith("fournisseur:"):
            supplier = line.split(":", 1)[1].strip()
        elif low.startswith("id:"):
            pharmacy_id = line.split(":", 1)[1].strip()
        else:
            body.append(line)
    name = body[1] if len(body) >= 2 else ""
    address = body[2] if len(body) >= 3 else ""
    return Pharmacy(name=name, address=address, id=pharmacy_id), supplier


def extract_statement_from_pdf(
    path: str | Path,
    *,
    source_file: str | None = None,
) -> Statement:
    """Extract a canonical Statement from a native-text PDF via pdfplumber.

    Opens ``path``, collects each page's tables and text into :class:`RawPage`
    objects, and delegates all normalization/validation to
    :func:`native_to_statement`. pdfplumber is a core dependency, so no optional
    guard is needed (unlike the torch-backed AI path).
    """
    import pdfplumber

    pages: list[RawPage] = []
    with pdfplumber.open(str(path)) as document:
        for page in document.pages:
            pages.append(
                RawPage(tables=page.extract_tables() or [], text=page.extract_text() or "")
            )
    return native_to_statement(pages, source_file or Path(path).name)
