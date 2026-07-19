"""NuExtract extraction template — the 'empty form' NuExtract fills from a photo.

Its shape mirrors the canonical :class:`~phaxtract.schema.Statement`. Leaf values
are NuExtract type markers (``verbatim-string``, ``date-time``, ``integer``); the
filled result is mapped to a ``Statement`` by
:func:`phaxtract.extract_ai.nuextract_to_statement`.
"""

from __future__ import annotations

from typing import Any

STATEMENT_TEMPLATE: dict[str, Any] = {
    "pharmacy": {
        "name": "verbatim-string",
        "id": "verbatim-string",
    },
    "supplier": "verbatim-string",
    "report_date": "date-time",
    "products": [
        {
            "code_produit": "verbatim-string",
            "designation": "verbatim-string",
            "sales": [
                {
                    "month": "date-time",
                    "quantity": "integer",
                }
            ],
        }
    ],
}
