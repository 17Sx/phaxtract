"""Identify pharmacy management software (LGO) from document text."""

from __future__ import annotations

import re

from phaxtract.config.loader import load_lgo_config


def identify_lgo(text: str) -> str | None:
    """Return LGO id when a configured signature matches, else None."""
    for lgo in load_lgo_config().lgos:
        for signature in lgo.signatures:
            if re.search(re.escape(signature), text, flags=re.IGNORECASE):
                return lgo.id
    return None
