from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from celery.exceptions import Retry

from app.auth.security import hash_password
from app.extraction.types import ExtractionResult, FieldValue
from app.models import Document, ExtractedField, Job, LineItem, User, ValidationIssue
from app.workers import tasks as task_module
from app.workers.celery_app import celery_app
from app.workers.stubs import StubExtractionResult, StubField, StubLineItem, stub_extract


PDF_BYTES = b"%PDF-1.7\nworker test document"


class FakeStorage:
    def __init__(self, objects: dict[str, bytes]) -> None:
        self.objects = objects

    def get_object(self, key: str) -> bytes:
        return self.objects[key]


def extraction_result(*, low_confidence: bool = False) -> StubExtractionResult:
    confidence = 0.60 if low_confidence else 0.95
    return StubExtractionResult(
        document_type="invoice",
        fields={
            "vendor_name": StubField("Acme Traders", confidence),
            "invoice_number": StubField("INV-2026-001", confidence),
            "invoice_date": StubField("2026-10-01", confidence),
            "gstin": StubField("27ABCDE1234F1Z5", confidence),
            "currency": StubField("INR", confidence),
            "subtotal": StubField("10000.00", confidence),
            "tax": StubField("1800.00", confidence),
            "total": StubField("11800.00", confidence),
        },
        line_items=[StubLineItem("Steel rods", "10", "1000.00", "10000.00", confidence)],
    )


def create_document(db, *, email: str = "worker@example.test", filename: str = "invoice.pdf"):
    user = User(email=email, password_hash=hash_password("Password123"), full_name="Worker User")
    db.add(user)
    db.flush()
    key = f"users/{user.id}/{uuid4()}"
    document = Document(
        user_id=user.id,
        filename=filename,
        mime_type="application/pdf",
        size_bytes=len(PDF_BYTES),
        file_hash=("a" * 64),
        storage_key=key,
        status="queued",
    )
    db.add(document)
    db.flush()
    db.add(Job(document_id=document.id, status="queued"))
    db.commit()
    db.refresh(document)
    return user, document


def run_task(db, monkeypatch, document_id: str, file_bytes: bytes = PDF_BYTES) -> None:
    document = db.get(Document, document_id)
    monkeypatch.setattr(task_module, "storage", FakeStorage({document.storage_key: file_bytes}))
    try:
        task_module.process_document.run(str(document_id))
    except Retry:
        pass
    db.expire_all()


def test_celery_delivery_settings() -> None:
    assert celery_app.conf.task_acks_late is True
    assert celery_app.conf.task_reject_on_worker_lost is True
    assert celery_app.conf.worker_prefetch_multiplier == 1
    assert celery_app.conf.task_serializer == "json"
    assert celery_app.conf.result_serializer == "json"
    assert celery_app.conf.accept_content == ["json"]


def test_stub_failure_marker_is_filename_based(monkeypatch) -> None:
    monkeypatch.setattr(task_module.settings, "force_fail_filename_contains", "trigger")
    with pytest.raises(RuntimeError, match="trigger.pdf"):
        stub_extract(PDF_BYTES, "application/pdf", filename="trigger.pdf")


def test_worker_happy_path_needs_review(client, db, monkeypatch) -> None:
    _user, document = create_document(db)
    monkeypatch.setattr(task_module, "_load_extraction_functions", lambda: (
        lambda data, mime, filename=None: extraction_result(low_confidence=True),
        lambda result: [],
        lambda result, issues, threshold=None: True,
        lambda result, threshold=None: ["gstin"],
        lambda result, existing: None,
    ))

    run_task(db, monkeypatch, document.id)

    assert document.status == "needs_review"
    assert document.auto_approved is False
    assert db.query(Job).filter(Job.document_id == document.id).one().status == "succeeded"
    assert db.query(ExtractedField).filter(ExtractedField.document_id == document.id).count() == 8
    assert db.query(LineItem).filter(LineItem.document_id == document.id).count() == 1


