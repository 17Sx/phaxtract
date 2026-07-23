"""Tests for PDF text-layer detection."""

from __future__ import annotations

from pathlib import Path

import fitz  # type: ignore[import-untyped]


def _text_pdf(path: Path, text: str) -> Path:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), text, fontsize=12)
    doc.save(str(path))
    doc.close()
    return path


def _blank_pdf(path: Path) -> Path:
    doc = fitz.open()
    doc.new_page()
    doc.save(str(path))
    doc.close()
    return path


def test_has_text_layer_true_for_text_pdf(tmp_path: Path) -> None:
    from phaxtract.ingest import has_text_layer

    assert has_text_layer(_text_pdf(tmp_path / "t.pdf", "Ceci est un relevé de ventes")) is True


def test_has_text_layer_false_for_blank_pdf(tmp_path: Path) -> None:
    from phaxtract.ingest import has_text_layer

    assert has_text_layer(_blank_pdf(tmp_path / "b.pdf")) is False
