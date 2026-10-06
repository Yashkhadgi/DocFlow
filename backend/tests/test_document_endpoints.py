from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
import json
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest
from app.auth.security import create_access_token, hash_password
from app.models import Document, ExtractedField, Job, LineItem, User, ValidationIssue


def load_fixture(name: str) -> dict:
    candidates = [
        Path("/contracts/fixtures") / name,
        Path(__file__).resolve().parents[2] / "contracts" / "fixtures" / name,
    ]
    for p in candidates:
        if p.exists():
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f)
    raise FileNotFoundError(f"Fixture {name} not found in {[str(p) for p in candidates]}")


def assert_matches_fixture_shape(actual: dict, expected: dict) -> None:
    assert set(actual.keys()) == set(expected.keys()), f"Keys mismatch: {set(actual.keys()) ^ set(expected.keys())}"
    for k, exp_val in expected.items():
        act_val = actual[k]
        if exp_val is None:
            continue
        if isinstance(exp_val, dict):
            assert isinstance(act_val, dict), f"Key {k} expected dict, got {type(act_val)}"
            assert set(act_val.keys()) == set(exp_val.keys()), f"Dict {k} keys mismatch: {set(act_val.keys()) ^ set(exp_val.keys())}"
        elif isinstance(exp_val, list):
            assert isinstance(act_val, list), f"Key {k} expected list, got {type(act_val)}"
            if exp_val and act_val:
                exp_item = exp_val[0]
                act_item = act_val[0]
                if isinstance(exp_item, dict):
                    assert isinstance(act_item, dict), f"Item in {k} expected dict"
                    assert set(act_item.keys()) == set(exp_item.keys()), f"Item in {k} keys mismatch: {set(act_item.keys()) ^ set(exp_item.keys())}"
        elif isinstance(exp_val, bool):
            assert isinstance(act_val, bool), f"Key {k} expected bool, got {type(act_val)}"
        elif isinstance(exp_val, int):
            assert isinstance(act_val, int), f"Key {k} expected int, got {type(act_val)}"
        elif isinstance(exp_val, float):
            assert isinstance(act_val, (float, int)), f"Key {k} expected float, got {type(act_val)}"
        elif isinstance(exp_val, str):
            assert isinstance(act_val, str), f"Key {k} expected str, got {type(act_val)}"


def create_user(db, prefix: str = "doc") -> User:
    user = User(
        email=f"{prefix}-{uuid4().hex}@example.test",
        password_hash=hash_password("Password123"),
        full_name=f"User {prefix}",
    )
    db.add(user)
    db.flush()
    return user


