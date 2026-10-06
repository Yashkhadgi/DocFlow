from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any
from uuid import UUID

from app.config import settings
from app.db import SessionLocal
from app.models import Document, ExtractedField, Job, LineItem, ValidationIssue
from app.services.storage import storage
from app.workers.celery_app import celery_app
from app.workers.stubs import stub_extract


TERMINAL_STATUSES = {"needs_review", "approved", "duplicate", "failed"}


@celery_app.task(
    name="app.workers.tasks.process_document",
    acks_late=True,
    reject_on_worker_lost=True,
)
def process_document(document_id: str) -> None:
    db = SessionLocal()
    try:
        document = db.get(Document, document_id)
        if document is None or document.status in TERMINAL_STATUSES:
            return

        job = (
            db.query(Job)
            .filter(Job.document_id == document.id)
            .order_by(Job.created_at.desc())
            .first()
        )
        if job is None:
            return

        now = datetime.now(timezone.utc)
        document.status = "processing"
        document.error_message = None
        document.updated_at = now
        job.status = "processing"
        job.attempts = (job.attempts or 0) + 1
        job.started_at = now
        job.finished_at = None
        db.commit()

        file_bytes = storage.get_object(document.storage_key)
        extract, validate, needs_review, low_confidence_fields, find_business_duplicate = (
            _load_extraction_functions()
        )
        if settings.use_stub_extractor:
            result = extract(file_bytes, document.mime_type, filename=document.filename)
        else:
            result = extract(file_bytes, document.mime_type)

        issues = validate(result)
        candidates = _business_duplicate_candidates(db, document)
        duplicate_match = find_business_duplicate(result, candidates)
        low_confidence = set(low_confidence_fields(result, settings.confidence_threshold))
        review_required = needs_review(result, issues, settings.confidence_threshold)

        _persist_result(
            db=db,
            document=document,
            job=job,
            result=result,
            issues=issues,
            low_confidence_fields=low_confidence,
            duplicate_match=duplicate_match,
            review_required=review_required,
        )
    except Exception as exc:
        db.rollback()
        _mark_failed(db, document_id, exc)
    finally:
        db.close()


def _load_extraction_functions():
    """Import extraction functions lazily so the worker can boot before B's module exists."""
    from app.extraction import (
        find_business_duplicate,
        needs_review,
        validate,
    )
    try:
        from app.extraction import low_confidence_fields
    except ImportError:
        low_confidence_fields = _local_low_confidence_fields

    if settings.use_stub_extractor:
        return stub_extract, validate, needs_review, low_confidence_fields, find_business_duplicate

    from app.extraction import extract

    return extract, validate, needs_review, low_confidence_fields, find_business_duplicate


def _local_low_confidence_fields(result: Any, threshold: float | None = None) -> list[str]:
    confidence_threshold = settings.confidence_threshold if threshold is None else threshold
    return [
        name
        for name, field in _get(result, "fields", {}).items()
        if float(_get(field, "confidence", 0)) < confidence_threshold
    ]


def _business_duplicate_candidates(db, document: Document) -> list[dict[str, str | None]]:
    candidates = (
        db.query(Document)
        .filter(
            Document.user_id == document.user_id,
            Document.id != document.id,
            Document.status != "duplicate",
        )
        .all()
    )
    result = []
    for candidate in candidates:
        values = {
            field.field_name: field.value
            for field in db.query(ExtractedField)
            .filter(ExtractedField.document_id == candidate.id)
            .all()
        }
        result.append(
            {
                "id": str(candidate.id),
                "vendor_name": values.get("vendor_name"),
                "invoice_number": values.get("invoice_number"),
            }
        )
    return result


def _persist_result(
    *,
    db,
    document: Document,
    job: Job,
    result: Any,
    issues: list[Any],
    low_confidence_fields: set[str],
    duplicate_match: Any,
    review_required: bool,
) -> None:
    db.query(ExtractedField).filter(ExtractedField.document_id == document.id).delete(
        synchronize_session=False
    )
    db.query(LineItem).filter(LineItem.document_id == document.id).delete(
        synchronize_session=False
    )
    db.query(ValidationIssue).filter(ValidationIssue.document_id == document.id).delete(
        synchronize_session=False
    )

    for field_name, field in _get(result, "fields", {}).items():
        db.add(
            ExtractedField(
                document_id=document.id,
                field_name=field_name,
                value=_get(field, "value"),
                confidence=Decimal(str(_get(field, "confidence", 0))),
                needs_review=field_name in low_confidence_fields,
                bbox=_json_value(_get(field, "bbox")),
            )
        )

    for position, item in enumerate(_get(result, "line_items", []), start=1):
        db.add(
            LineItem(
                document_id=document.id,
                position=position,
                description=_get(item, "description"),
                quantity=_decimal_or_none(_get(item, "quantity")),
                rate=_decimal_or_none(_get(item, "rate")),
                amount=_decimal_or_none(_get(item, "amount")),
                confidence=_decimal_or_none(_get(item, "confidence")),
            )
        )

    for issue in issues:
        db.add(
            ValidationIssue(
                document_id=document.id,
                rule=_get(issue, "rule", "unknown"),
                severity=_get(issue, "severity", "error"),
                field_name=_get(issue, "field_name"),
                message=_get(issue, "message", "Validation failed"),
            )
        )

    duplicate_id = _get(duplicate_match, "document_id") if duplicate_match else None
    if duplicate_id is not None and not isinstance(duplicate_id, UUID):
        duplicate_id = UUID(str(duplicate_id))
    now = datetime.now(timezone.utc)
    if duplicate_id:
        document.status = "duplicate"
        document.duplicate_of_id = duplicate_id
        document.duplicate_reason = _get(duplicate_match, "reason", "same_invoice")
        document.auto_approved = False
        document.approved_at = None
    elif review_required:
        document.status = "needs_review"
        document.auto_approved = False
        document.approved_at = None
    else:
        document.status = "approved"
        document.auto_approved = True
        document.approved_at = now

    document.error_message = None
    document.updated_at = now
    job.status = "succeeded"
    job.last_error = None
    job.finished_at = now
    db.commit()


def _mark_failed(db, document_id: str, exc: Exception) -> None:
    message = str(exc).strip() or exc.__class__.__name__
    try:
        document = db.get(Document, document_id)
        if document is None:
            return
        job = (
            db.query(Job)
            .filter(Job.document_id == document.id)
            .order_by(Job.created_at.desc())
            .first()
        )
        document.status = "failed"
        document.error_message = message
        document.updated_at = datetime.now(timezone.utc)
        if job is not None:
            job.status = "failed"
            job.last_error = message
            job.finished_at = datetime.now(timezone.utc)
        db.commit()
    except Exception:
        db.rollback()


def _get(value: Any, name: str, default: Any = None) -> Any:
    if isinstance(value, dict):
        return value.get(name, default)
    return getattr(value, name, default)


def _json_value(value: Any) -> Any:
    """Convert Pydantic models and nested values into JSONB-compatible data."""
    if value is None or isinstance(value, (str, int, float, bool, list, dict)):
        if isinstance(value, list):
            return [_json_value(item) for item in value]
        if isinstance(value, dict):
            return {key: _json_value(item) for key, item in value.items()}
        return value
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        return _json_value(model_dump())
    return value


def _decimal_or_none(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
