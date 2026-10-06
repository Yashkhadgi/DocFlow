from __future__ import annotations

import os
from pathlib import Path
from uuid import uuid4

import pytest
from moto import mock_aws

from app.auth.security import create_access_token, hash_password
from app.config import settings
from app.models import Document, User, ValidationIssue
from app.services.storage import StorageService
from app.workers import tasks


pytestmark = pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY"),
    reason="live extraction requires ANTHROPIC_API_KEY",
)


@mock_aws
def test_sample_pack_through_upload_and_real_worker(client, db, monkeypatch) -> None:
    from app.routers import documents

    samples = Path(__file__).resolve().parents[2] / "samples" / "invoices"
    monkeypatch.setattr(settings, "s3_endpoint_url", None)
    monkeypatch.setattr(settings, "s3_region", "us-east-1")
    monkeypatch.setattr(settings, "s3_access_key", "testing")
    monkeypatch.setattr(settings, "s3_secret_key", "testing")
    monkeypatch.setattr(settings, "s3_bucket", "docflow-live-test")
    monkeypatch.setattr(settings, "use_stub_extractor", False)

    storage = StorageService()
    storage.client.create_bucket(Bucket=storage.bucket)
    monkeypatch.setattr(documents, "storage", storage)
    monkeypatch.setattr(tasks, "storage", storage)

    class TaskResult:
        id = "live-test-task"

    monkeypatch.setattr(documents.process_document, "delay", lambda _id: TaskResult())

    user = User(
        email=f"live-{uuid4().hex}@example.test",
        password_hash=hash_password("Password123"),
        full_name="Live Integration Test",
    )
    db.add(user)
    db.commit()
    token = create_access_token(str(user.id))
    headers = {"Authorization": f"Bearer {token}"}

    def upload(name: str) -> Document:
        mime = "application/pdf" if name.endswith(".pdf") else (
            "image/png" if name.endswith(".png") else "image/jpeg"
        )
        response = client.post(
            "/api/v1/documents/upload",
            files=[("files", (name, (samples / name).read_bytes(), mime))],
            headers=headers,
        )
        assert response.status_code == 200, name
        result = response.json()["results"][0]
        assert result["error"] is None, (name, result)
        document = db.get(Document, result["document_id"])
        assert document is not None
        if result["status"] == "queued":
            tasks.process_document.run(str(document.id))
            db.expire_all()
        return document

    clean = upload("clean_invoice.pdf")
    assert clean.status in {"approved", "needs_review"}

    copy = upload("clean_invoice_copy.pdf")
    assert copy.status == "duplicate"
    assert copy.duplicate_reason == "same_file"
    assert copy.duplicate_of_id == clean.id

    resaved = upload("same_invoice_resaved.pdf")
    assert resaved.status == "duplicate"
    assert resaved.duplicate_reason == "same_invoice"
    assert resaved.duplicate_of_id == clean.id

    for name in (
        "scanned_invoice.pdf",
        "photo_invoice.jpg",
        "blurry_invoice.png",
        "wrong_total.pdf",
        "bad_gstin.pdf",
    ):
        document = upload(name)
        assert document.status in {"approved", "needs_review"}, name
        issue_rules = {
            rule for (rule,) in db.query(ValidationIssue.rule)
            .filter(ValidationIssue.document_id == document.id)
            .all()
        }
        if name == "wrong_total.pdf":
            assert document.status == "needs_review"
            assert "total_mismatch" in issue_rules
        if name == "bad_gstin.pdf":
            assert document.status == "needs_review"
            assert "invalid_gstin" in issue_rules