def create_seed_document(
    db,
    user: User,
    *,
    filename: str = "invoice.pdf",
    status: str = "needs_review",
    auto_approved: bool = False,
    duplicate_of_id=None,
    duplicate_reason: str | None = None,
    error_message: str | None = None,
    vendor_name: str | None = "Acme Corp",
    invoice_number: str | None = "INV-100",
    invoice_date: str | None = "2026-10-01",
    subtotal: str | None = "100.00",
    tax: str | None = "18.00",
    total: str | None = "118.00",
    currency: str | None = "INR",
    low_confidence: bool = False,
    issues: list[dict[str, str]] | None = None,
    line_items: list[dict[str, Any]] | None = None,
) -> Document:
    doc = Document(
        user_id=user.id,
        filename=filename,
        mime_type="application/pdf",
        size_bytes=2048,
        file_hash=uuid4().hex + uuid4().hex,
        storage_key=f"users/{user.id}/{uuid4()}",
        status=status,
        auto_approved=auto_approved,
        duplicate_of_id=duplicate_of_id,
        duplicate_reason=duplicate_reason,
        error_message=error_message,
    )
    db.add(doc)
    db.flush()

    if status != "duplicate":
        job = Job(
            document_id=doc.id,
            status="succeeded" if status != "failed" else "failed",
            attempts=1,
            max_attempts=3,
            last_error=error_message,
        )
        db.add(job)

    field_data = {
        "vendor_name": vendor_name,
        "invoice_number": invoice_number,
        "invoice_date": invoice_date,
        "subtotal": subtotal,
        "tax": tax,
        "currency": currency,
        "total": total,
    }
    for fname, fval in field_data.items():
        if fval is not None:
            db.add(
                ExtractedField(
                    document_id=doc.id,
                    field_name=fname,
                    value=fval,
                    confidence=Decimal("0.60") if (low_confidence and fname == "total") else Decimal("0.95"),
                    needs_review=low_confidence and fname == "total",
                )
            )

    if line_items:
        for idx, item in enumerate(line_items, 1):
            db.add(
                LineItem(
                    document_id=doc.id,
                    position=item.get("position", idx),
                    description=item.get("description", "Item"),
                    quantity=Decimal(str(item["quantity"])) if item.get("quantity") is not None else None,
                    rate=Decimal(str(item["rate"])) if item.get("rate") is not None else None,
                    amount=Decimal(str(item["amount"])) if item.get("amount") is not None else None,
                    confidence=Decimal(str(item.get("confidence", "0.95"))),
                )
            )

    if issues:
        for iss in issues:
            db.add(
                ValidationIssue(
                    document_id=doc.id,
                    rule=iss["rule"],
                    severity=iss["severity"],
                    field_name=iss.get("field_name"),
                    message=iss["message"],
                )
            )

    db.commit()
    db.refresh(doc)
    return doc


def test_list_documents_pagination_and_counts_and_fixture_shape(client, db):
    user = create_user(db, "list-all")
    token = create_access_token(str(user.id))
    headers = {"Authorization": f"Bearer {token}"}

    # Create one document in each of the 6 statuses
    primary = create_seed_document(db, user, filename="inv_approved.pdf", status="approved", auto_approved=True)
    create_seed_document(db, user, filename="inv_needs_review.pdf", status="needs_review", low_confidence=True)
    create_seed_document(db, user, filename="inv_queued.pdf", status="queued")
    create_seed_document(db, user, filename="inv_processing.pdf", status="processing")
    create_seed_document(db, user, filename="inv_failed.pdf", status="failed", error_message="Fatal error")
    create_seed_document(
        db,
        user,
        filename="inv_duplicate.pdf",
        status="duplicate",
        duplicate_of_id=primary.id,
        duplicate_reason="same_file",
    )

    # 1. Whole collection listing
    resp = client.get("/api/v1/documents?page=1&page_size=2", headers=headers)
    assert resp.status_code == 200
    data = resp.json()

    assert data["page"] == 1
    assert data["page_size"] == 2
    assert data["total"] == 6
    assert len(data["items"]) == 2
    assert "currency" in data["items"][0]
    assert data["counts"] == {
        "queued": 1,
        "processing": 1,
        "needs_review": 1,
        "approved": 1,
        "failed": 1,
        "duplicate": 1,
    }

    # Verify fixture structure matches contracts/fixtures/documents_list.json
    expected_fixture = load_fixture("documents_list.json")
    assert_matches_fixture_shape(data, expected_fixture)


