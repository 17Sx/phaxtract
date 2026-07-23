"""End-to-end extraction dispatcher: pick the path by file type.

This is a plain file-type dispatch (``.pdf`` -> native pdfplumber path; image ->
NuExtract photo path). The smarter text-layer *router* (a native PDF with no
usable text layer falling back to the photo path) is deferred to a later phase;
:func:`phaxtract.ingest.has_text_layer` already provides the discriminant.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from phaxtract.schema import Statement

if TYPE_CHECKING:
    from phaxtract.nuextract_engine import ExtractionEngine

_IMAGE_SUFFIXES = frozenset({".png", ".jpg", ".jpeg", ".tif", ".tiff"})


def extract_statement(path: str | Path, *, engine: ExtractionEngine | None = None) -> Statement:
    """Extract a canonical Statement, choosing the path by the file suffix.

    ``.pdf`` files go through the native pdfplumber path; image files through the
    NuExtract photo path (``engine`` is forwarded there). Raises ``ValueError`` for
    any other suffix.
    """
    suffix = Path(path).suffix.lower()
    if suffix == ".pdf":
        from phaxtract.extract_native import extract_statement_from_pdf

        return extract_statement_from_pdf(path)
    if suffix in _IMAGE_SUFFIXES:
        from phaxtract.extract_ai import extract_statement_from_image

        return extract_statement_from_image(path, engine=engine)
    msg = f"Unsupported file type: {suffix!r}"
    raise ValueError(msg)
