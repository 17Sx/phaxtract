"""Canonical JSON schema for extracted pharmacy sales statements."""

from __future__ import annotations

import re
from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, field_validator

StatementType = Literal["monthly", "period"]
_MONTH_PATTERN = re.compile(r"^\d{4}-\d{2}$")
_EAN_PATTERN = re.compile(r"^\d{13}$")


class Pharmacy(BaseModel):
    name: str
    address: str = ""
    id: str = ""


class DocumentMeta(BaseModel):
    source_file: str
    lgo: str
    statement_type: StatementType
    pharmacy: Pharmacy
    supplier: str = ""
    months: list[str] = Field(default_factory=list)
    generated_at: date | None = None
    page_count: int = Field(default=1, ge=1)

    @field_validator("months")
    @classmethod
    def validate_months(cls, value: list[str]) -> list[str]:
        for month in value:
            if not _MONTH_PATTERN.match(month):
                msg = f"Invalid month format: {month!r}, expected YYYY-MM"
                raise ValueError(msg)
        return value


class Prices(BaseModel):
    pa_cat: float | None = None
    pa_cat_net: float | None = None
    pv_ttc: float | None = None


class LineSource(BaseModel):
    page: int = Field(default=1, ge=1)
    row_bbox: list[float] = Field(default_factory=lambda: [0.0, 0.0, 0.0, 0.0])


class Line(BaseModel):
    code_produit: str
    designation: str = ""
    prices: Prices = Field(default_factory=Prices)
    quantities: dict[str, int | float] = Field(default_factory=dict)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    source: LineSource = Field(default_factory=LineSource)

    @field_validator("code_produit")
    @classmethod
    def validate_ean(cls, value: str) -> str:
        cleaned = re.sub(r"\D", "", value)
        if cleaned and not _EAN_PATTERN.match(cleaned):
            msg = f"Invalid EAN-13: {value!r}"
            raise ValueError(msg)
        return cleaned


class ValidationResult(BaseModel):
    totals_reconciled: bool = False
    row_count: int = Field(default=0, ge=0)
    flags: list[str] = Field(default_factory=list)


class Statement(BaseModel):
    document: DocumentMeta
    lines: list[Line] = Field(default_factory=list)
    validation: ValidationResult = Field(default_factory=ValidationResult)