def test_list_documents_filtering_and_search(client, db):
    user = create_user(db, "search")
    token = create_access_token(str(user.id))
    headers = {"Authorization": f"Bearer {token}"}

    create_seed_document(
        db,
        user,
        filename="alpha_receipt.pdf",
        vendor_name="Acme Supplies",
        invoice_number="INV-ALPHA-01",
        status="needs_review",
    )
    create_seed_document(
        db,
        user,
        filename="beta_bill.pdf",
        vendor_name="Global Goods",
        invoice_number="INV-BETA-02",
        status="approved",
    )

    # Filter by status
    r_status = client.get("/api/v1/documents?status=needs_review", headers=headers)
    assert r_status.status_code == 200
    items = r_status.json()["items"]
    assert len(items) == 1
    assert items[0]["filename"] == "alpha_receipt.pdf"
    # Counts cover the whole user set, not just filtered page
    assert r_status.json()["counts"]["needs_review"] == 1
    assert r_status.json()["counts"]["approved"] == 1

    # Search by filename
    r_q_file = client.get("/api/v1/documents?q=alpha", headers=headers)
    assert r_q_file.status_code == 200
    assert len(r_q_file.json()["items"]) == 1

    # Search by vendor_name (case-insensitive)
    r_q_vendor = client.get("/api/v1/documents?q=gLoBaL", headers=headers)
    assert r_q_vendor.status_code == 200
    assert len(r_q_vendor.json()["items"]) == 1
    assert r_q_vendor.json()["items"][0]["vendor_name"] == "Global Goods"

    # Search by invoice_number
    r_q_inv = client.get("/api/v1/documents?q=BETA-02", headers=headers)
    assert r_q_inv.status_code == 200
    assert len(r_q_inv.json()["items"]) == 1
    assert r_q_inv.json()["items"][0]["invoice_number"] == "INV-BETA-02"


def test_list_documents_returns_reviewed_currency_and_zero_total(client, db):
    user = create_user(db, "currency")
    token = create_access_token(str(user.id))
    headers = {"Authorization": f"Bearer {token}"}

    doc = create_seed_document(
        db,
        user,
        filename="zero_usd.pdf",
        status="needs_review",
        currency="INR",
        total="0.00",
    )
    currency_field = (
        db.query(ExtractedField)
        .filter(ExtractedField.document_id == doc.id, ExtractedField.field_name == "currency")
        .first()
    )
    currency_field.reviewed_value = "USD"
    db.commit()

    response = client.get("/api/v1/documents", headers=headers)

    assert response.status_code == 200
    item = response.json()["items"][0]
    assert item["currency"] == "USD"
    assert item["total"] == "0.00"


