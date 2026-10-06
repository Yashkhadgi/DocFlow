from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

from app.auth.security import create_access_token, hash_password
from app.models import Document, ExtractedField, Job, User, ValidationIssue


def create_review_document(db):
    user = User(
        email=f"documents-{uuid4().hex}@example.test",
        password_hash=hash_password("Password123"),
        full_name="Documents User",
    )
    db.add(user)
    db.flush()
    document = Document(
        user_id=user.id,
        filename="invoice-001.pdf",
        mime_type="application/pdf",
        size_bytes=1024,
        file_hash=uuid4().hex + uuid4().hex,
        storage_key=f"users/{user.id}/{uuid4()}",
        status="needs_review",
    )
    db.add(document)
    db.flush()
    db.add(Job(document_id=document.id, status="succeeded", attempts=1, max_attempts=3))
    for name, value in {
        "vendor_name": "Acme Traders",
        "invoice_number": "INV-001",
        "invoice_date": "2026-10-01",
        "subtotal": "100.00",
        "tax": "18.00",
        "total": "115.00",
    }.items():
        db.add(
            ExtractedField(
                document_id=document.id,
                field_name=name,
                value=value,
                confidence=Decimal("0.95"),
                needs_review=name == "total",
            )
        )
    db.add(
        ValidationIssue(
            document_id=document.id,
            rule="total_mismatch",
            severity="error",
            field_name="total",
            message="Subtotal plus tax does not match total",
        )
    )
    db.commit()
    db.refresh(document)
    return user, document


def test_document_search_matches_vendor_and_detail_shape(client, db, monkeypatch):
    user, document = create_review_document(db)
    token = create_access_token(str(user.id))
    monkeypatch.setattr(
        "app.routers.documents.storage.presign_get_url",
        lambda key: f"https://storage.test/{key}",
    )
    headers = {"Authorization": f"Bearer {token}"}

    listing = client.get("/api/v1/documents?q=Acme", headers=headers)
    assert listing.status_code == 200
    assert [item["id"] for item in listing.json()["items"]] == [str(document.id)]
    assert listing.json()["items"][0]["vendor_name"] == "Acme Traders"

    detail = client.get(f"/api/v1/documents/{document.id}", headers=headers)
    assert detail.status_code == 200
    body = detail.json()
    assert body["file_url"] == f"https://storage.test/{document.storage_key}"
    assert isinstance(body["fields"], list)
    assert next(field for field in body["fields"] if field["field_name"] == "total")["needs_review"]


def test_review_edit_revalidates_then_approves(client, db, monkeypatch):
    user, document = create_review_document(db)
    token = create_access_token(str(user.id))
    monkeypatch.setattr(
        "app.routers.documents.storage.presign_get_url",
        lambda key: f"https://storage.test/{key}",
    )
    headers = {"Authorization": f"Bearer {token}"}

    update = client.patch(
        f"/api/v1/documents/{document.id}/fields",
        headers=headers,
        json={"fields": {"total": "118.00"}},
    )
    assert update.status_code == 200
    body = update.json()
    total = next(field for field in body["fields"] if field["field_name"] == "total")
    assert total["reviewed_value"] == "118.00"
    assert not any(issue["rule"] == "total_mismatch" for issue in body["validation_issues"])

    approved = client.post(f"/api/v1/documents/{document.id}/approve", headers=headers)
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"


def test_document_status_filter_rejects_unknown_status(client, db):
    user, _document = create_review_document(db)
    token = create_access_token(str(user.id))

    response = client.get(
        "/api/v1/documents?status=archived",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
