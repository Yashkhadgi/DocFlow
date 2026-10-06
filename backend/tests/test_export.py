from __future__ import annotations

import csv
from datetime import datetime, timezone
from decimal import Decimal
import io
import json
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.auth.security import create_access_token, hash_password
from app.models import Document, ExtractedField, LineItem, User
from app.services.export_service import CSV_HEADERS


def create_test_user(db: Session, email_prefix: str = "export-user") -> tuple[User, str]:
    email = f"{email_prefix}-{uuid4().hex[:8]}@example.com"
    user = User(
        email=email,
        password_hash=hash_password("Password123"),
        full_name="Export User",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token(subject=str(user.id))
    return user, token


def create_test_document(
    db: Session,
    user: User,
    filename: str = "invoice.pdf",
    status: str = "approved",
    fields: dict[str, tuple[str | None, str | None]] | None = None,
    line_items: list[dict] | None = None,
) -> Document:
    doc = Document(
        user_id=user.id,
        filename=filename,
        mime_type="application/pdf",
        size_bytes=1024,
        file_hash=uuid4().hex,
        storage_key=f"users/{user.id}/{uuid4()}",
        status=status,
    )
    db.add(doc)
    db.flush()

    if fields:
        for fname, (val, rev_val) in fields.items():
            db.add(
                ExtractedField(
                    document_id=doc.id,
                    field_name=fname,
                    value=val,
                    reviewed_value=rev_val,
                    confidence=Decimal("0.95"),
                )
            )

    if line_items is not None:
        for item in line_items:
            db.add(
                LineItem(
                    document_id=doc.id,
                    position=item.get("position", 1),
                    description=item.get("description"),
                    quantity=Decimal(str(item["quantity"])) if item.get("quantity") is not None else None,
                    rate=Decimal(str(item["rate"])) if item.get("rate") is not None else None,
                    amount=Decimal(str(item["amount"])) if item.get("amount") is not None else None,
                )
            )

    db.commit()
    db.refresh(doc)
    return doc


def test_export_requires_format_query_param(client: TestClient, db: Session) -> None:
    _user, token = create_test_user(db)
    response = client.get("/api/v1/export", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 422


def test_export_invalid_format_returns_422(client: TestClient, db: Session) -> None:
    _user, token = create_test_user(db)
    response = client.get("/api/v1/export?format=xml", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 422


def test_export_csv_headers_and_order(client: TestClient, db: Session) -> None:
    user, token = create_test_user(db)
    create_test_document(db, user, filename="empty_doc.pdf", status="approved")

    response = client.get("/api/v1/export?format=csv", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert "text/csv" in response.headers["Content-Type"]

    today_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    assert f'filename="docflow_export_{today_str}.csv"' in response.headers["Content-Disposition"]

    reader = list(csv.reader(io.StringIO(response.text)))
    assert len(reader) >= 1
    assert reader[0] == CSV_HEADERS


def test_export_multiple_line_items(client: TestClient, db: Session) -> None:
    user, token = create_test_user(db)
    doc = create_test_document(
        db,
        user,
        filename="multi_items.pdf",
        status="approved",
        fields={
            "vendor_name": ("Acme Corp", None),
            "invoice_number": ("INV-100", None),
            "total": ("1500.00", None),
        },
        line_items=[
            {"position": 1, "description": "Item A", "quantity": 2, "rate": 500, "amount": 1000},
            {"position": 2, "description": "Item B", "quantity": 1, "rate": 500, "amount": 500},
        ],
    )

    response = client.get(
        f"/api/v1/export?format=csv&ids={doc.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200

    reader = list(csv.reader(io.StringIO(response.text)))
    # 1 header row + 2 line item rows = 3 rows
    assert len(reader) == 3

    row1 = reader[1]
    assert row1[0] == str(doc.id)
    assert row1[1] == "multi_items.pdf"
    assert row1[2] == "Acme Corp"
    assert row1[3] == "INV-100"
    assert row1[9] == "1500.00"
    assert row1[10] == "1"
    assert row1[11] == "Item A"
    assert row1[12] == "2.000"
    assert row1[13] == "500.00"
    assert row1[14] == "1000.00"

    row2 = reader[2]
    assert row2[0] == str(doc.id)
    assert row2[10] == "2"
    assert row2[11] == "Item B"
    assert row2[14] == "500.00"


def test_export_no_line_items_yields_one_row_with_empty_items(client: TestClient, db: Session) -> None:
    user, token = create_test_user(db)
    doc = create_test_document(
        db,
        user,
        filename="no_items.pdf",
        status="approved",
        fields={"vendor_name": ("Solo Vendor", None)},
        line_items=[],
    )

    response = client.get(
        f"/api/v1/export?format=csv&ids={doc.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200

    reader = list(csv.reader(io.StringIO(response.text)))
    # 1 header + 1 row with empty line items
    assert len(reader) == 2

    row = reader[1]
    assert row[0] == str(doc.id)
    assert row[1] == "no_items.pdf"
    assert row[2] == "Solo Vendor"
    # item columns: item_position, item_description, item_quantity, item_rate, item_amount
    assert row[10] == ""
    assert row[11] == ""
    assert row[12] == ""
    assert row[13] == ""
    assert row[14] == ""


def test_export_reviewed_value_precedence(client: TestClient, db: Session) -> None:
    user, token = create_test_user(db)
    doc = create_test_document(
        db,
        user,
        filename="reviewed.pdf",
        status="approved",
        fields={
            "vendor_name": ("Old Extracted Name", "Corrected Vendor Name"),
            "invoice_number": ("INV-OLD", "INV-CORRECTED"),
            "total": ("999.00", None),  # reviewed_value is None -> should use value
        },
        line_items=[],
    )

    # Test CSV
    response_csv = client.get(
        f"/api/v1/export?format=csv&ids={doc.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response_csv.status_code == 200
    reader = list(csv.reader(io.StringIO(response_csv.text)))
    row = reader[1]
    assert row[2] == "Corrected Vendor Name"
    assert row[3] == "INV-CORRECTED"
    assert row[9] == "999.00"

    # Test JSON
    response_json = client.get(
        f"/api/v1/export?format=json&ids={doc.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response_json.status_code == 200
    data = response_json.json()
    assert len(data) == 1
    assert data[0]["fields"]["vendor_name"] == "Corrected Vendor Name"
    assert data[0]["fields"]["invoice_number"] == "INV-CORRECTED"
    assert data[0]["fields"]["total"] == "999.00"


def test_export_quotes_commas_and_newlines_in_descriptions(client: TestClient, db: Session) -> None:
    user, token = create_test_user(db)
    complex_desc = 'Heavy Duty "Steel" Rods, Grade-A\nBatch #104'
    doc = create_test_document(
        db,
        user,
        filename="complex_desc.pdf",
        status="approved",
        fields={"vendor_name": ("Special Steel Ltd", None)},
        line_items=[
            {"position": 1, "description": complex_desc, "quantity": 10, "rate": 100, "amount": 1000}
        ],
    )

    response = client.get(
        f"/api/v1/export?format=csv&ids={doc.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200

    reader = list(csv.reader(io.StringIO(response.text)))
    assert len(reader) == 2
    row = reader[1]
    # Check that csv module properly quoted and read the complex string back
    assert row[11] == complex_desc


def test_export_csv_injection_protection(client: TestClient, db: Session) -> None:
    user, token = create_test_user(db)
    doc = create_test_document(
        db,
        user,
        filename="injection.pdf",
        status="approved",
        fields={
            "vendor_name": ("=cmd|' /C calc'!A0", None),
            "invoice_number": ("@secret_val", None),
            "currency": ("+USD", None),
            "total": ("-500.00", None),
        },
        line_items=[
            {"position": 1, "description": "=1+1", "quantity": 1, "rate": 10, "amount": 10}
        ],
    )

    response = client.get(
        f"/api/v1/export?format=csv&ids={doc.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200

    reader = list(csv.reader(io.StringIO(response.text)))
    row = reader[1]

    # All cells starting with =, +, -, @ must be prefixed with a single quote
    assert row[2] == "'=cmd|' /C calc'!A0"
    assert row[3] == "'@secret_val"
    assert row[6] == "'+USD"
    assert row[9] == "'-500.00"
    assert row[11] == "'=1+1"


def test_export_status_filter(client: TestClient, db: Session) -> None:
    user, token = create_test_user(db)
    doc_approved = create_test_document(db, user, filename="app.pdf", status="approved")
    doc_review = create_test_document(db, user, filename="rev.pdf", status="needs_review")

    # Default is approved
    resp_default = client.get("/api/v1/export?format=json", headers={"Authorization": f"Bearer {token}"})
    assert resp_default.status_code == 200
    ids_default = [d["document_id"] for d in resp_default.json()]
    assert str(doc_approved.id) in ids_default
    assert str(doc_review.id) not in ids_default

    # Explicit status=needs_review
    resp_review = client.get(
        "/api/v1/export?format=json&status=needs_review",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp_review.status_code == 200
    ids_review = [d["document_id"] for d in resp_review.json()]
    assert str(doc_review.id) in ids_review
    assert str(doc_approved.id) not in ids_review


def test_export_ignores_other_users_ids(client: TestClient, db: Session) -> None:
    user_a, token_a = create_test_user(db, email_prefix="user-a")
    user_b, _ = create_test_user(db, email_prefix="user-b")

    doc_a = create_test_document(db, user_a, filename="doc_a.pdf", status="approved")
    doc_b = create_test_document(db, user_b, filename="doc_b.pdf", status="approved")

    # User A requests both their doc and User B's doc
    response = client.get(
        f"/api/v1/export?format=json&ids={doc_a.id},{doc_b.id}",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert response.status_code == 200
    data = response.json()
    exported_ids = [d["document_id"] for d in data]

    assert str(doc_a.id) in exported_ids
    assert str(doc_b.id) not in exported_ids


def test_export_json_structure(client: TestClient, db: Session) -> None:
    user, token = create_test_user(db)
    doc = create_test_document(
        db,
        user,
        filename="json_test.pdf",
        status="approved",
        fields={
            "vendor_name": ("Global Tech", None),
            "invoice_number": ("GT-99", None),
            "total": ("250.00", None),
        },
        line_items=[
            {"position": 1, "description": "Consulting", "quantity": 2, "rate": 125, "amount": 250}
        ],
    )

    response = client.get(
        f"/api/v1/export?format=json&ids={doc.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert "application/json" in response.headers["Content-Type"]

    today_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    assert f'filename="docflow_export_{today_str}.json"' in response.headers["Content-Disposition"]

    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    doc_data = data[0]

    assert set(doc_data.keys()) == {"document_id", "filename", "fields", "line_items"}
    assert doc_data["document_id"] == str(doc.id)
    assert doc_data["filename"] == "json_test.pdf"
    assert doc_data["fields"]["vendor_name"] == "Global Tech"
    assert doc_data["fields"]["invoice_number"] == "GT-99"
    assert doc_data["fields"]["total"] == "250.00"

    assert len(doc_data["line_items"]) == 1
    item = doc_data["line_items"][0]
    assert item["position"] == 1
    assert item["description"] == "Consulting"
    assert item["quantity"] == "2.000"
    assert item["rate"] == "125.00"
    assert item["amount"] == "250.00"
