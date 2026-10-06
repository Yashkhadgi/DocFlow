from __future__ import annotations

from app.workers.stubs import StubExtractionResult as ExtractionResult


class ExtractionError(Exception):
    pass


class ValidationIssue:
    pass


class DuplicateMatch:
    pass


def extract(file_bytes: bytes, mime_type: str) -> ExtractionResult:
    from app.workers.stubs import stub_extract

    return stub_extract(file_bytes, mime_type)


def validate(result: ExtractionResult) -> list[ValidationIssue]:
    return []


def needs_review(
    result: ExtractionResult,
    issues: list[ValidationIssue],
    threshold: float | None = None,
) -> bool:
    confidence_threshold = 0.85 if threshold is None else threshold
    return any(field.confidence < confidence_threshold for field in result.fields.values())


def low_confidence_fields(result: ExtractionResult, threshold: float | None = None) -> list[str]:
    confidence_threshold = 0.85 if threshold is None else threshold
    return [name for name, field in result.fields.items() if field.confidence < confidence_threshold]


def find_business_duplicate(result: ExtractionResult, existing: list[dict]) -> DuplicateMatch | None:
    return None


def to_csv(docs: list[dict]) -> str:
    return ""


def to_json(docs: list[dict]) -> str:
    return "[]"