def test_worker_clean_path_auto_approves(client, db, monkeypatch) -> None:
    _user, document = create_document(db)
    result = extraction_result()
    monkeypatch.setattr(task_module, "_load_extraction_functions", lambda: (
        lambda data, mime, filename=None: result,
        lambda result: [],
        lambda result, issues, threshold=None: False,
        lambda result, threshold=None: [],
        lambda result, existing: None,
    ))

    run_task(db, monkeypatch, document.id)

    assert document.status == "approved"
    assert document.auto_approved is True
    assert document.approved_at is not None
    assert db.query(Job).filter(Job.document_id == document.id).one().status == "succeeded"


def test_worker_serializes_pydantic_bboxes_for_jsonb(client, db, monkeypatch) -> None:
    _user, document = create_document(db)
    result = ExtractionResult(
        fields={
            "vendor_name": FieldValue(
                value="Acme Traders",
                confidence=0.95,
                bbox={"page": 1, "x": 0.1, "y": 0.1, "w": 0.2, "h": 0.1},
            )
        }
    )
    monkeypatch.setattr(task_module, "_load_extraction_functions", lambda: (
        lambda data, mime, filename=None: result,
        lambda result: [],
        lambda result, issues, threshold=None: False,
        lambda result, threshold=None: [],
        lambda result, existing: None,
    ))

    run_task(db, monkeypatch, document.id)

    field = db.query(ExtractedField).filter(ExtractedField.document_id == document.id).one()
    assert field.bbox == {"page": 1, "x": 0.1, "y": 0.1, "w": 0.2, "h": 0.1}


def test_worker_redelivery_is_idempotent(client, db, monkeypatch) -> None:
    _user, document = create_document(db)
    monkeypatch.setattr(task_module, "_load_extraction_functions", lambda: (
        lambda data, mime, filename=None: extraction_result(),
        lambda result: [],
        lambda result, issues, threshold=None: False,
        lambda result, threshold=None: [],
        lambda result, existing: None,
    ))
    run_task(db, monkeypatch, document.id)
    first_fields = db.query(ExtractedField).filter(ExtractedField.document_id == document.id).count()
    first_items = db.query(LineItem).filter(LineItem.document_id == document.id).count()
    first_attempts = db.query(Job).filter(Job.document_id == document.id).one().attempts

    run_task(db, monkeypatch, document.id)

    assert document.status == "approved"
    assert db.query(ExtractedField).filter(ExtractedField.document_id == document.id).count() == first_fields
    assert db.query(LineItem).filter(LineItem.document_id == document.id).count() == first_items
    assert db.query(Job).filter(Job.document_id == document.id).one().attempts == first_attempts


def test_worker_extraction_exception_marks_job_failed(client, db, monkeypatch) -> None:
    _user, document = create_document(db, filename="failme.pdf")
    def fail(*_args, **_kwargs):
        raise RuntimeError("extractor unavailable")

    monkeypatch.setattr(task_module, "_load_extraction_functions", lambda: (
        fail,
        lambda result: [],
        lambda result, issues, threshold=None: False,
        lambda result, threshold=None: [],
        lambda result, existing: None,
    ))
    monkeypatch.setattr(
        task_module.process_document,
        "retry",
        lambda **_kwargs: Retry("retry scheduled"),
    )

    for _ in range(task_module.settings.job_max_attempts):
        run_task(db, monkeypatch, document.id)

    job = db.query(Job).filter(Job.document_id == document.id).one()
    assert document.status == "failed"
    assert document.error_message == "extractor unavailable"
    assert job.status == "failed"
    assert job.last_error == "extractor unavailable"
    assert job.attempts == task_module.settings.job_max_attempts


