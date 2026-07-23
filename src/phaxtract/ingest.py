"""Document ingestion and text-layer detection for the native PDF path."""

from __future__ import annotations

from pathlib import Path

import pdfplumber


def has_text_layer(pdf: str | Path, *, min_chars: int = 20) -> bool:
    """Return True when the PDF exposes at least ``min_chars`` selectable characters.

    This is the sole native-vs-photo discriminant: a text layer means the native
    pdfplumber path can read the document; its absence routes to the photo path.
    Scans pages lazily and stops as soon as the threshold is reached.
    """
    total = 0
    with pdfplumber.open(str(pdf)) as document:
        for page in document.pages:
            total += len((page.extract_text() or "").strip())
            if total >= min_chars:
                return True
    return False
