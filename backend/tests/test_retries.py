from __future__ import annotations

from decimal import Decimal

from celery.exceptions import Retry

from app.auth.security import create_access_token, hash_password
from app.config import settings
from app.models import Document, ExtractedField, Job, User
from app.workers import tasks as task_module
from app.workers.stubs import StubExtractionResult

from test_worker import PDF_BYTES, FakeStorage, create_document, extraction_result


def _patch_retry(monkeypatch):
    countdowns: list[int] = []

    def fake_retry(*, countdown: int, exc=None, max_retries=None):
        countdowns.append(countdown)
        return Retry("retry scheduled")

    monkeypatch.setattr(task_module.process_document, "retry", fake_retry)
    return countdowns


def _run_with_storage(db, monkeypatch, document_id, file_bytes=PDF_BYTES):
    document = db.get(Document, document_id)
    monkeypatch.setattr(task_module, "storage", FakeStorage({document.storage_key: file_bytes}))
    try:
        task_module.process_document.run(str(document_id))
    except Retry:
        pass
    db.expire_all()


def test_transient_failure_retries_then_succeeds_on_second_attempt(db, monkeypatch):
    _user, document = create_document(db)
    countdowns = _patch_retry(monkeypatch)
    calls = 0

    def transient_extractor(*_args, **_kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("temporary extractor outage")
        return extraction_result()

    monkeypatch.setattr(task_module, "_load_extraction_functions", lambda: (
        transient_extractor,
        lambda result: [],
        lambda result, issues, threshold=None: False,
        lambda result, threshold=None: [],
        lambda result, existing: None,
    ))

    _run_with_storage(db, monkeypatch, document.id)
    assert document.status == "processing"
    assert db.query(Job).filter(Job.document_id == document.id).one().attempts == 1
    assert countdowns == [5]

    _run_with_storage(db, monkeypatch, document.id)
    job = db.query(Job).filter(Job.document_id == document.id).one()
    assert document.status == "approved"
    assert job.status == "succeeded"
    assert job.attempts == 2


def test_permanent_failure_stops_after_max_attempts(db, monkeypatch):
    _user, document = create_document(db)
    countdowns = _patch_retry(monkeypatch)

    def permanent_extractor(*_args, **_kwargs):
        raise RuntimeError("provider unavailable")

    monkeypatch.setattr(task_module, "_load_extraction_functions", lambda: (
        permanent_extractor,
        lambda result: [],
        lambda result, issues, threshold=None: False,
        lambda result, threshold=None: [],
        lambda result, existing: None,
    ))

    for _ in range(settings.job_max_attempts):
        _run_with_storage(db, monkeypatch, document.id)

    job = db.query(Job).filter(Job.document_id == document.id).one()
    assert document.status == "failed"
    assert job.status == "failed"
    assert job.attempts == settings.job_max_attempts
    assert job.last_error == "provider unavailable"
    assert countdowns == [5, 20]


def test_non_retryable_failure_fails_after_one_attempt(db, monkeypatch):
    _user, document = create_document(db)
    countdowns = _patch_retry(monkeypatch)

    class UnsupportedContentError(Exception):
        retryable = False

    def unsupported_extractor(*_args, **_kwargs):
        raise UnsupportedContentError("unsupported content")

    monkeypatch.setattr(task_module, "_load_extraction_functions", lambda: (
        unsupported_extractor,
        lambda result: [],
        lambda result, issues, threshold=None: False,
        lambda result, threshold=None: [],
        lambda result, existing: None,
    ))

    _run_with_storage(db, monkeypatch, document.id)

    job = db.query(Job).filter(Job.document_id == document.id).one()
    assert document.status == "failed"
    assert job.status == "failed"
    assert job.attempts == 1
    assert countdowns == []


def test_manual_retry_requeues_failed_document_and_does_not_append_rows(client, db, monkeypatch):
    user, document = create_document(db, filename="retry.pdf")
    document.status = "failed"
    document.error_message = "temporary extractor outage"
    job = db.query(Job).filter(Job.document_id == document.id).one()
    job.status = "failed"
    job.attempts = settings.job_max_attempts
    job.last_error = document.error_message
    db.add(ExtractedField(document_id=document.id, field_name="old_field", value="old", confidence=Decimal("0.95")))
    db.commit()

    class AsyncResult:
        id = "retry-task-id"

    monkeypatch.setattr(task_module.storage, "presign_get_url", lambda key: f"http://storage/{key}")
    monkeypatch.setattr(
        "app.routers.documents.process_document.delay",
        lambda document_id: AsyncResult(),
    )
    token = create_access_token(str(user.id))

    response = client.post(
        f"/api/v1/documents/{document.id}/retry",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "queued"
    db.expire_all()
    assert document.status == "queued"
    assert job.status == "queued"
    assert job.attempts == 0
    assert job.last_error is None

    monkeypatch.setattr(task_module, "storage", FakeStorage({document.storage_key: PDF_BYTES}))
    monkeypatch.setattr(task_module, "_load_extraction_functions", lambda: (
        lambda data, mime, filename=None: extraction_result(),
        lambda result: [],
        lambda result, issues, threshold=None: False,
        lambda result, threshold=None: [],
        lambda result, existing: None,
    ))
    task_module.process_document.run(str(document.id))
    db.expire_all()

    assert document.status == "approved"
    assert db.query(ExtractedField).filter(ExtractedField.document_id == document.id).count() == 8
    assert db.query(ExtractedField).filter(
        ExtractedField.document_id == document.id,
        ExtractedField.field_name == "old_field",
    ).count() == 0


def test_retry_endpoint_rejects_non_failed_documents(client, db):
    user, document = create_document(db)
    token = create_access_token(str(user.id))

    response = client.post(
        f"/api/v1/documents/{document.id}/retry",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "conflict"


def test_retry_endpoint_hides_another_users_document(client, db):
    _user, document = create_document(db, email="owner@example.test")
    other = User(email="other@example.test", password_hash=hash_password("Password123"), full_name="Other")
    db.add(other)
    db.commit()
    token = create_access_token(str(other.id))

    response = client.post(
        f"/api/v1/documents/{document.id}/retry",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_stub_can_fail_for_first_n_attempts(monkeypatch):
    monkeypatch.setattr(task_module.settings, "force_fail_filename_contains", "failme")
    monkeypatch.setattr(task_module.settings, "force_fail_until_attempt", 1)
    from app.workers.stubs import stub_extract

    try:
        stub_extract(PDF_BYTES, "application/pdf", filename="failme.pdf", attempt=1)
    except RuntimeError:
        pass
    else:
        raise AssertionError("attempt one should fail")

    result = stub_extract(PDF_BYTES, "application/pdf", filename="failme.pdf", attempt=2)
    assert isinstance(result, StubExtractionResult)
