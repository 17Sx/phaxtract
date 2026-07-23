"""Render synthetic 'état des ventes' gold PDFs from a validated Statement."""

from __future__ import annotations

import json
from pathlib import Path

import fitz  # type: ignore[import-untyped]  # PyMuPDF ships no type stubs

from phaxtract.config.loader import load_lgo_config, load_month_abbreviations
from phaxtract.schema import Statement


def month_column_label(month: str) -> str:
    """Return a French column label such as 'janv. 2026' for a 'YYYY-MM' code.

    The abbreviation is drawn from ``month_abbreviations.json`` (never hard-coded):
    among tokens mapping to the month, the longest one of at most four characters
    wins, so labels round-trip through :func:`phaxtract.normalize.normalize_month`.
    """
    year, num = month.split("-")
    best_token = ""
    best_key: tuple[bool, int, str] = (False, -1, "")
    for token, number in load_month_abbreviations().items():
        if number != num:
            continue
        key = (len(token) <= 4, len(token), token)
        if key > best_key:
            best_key, best_token = key, token
    if not best_token:
        msg = f"No abbreviation configured for month {month!r}"
        raise ValueError(msg)
    return f"{best_token}. {year}"


_PAGE_W = 595.0  # A4 width in points
_PAGE_H = 842.0  # A4 height in points
_MARGIN = 40.0
_ROW_H = 22.0
_FONT = "helv"  # PyMuPDF base-14 Helvetica (covers Latin-1 accents)

_FIXED_HEADERS = ["Code EAN", "Désignation", "PA cat", "PA cat net", "PV TTC"]
_FIXED_WEIGHTS = [2.0, 4.0, 1.5, 1.5, 1.5]


def _lgo_signature(lgo_id: str) -> str:
    """First configured signature string for an LGO id, or the id as fallback."""
    for lgo in load_lgo_config().lgos:
        if lgo.id == lgo_id:
            return lgo.signatures[0]
    return lgo_id


def _fr_decimal(value: float | None) -> str:
    """Format a number the French way: '1 234,56'. Empty string for None."""
    if value is None:
        return ""
    return f"{value:,.2f}".replace(",", " ").replace(".", ",")


def _qty(value: float) -> str:
    """Render a quantity as an integer when whole, else as a plain number."""
    number = float(value)
    return str(int(number)) if number.is_integer() else str(number)


def _draw_document_header(page: fitz.Page, stmt: Statement) -> float:
    """Draw the LGO title + pharmacy/supplier block; return the y below it."""
    y = _MARGIN
    page.insert_text((_MARGIN, y), _lgo_signature(stmt.document.lgo), fontname=_FONT, fontsize=16)
    y += _ROW_H
    pharmacy = stmt.document.pharmacy
    for line_text in [
        pharmacy.name,
        pharmacy.address,
        f"ID: {pharmacy.id}",
        f"Fournisseur: {stmt.document.supplier}",
    ]:
        page.insert_text((_MARGIN, y), line_text, fontname=_FONT, fontsize=9)
        y += 14
    return y


def render_statement_pdf(stmt: Statement, out_path: Path) -> Path:
    """Render a synthetic gold PDF for a validated Statement (monthly layout).

    Writes ``out_path`` and returns it. Performs no JSON I/O — callers pass an
    already-validated :class:`~phaxtract.schema.Statement`.
    """
    return _render_monthly_pdf(stmt, out_path)


def _render_monthly_pdf(stmt: Statement, out_path: Path) -> Path:
    """Render a monthly product-by-month grid.

    The printed TOTAL row equals the per-month sum of line quantities, so
    reconciliation passes.
    """
    doc = fitz.open()
    page = doc.new_page(width=_PAGE_W, height=_PAGE_H)
    y = _draw_document_header(page, stmt)

    months = stmt.document.months
    headers = _FIXED_HEADERS + [month_column_label(m) for m in months]
    weights = _FIXED_WEIGHTS + [1.5] * len(months)
    x_left = _MARGIN
    x_right = _PAGE_W - _MARGIN
    span = x_right - x_left
    total_weight = sum(weights)
    xs = [x_left]
    for weight in weights:
        xs.append(xs[-1] + span * weight / total_weight)

    def draw_row(cells: list[str], top: float) -> None:
        for index, text in enumerate(cells):
            page.insert_text((xs[index] + 2, top + 15), text, fontname=_FONT, fontsize=8)

    table_top = y + 6
    row_tops = [table_top]
    draw_row(headers, table_top)

    current_top = table_top + _ROW_H
    for line in stmt.lines:
        cells = [
            line.code_produit,
            line.designation,
            _fr_decimal(line.prices.pa_cat),
            _fr_decimal(line.prices.pa_cat_net),
            _fr_decimal(line.prices.pv_ttc),
        ] + [_qty(line.quantities.get(month, 0)) for month in months]
        draw_row(cells, current_top)
        row_tops.append(current_top)
        current_top += _ROW_H

    totals = {
        month: sum(float(line.quantities.get(month, 0)) for line in stmt.lines)
        for month in months
    }
    total_cells = ["", "TOTAL", "", "", ""] + [_qty(totals[m]) for m in months]
    draw_row(total_cells, current_top)
    row_tops.append(current_top)
    current_top += _ROW_H
    row_tops.append(current_top)

    for row_top in row_tops:
        page.draw_line((x_left, row_top), (x_right, row_top))
    for column_x in xs:
        page.draw_line((column_x, table_top), (column_x, current_top))

    return _save(doc, out_path)


def _save(doc: fitz.Document, out_path: Path) -> Path:
    """Set reproducible metadata, write the PDF, and return its path."""
    doc.set_metadata(
        {"title": out_path.stem, "producer": "phaxtract.synth", "creationDate": "", "modDate": ""}
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(out_path))
    doc.close()
    return out_path


def render_expected_file(expected_path: Path, out_dir: Path) -> Path:
    """Render the PDF for one ``*.expected.json`` gold fixture.

    The output filename drops the ``.expected`` suffix:
    ``monthly_etat_des_ventes.expected.json`` -> ``monthly_etat_des_ventes.pdf``.
    """
    stmt = Statement.model_validate(json.loads(expected_path.read_text(encoding="utf-8")))
    stem = expected_path.name.removesuffix(".expected.json")
    return render_statement_pdf(stmt, out_dir / f"{stem}.pdf")