def test_stub_recovery_lists_candidates_and_skips_human_edits(client, db, monkeypatch):
    user = create_user(db, "stub-recovery")
    token = create_access_token(str(user.id))
    headers = {"Authorization": f"Bearer {token}"}

    stub_doc = create_seed_document(
        db,
        user,
        filename="historical_stub.pdf",
        status="approved",
        vendor_name="Demo Vendor 07",
        subtotal="10000.00",
        tax="1800.00",
        total="11800.00",
    )
    edited_doc = create_seed_document(
        db,
        user,
        filename="edited_stub.pdf",
        status="needs_review",
        vendor_name="Demo Vendor 08",
        subtotal="10000.00",
        tax="1800.00",
        total="12000.00",
    )
    edited_field = (
        db.query(ExtractedField)
        .filter(ExtractedField.document_id == edited_doc.id, ExtractedField.field_name == "total")
        .first()
    )
    edited_field.reviewed_value = "11800.00"
    db.commit()

    candidates = client.get("/api/v1/documents/recovery/stub-generated", headers=headers)

    assert candidates.status_code == 200
    items_by_id = {item["id"]: item for item in candidates.json()["items"]}
    assert items_by_id[str(stub_doc.id)]["can_reprocess"] is True
    assert items_by_id[str(edited_doc.id)]["can_reprocess"] is False
    assert items_by_id[str(edited_doc.id)]["has_human_edits"] is True
    assert items_by_id[str(stub_doc.id)]["backup"]["fields"]

    enqueued: list[str] = []
    monkeypatch.setattr(
        "app.routers.documents.process_document.delay",
        lambda document_id: type("Result", (), {"id": f"task-{document_id}"})(),
    )

    response = client.post(
        "/api/v1/documents/recovery/stub-generated/reprocess",
        headers=headers,
        json={
            "document_ids": [str(stub_doc.id), str(edited_doc.id)],
            "spend_limit_usd": 0,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["queued"] == [{"id": str(stub_doc.id), "filename": "historical_stub.pdf"}]
    assert {"id": str(edited_doc.id), "reason": "has_human_edits"} in body["skipped"]
    assert body["backups"]

    db.refresh(stub_doc)
    assert stub_doc.status == "queued"


def test_get_document_detail_matches_fixtures(client, db, monkeypatch):
    user = create_user(db, "detail")
    token = create_access_token(str(user.id))
    headers = {"Authorization": f"Bearer {token}"}
    monkeypatch.setattr(
        "app.routers.documents.storage.presign_get_url",
        lambda key, expires=300: f"https://storage.example.com/presigned/{key}",
    )

    # 1. Needs review detail
    doc_review = create_seed_document(
        db,
        user,
        filename="wrong_total.pdf",
        status="needs_review",
        subtotal="10000.00",
        tax="1800.00",
        total="11500.00",
        low_confidence=True,
        line_items=[
            {"position": 1, "description": "Steel rods", "quantity": "10.000", "rate": "1000.00", "amount": "10000.00"}
        ],
        issues=[
            {
                "rule": "total_mismatch",
                "severity": "error",
                "field_name": "total",
                "message": "subtotal (10000.00) + tax (1800.00) = 11800.00 but total is 11500.00",
            }
        ],
    )
    r_review = client.get(f"/api/v1/documents/{doc_review.id}", headers=headers)
    assert r_review.status_code == 200
    data_review = r_review.json()
    expected_review_fixture = load_fixture("document_detail_needs_review.json")
    assert_matches_fixture_shape(data_review, expected_review_fixture)

    # 2. Duplicate detail
    doc_dup = create_seed_document(
        db,
        user,
        filename="clean_copy.pdf",
        status="duplicate",
        duplicate_of_id=doc_review.id,
        duplicate_reason="same_file",
    )
    r_dup = client.get(f"/api/v1/documents/{doc_dup.id}", headers=headers)
    assert r_dup.status_code == 200
    data_dup = r_dup.json()
    assert data_dup["file_url"] is None
    assert data_dup["job"] is None
    expected_dup_fixture = load_fixture("document_detail_duplicate.json")
    assert_matches_fixture_shape(data_dup, expected_dup_fixture)


def test_404_for_other_user_rule_across_endpoints(client, db):
    user_a = create_user(db, "user-a")
    user_b = create_user(db, "user-b")
    doc_a = create_seed_document(db, user_a, status="needs_review")

    token_b = create_access_token(str(user_b.id))
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # All endpoints must return 404, never 403
    r_get = client.get(f"/api/v1/documents/{doc_a.id}", headers=headers_b)
    assert r_get.status_code == 404
    assert r_get.json()["error"]["code"] == "not_found"

    r_patch = client.patch(
        f"/api/v1/documents/{doc_a.id}/fields",
        headers=headers_b,
        json={"fields": {"total": "100.00"}},
    )
    assert r_patch.status_code == 404
    assert r_patch.json()["error"]["code"] == "not_found"

    r_approve = client.post(f"/api/v1/documents/{doc_a.id}/approve", headers=headers_b)
    assert r_approve.status_code == 404
    assert r_approve.json()["error"]["code"] == "not_found"

    r_retry = client.post(f"/api/v1/documents/{doc_a.id}/retry", headers=headers_b)
    assert r_retry.status_code == 404
    assert r_retry.json()["error"]["code"] == "not_found"


def test_patch_fields_409_for_non_needs_review(client, db):
    user = create_user(db, "patch-conflict")
    token = create_access_token(str(user.id))
    headers = {"Authorization": f"Bearer {token}"}

    doc_approved = create_seed_document(db, user, status="approved")
    r = client.patch(
        f"/api/v1/documents/{doc_approved.id}/fields",
        headers=headers,
        json={"fields": {"total": "120.00"}},
    )
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "conflict"


def test_patch_fields_sets_reviewed_value_clears_needs_review_and_revalidates(client, db, monkeypatch):
    user = create_user(db, "patch-revalidate")
    token = create_access_token(str(user.id))
    headers = {"Authorization": f"Bearer {token}"}
    monkeypatch.setattr(
        "app.routers.documents.storage.presign_get_url",
        lambda key, expires=300: f"https://storage.example.com/{key}",
    )

    doc = create_seed_document(
        db,
        user,
        status="needs_review",
        subtotal="100.00",
        tax="18.00",
        total="115.00",
        low_confidence=True,
        issues=[
            {
                "rule": "total_mismatch",
                "severity": "error",
                "field_name": "total",
                "message": "subtotal (100.00) + tax (18.00) = 118.00 but total is 115.00",
            }
        ],
    )

    # Send correct total to fix the mismatch and add line items
    patch_resp = client.patch(
        f"/api/v1/documents/{doc.id}/fields",
        headers=headers,
        json={
            "fields": {"total": "118.00"},
            "line_items": [
                {"position": 1, "description": "Consulting", "quantity": "1", "rate": "100.00", "amount": "100.00"}
            ],
        },
    )
    assert patch_resp.status_code == 200
    body = patch_resp.json()

    total_field = next(f for f in body["fields"] if f["field_name"] == "total")
    assert total_field["reviewed_value"] == "118.00"
    assert total_field["needs_review"] is False

    # Validation should have re-run: total_mismatch is resolved!
    assert not any(i["rule"] == "total_mismatch" for i in body["validation_issues"])

    # Check line items are replaced
    assert len(body["line_items"]) == 1
    assert body["line_items"][0]["description"] == "Consulting"
    assert body["line_items"][0]["amount"] == "100.00"


def test_approve_conflict_with_errors_and_force_approve(client, db, monkeypatch):
    user = create_user(db, "approve")
    token = create_access_token(str(user.id))
    headers = {"Authorization": f"Bearer {token}"}
    monkeypatch.setattr(
        "app.routers.documents.storage.presign_get_url",
        lambda key, expires=300: f"https://storage.example.com/{key}",
    )

    # 1. Non needs_review status -> 409
    doc_queued = create_seed_document(db, user, status="queued")
    r_queued = client.post(f"/api/v1/documents/{doc_queued.id}/approve", headers=headers)
    assert r_queued.status_code == 409
    assert r_queued.json()["error"]["code"] == "conflict"

    # 2. Needs review with blocking error issue -> 409 listing errors
    doc_blocked = create_seed_document(
        db,
        user,
        status="needs_review",
        issues=[
            {
                "rule": "invalid_gstin",
                "severity": "error",
                "field_name": "gstin",
                "message": "GSTIN does not match format",
            }
        ],
    )
    r_blocked = client.post(f"/api/v1/documents/{doc_blocked.id}/approve", headers=headers)
    assert r_blocked.status_code == 409
    assert r_blocked.json()["error"]["code"] == "conflict"
    assert "invalid_gstin" in r_blocked.json()["error"]["message"]

    # 3. Force approve with {"force": true} -> succeeds and sets approved + approved_at
    r_force = client.post(
        f"/api/v1/documents/{doc_blocked.id}/approve",
        headers=headers,
        json={"force": True},
    )
    assert r_force.status_code == 200
    approved_body = r_force.json()
    assert approved_body["status"] == "approved"

    # Verify DB has approved_at set
    db.refresh(doc_blocked)
    assert doc_blocked.status == "approved"
    assert doc_blocked.approved_at is not None


def test_unauthenticated_requests_rejected(client):
    r_list = client.get("/api/v1/documents")
    assert r_list.status_code == 401

    fake_id = uuid4()
    r_get = client.get(f"/api/v1/documents/{fake_id}")
    assert r_get.status_code == 401

    r_patch = client.patch(f"/api/v1/documents/{fake_id}/fields", json={"fields": {}})
    assert r_patch.status_code == 401

    r_approve = client.post(f"/api/v1/documents/{fake_id}/approve")
    assert r_approve.status_code == 401