def test_business_duplicate_stores_extraction_and_points_to_original(client, db, monkeypatch) -> None:
    user, original = create_document(db, filename="original.pdf")
    original.status = "approved"
    db.add(ExtractedField(document_id=original.id, field_name="vendor_name", value="Acme Traders", confidence=Decimal("0.95")))
    db.add(ExtractedField(document_id=original.id, field_name="invoice_number", value="INV-2026-001", confidence=Decimal("0.95")))
    db.commit()

    duplicate = Document(
        user_id=user.id,
        filename="resaved.pdf",
        mime_type="application/pdf",
        size_bytes=len(PDF_BYTES),
        file_hash=("b" * 64),
        storage_key=f"users/{user.id}/{uuid4()}",
        status="queued",
    )
    db.add(duplicate)
    db.flush()
    db.add(Job(document_id=duplicate.id, status="queued"))
    db.commit()

    def find_duplicate(_result, existing):
        assert {row["id"] for row in existing} == {str(original.id)}
        return {"document_id": str(original.id), "reason": "same_invoice"}

    monkeypatch.setattr(task_module, "_load_extraction_functions", lambda: (
        lambda data, mime, filename=None: extraction_result(),
        lambda result: [],
        lambda result, issues, threshold=None: False,
        lambda result, threshold=None: [],
        find_duplicate,
    ))

    run_task(db, monkeypatch, duplicate.id, file_bytes=b"%PDF-1.7\nresaved bytes")

    assert duplicate.status == "duplicate"
    assert duplicate.duplicate_of_id == original.id
    assert duplicate.duplicate_reason == "same_invoice"
    assert db.query(ExtractedField).filter(ExtractedField.document_id == duplicate.id).count() == 8
    assert db.query(Job).filter(Job.document_id == duplicate.id).one().status == "succeeded"


def test_worker_replaces_existing_rows_instead_of_appending(client, db, monkeypatch) -> None:
    _user, document = create_document(db)
    db.add(ExtractedField(document_id=document.id, field_name="old_field", value="old", confidence=Decimal("0.95")))
    db.add(LineItem(document_id=document.id, position=99, description="old row", confidence=Decimal("0.95")))
    db.add(ValidationIssue(document_id=document.id, rule="old_rule", severity="warning", message="old issue"))
    db.commit()
    monkeypatch.setattr(task_module, "_load_extraction_functions", lambda: (
        lambda data, mime, filename=None: extraction_result(),
        lambda result: [],
        lambda result, issues, threshold=None: False,
        lambda result, threshold=None: [],
        lambda result, existing: None,
    ))

    run_task(db, monkeypatch, document.id)

    assert db.query(ExtractedField).filter(ExtractedField.document_id == document.id).count() == 8
    assert db.query(ExtractedField).filter(
        ExtractedField.document_id == document.id,
        ExtractedField.field_name == "old_field",
    ).count() == 0
    assert db.query(LineItem).filter(LineItem.document_id == document.id).count() == 1
    assert db.query(ValidationIssue).filter(ValidationIssue.document_id == document.id).count() == 0


def test_business_duplicate_candidates_are_user_isolated(client, db, monkeypatch) -> None:
    _user_a, document = create_document(db, email="worker-a@example.test")
    user_b, other = create_document(db, email="worker-b@example.test", filename="other.pdf")
    other.user_id = user_b.id
    other.status = "approved"
    db.add(ExtractedField(document_id=other.id, field_name="vendor_name", value="Acme Traders", confidence=Decimal("0.95")))
    db.add(ExtractedField(document_id=other.id, field_name="invoice_number", value="INV-2026-001", confidence=Decimal("0.95")))
    db.commit()

    def assert_no_cross_user_match(_result, existing):
        assert all(row["id"] != str(other.id) for row in existing)
        return None

    monkeypatch.setattr(task_module, "_load_extraction_functions", lambda: (
        lambda data, mime, filename=None: extraction_result(),
        lambda result: [],
        lambda result, issues, threshold=None: False,
        lambda result, threshold=None: [],
        assert_no_cross_user_match,
    ))

    run_task(db, monkeypatch, document.id)

    assert document.status == "approved"
