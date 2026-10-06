from __future__ import annotations

from typing import Any, Literal
from pydantic import BaseModel, Field, field_validator


class ExtractionError(Exception):
    """
    Raised when document extraction fails.
    Attributes:
        message (str): Human-readable error description (safe for UI display).
        retryable (bool): Whether the worker should retry this failure with backoff.
    """
    def __init__(
        self,
        message: str,
        retryable: bool = True,
        fallback_allowed: bool = False,
    ):
        super().__init__(message)
        self.message = message
        self.retryable = retryable
        self.fallback_allowed = fallback_allowed


class BBox(BaseModel):
    page: int = Field(ge=1)
    x: float = Field(ge=0.0, le=1.0)
    y: float = Field(ge=0.0, le=1.0)
    w: float = Field(ge=0.0, le=1.0)
    h: float = Field(ge=0.0, le=1.0)


class FieldValue(BaseModel):
    value: str | None = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    bbox: BBox | None = None

    @field_validator("confidence", mode="before")
    @classmethod
    def validate_confidence(cls, v: Any) -> float:
        try:
            val = float(v)
            return max(0.0, min(1.0, val))
        except (TypeError, ValueError):
            return 0.0


class LineItem(BaseModel):
    description: str | None = None
    quantity: str | None = None
    rate: str | None = None
    amount: str | None = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)

    @field_validator("confidence", mode="before")
    @classmethod
    def validate_confidence(cls, v: Any) -> float:
        try:
            val = float(v)
            return max(0.0, min(1.0, val))
        except (TypeError, ValueError):
            return 0.0


class ExtractionResult(BaseModel):
    document_type: Literal["invoice"] = "invoice"
    fields: dict[str, FieldValue] = Field(default_factory=dict)
    line_items: list[LineItem] = Field(default_factory=list)
    raw_model_output: str | None = None


class ValidationIssue(BaseModel):
    rule: str
    severity: Literal["error", "warning"]
    field_name: str | None = None
    message: str


class DuplicateMatch(BaseModel):
    document_id: str
    reason: Literal["same_invoice", "same_file"] = "same_invoice"
