"""Load and validate embedded JSON business-rule configs."""

from __future__ import annotations

import json
from importlib import resources
from typing import Any

from pydantic import BaseModel, Field


class LgoFingerprint(BaseModel):
    id: str
    display_name: str
    signatures: list[str] = Field(min_length=1)
    statement_types: list[str] = Field(default_factory=lambda: ["monthly", "period"])


class LgoConfig(BaseModel):
    lgos: list[LgoFingerprint]


def _load_json(filename: str) -> Any:
    raw = resources.files("phaxtract.config").joinpath(filename).read_text(encoding="utf-8")
    return json.loads(raw)


def load_lgo_config() -> LgoConfig:
    return LgoConfig.model_validate(_load_json("lgo_fingerprints.json"))


def load_column_aliases() -> dict[str, str]:
    data = _load_json("column_aliases.json")
    if not isinstance(data, dict):
        msg = "column_aliases.json must be a JSON object"
        raise TypeError(msg)
    return {str(k).strip().lower(): str(v) for k, v in data.items()}


def load_month_abbreviations() -> dict[str, str]:
    data = _load_json("month_abbreviations.json")
    if not isinstance(data, dict):
        msg = "month_abbreviations.json must be a JSON object"
        raise TypeError(msg)
    return {str(k).strip().lower(): str(v).zfill(2) for k, v in data.items()}
