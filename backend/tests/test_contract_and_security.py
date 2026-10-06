from __future__ import annotations

import concurrent.futures
import json
import os
import re
import time
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.auth.security import create_access_token, hash_password
from app.config import settings
from app.models import Document, ExtractedField, Job, LineItem, User, ValidationIssue
from app.services.storage import storage


# --- Helper: Fixture Paths and Shape Checker ---

def get_fixtures_dir() -> Path:
    candidates = [
        Path("/contracts/fixtures"),
        Path(__file__).resolve().parents[2] / "contracts" / "fixtures",
        Path(__file__).resolve().parents[1] / "contracts" / "fixtures",
        Path("contracts/fixtures").resolve(),
    ]
    for c in candidates:
        if c.exists() and c.is_dir():
            return c
    raise FileNotFoundError("Could not locate contracts/fixtures directory")


def load_fixture(name: str) -> Any:
    path = get_fixtures_dir() / name
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def assert_shape_matches(actual: Any, expected: Any, path: str = "root") -> None:
    """
    Recursively asserts that `actual` has the exact same keys and value types as `expected`.
    Allows None for nullable fields when expected is None or actual is None.
    Handles int/float compatibility for numeric fields.
    """
    if expected is None:
        # Fixture demonstrates nullable field (can be None or concrete value)
        return

    if actual is None:
        # Actual can be None if field is nullable
        return

    if isinstance(expected, dict):
        assert isinstance(actual, dict), f"At {path}: expected dict, got {type(actual).__name__}"
        assert set(actual.keys()) == set(expected.keys()), (
            f"At {path}: key mismatch.\n"
            f"Missing in actual: {set(expected.keys()) - set(actual.keys())}\n"
            f"Unexpected in actual: {set(actual.keys()) - set(expected.keys())}"
        )
        for key in expected:
            assert_shape_matches(actual[key], expected[key], f"{path}.{key}")

    elif isinstance(expected, list):
        assert isinstance(actual, list), f"At {path}: expected list, got {type(actual).__name__}"
        if expected and actual:
            template = expected[0]
            for i, item in enumerate(actual):
                assert_shape_matches(item, template, f"{path}[{i}]")

    elif isinstance(expected, bool):
        assert isinstance(actual, bool), f"At {path}: expected bool, got {type(actual).__name__}"

    elif isinstance(expected, (int, float)):
        assert isinstance(actual, (int, float)) and not isinstance(actual, bool), (
            f"At {path}: expected number, got {type(actual).__name__}"
        )

    elif isinstance(expected, str):
        assert isinstance(actual, str), f"At {path}: expected str, got {type(actual).__name__}"

    else:
        assert type(actual) is type(expected), (
            f"At {path}: type mismatch, expected {type(expected).__name__}, got {type(actual).__name__}"
        )


# --- Helper: User and Document Factories ---

def create_test_user(db: Session, prefix: str = "test") -> tuple[User, str]:
    email = f"{prefix}-{uuid4().hex[:8]}@example.test"
    user = User(
        email=email,
        password_hash=hash_password("Password123"),
        full_name=f"User {prefix}",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token(str(user.id))
    return user, token


def create_test_document(
    db: Session,
    user: User,
    status: str = "queued",
    filename: str = "test_invoice.pdf",
    duplicate_of: Document | None = None,
    with_fields: bool = False,
    with_job: bool = True,
    job_status: str = "succeeded",
    error_message: str | None = None,
) -> Document:
    storage_key = f"users/{user.id}/{uuid4()}"
    doc = Document(
        user_id=user.id,
        filename=filename,
        mime_type="application/pdf",
        size_bytes=1024,
        file_hash=uuid4().hex + uuid4().hex,
        storage_key=storage_key,
        status=status,
        auto_approved=(status == "approved"),
        duplicate_of_id=duplicate_of.id if duplicate_of else None,
        duplicate_reason="same_file" if duplicate_of else None,
        error_message=error_message,
    )
    db.add(doc)
    db.flush()

    if with_job and status != "duplicate":
        job = Job(
            document_id=doc.id,
            status=job_status,
            attempts=1 if job_status == "succeeded" else (3 if job_status == "failed" else 0),
            max_attempts=3,
            last_error="Test error" if job_status == "failed" else None,
        )
        db.add(job)

    if with_fields:
        fields_data = [
            ("vendor_name", "Acme Traders", Decimal("0.97"), False, {"page": 1, "x": 0.1, "y": 0.05, "w": 0.3, "h": 0.04}),
            ("invoice_number", "INV-001", Decimal("0.98"), False, None),
            ("invoice_date", "2026-10-01", Decimal("0.95"), False, None),
            ("gstin", "27ABCDE1234F1Z5", Decimal("0.62"), True, None),
            ("currency", "INR", Decimal("0.90"), False, None),
            ("subtotal", "10000.00", Decimal("0.96"), False, None),
            ("tax", "1800.00", Decimal("0.94"), False, None),
            ("total", "11800.00", Decimal("0.97"), False, None),
        ]
        for fname, val, conf, nr, bbox in fields_data:
            db.add(
                ExtractedField(
                    document_id=doc.id,
                    field_name=fname,
                    value=val,
                    confidence=conf,
                    needs_review=nr,
                    bbox=bbox,
                )
            )

        db.add(
            LineItem(
                document_id=doc.id,
                position=1,
                description="Steel rods",
                quantity=Decimal("10.000"),
                rate=Decimal("1000.00"),
                amount=Decimal("10000.00"),
                confidence=Decimal("0.95"),
            )
        )

        if status == "needs_review":
            db.add(
                ValidationIssue(
                    document_id=doc.id,
                    rule="total_mismatch",
                    severity="error",
                    field_name="total",
                    message="Total mismatch detected",
                )
            )

    db.commit()
    db.refresh(doc)
    return doc


# =====================================================================
# AREA 1: CONTRACT SHAPE TESTS
# =====================================================================

def test_contract_fixture_files_all_loaded_and_accounted_for() -> None:
    fixtures_dir = get_fixtures_dir()
    fixture_files = set(os.listdir(fixtures_dir))
    expected_files = {
        "auth_login.json",
        "documents_list.json",
        "document_detail_needs_review.json",
        "document_detail_approved.json",
        "document_detail_failed.json",
        "document_detail_duplicate.json",
        "upload_response.json",
    }
    assert expected_files.issubset(fixture_files), f"Missing fixtures: {expected_files - fixture_files}"


def test_auth_login_contract_shape(client: TestClient, db: Session) -> None:
    expected = load_fixture("auth_login.json")
    user, _ = create_test_user(db, prefix="auth-shape")

    res = client.post(
        "/api/v1/auth/login",
        json={"email": user.email, "password": "Password123"},
    )
    assert res.status_code == 200
    actual = res.json()
    assert_shape_matches(actual, expected)


def test_documents_list_contract_shape(client: TestClient, db: Session) -> None:
    expected = load_fixture("documents_list.json")
    user, token = create_test_user(db, prefix="list-shape")

    # Seed one doc of each status
    create_test_document(db, user, status="approved", with_fields=True)
    create_test_document(db, user, status="needs_review", with_fields=True)
    create_test_document(db, user, status="failed", job_status="failed")
    create_test_document(db, user, status="processing", job_status="processing")
    orig = create_test_document(db, user, status="approved")
    create_test_document(db, user, status="duplicate", duplicate_of=orig)

    res = client.get(
        "/api/v1/documents",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    actual = res.json()
    assert_shape_matches(actual, expected)


def test_document_detail_needs_review_contract_shape(client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    expected = load_fixture("document_detail_needs_review.json")
    user, token = create_test_user(db, prefix="detail-nr")
    doc = create_test_document(db, user, status="needs_review", with_fields=True)

    monkeypatch.setattr(storage, "presign_get_url", lambda key: f"https://storage.example.com/presigned/{key}")

    res = client.get(
        f"/api/v1/documents/{doc.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    actual = res.json()
    assert_shape_matches(actual, expected)


def test_document_detail_approved_contract_shape(client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    expected = load_fixture("document_detail_approved.json")
    user, token = create_test_user(db, prefix="detail-appr")
    doc = create_test_document(db, user, status="approved", with_fields=True)

    monkeypatch.setattr(storage, "presign_get_url", lambda key: f"https://storage.example.com/presigned/{key}")

    res = client.get(
        f"/api/v1/documents/{doc.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    actual = res.json()
    assert_shape_matches(actual, expected)


def test_document_detail_failed_contract_shape(client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    expected = load_fixture("document_detail_failed.json")
    user, token = create_test_user(db, prefix="detail-fail")
    doc = create_test_document(
        db, user, status="failed", job_status="failed", error_message="Extractor failed after 3 attempts"
    )

    monkeypatch.setattr(storage, "presign_get_url", lambda key: f"https://storage.example.com/presigned/{key}")

    res = client.get(
        f"/api/v1/documents/{doc.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    actual = res.json()
    assert_shape_matches(actual, expected)


def test_document_detail_duplicate_contract_shape(client: TestClient, db: Session) -> None:
    expected = load_fixture("document_detail_duplicate.json")
    user, token = create_test_user(db, prefix="detail-dup")
    primary = create_test_document(db, user, status="approved")
    doc = create_test_document(db, user, status="duplicate", duplicate_of=primary)

    res = client.get(
        f"/api/v1/documents/{doc.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    actual = res.json()
    assert_shape_matches(actual, expected)


def test_upload_response_contract_shape(client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    expected = load_fixture("upload_response.json")
    user, token = create_test_user(db, prefix="upload-shape")

    pdf_bytes = b"%PDF-1.4 sample content"
    monkeypatch.setattr("app.routers.documents.enqueue_document_processing", lambda *args, **kwargs: None)

    # First upload to establish primary
    res1 = client.post(
        "/api/v1/documents/upload",
        files=[("files", ("invoice.pdf", pdf_bytes, "application/pdf"))],
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res1.status_code == 200

    # Multi-file upload: new PDF, copy of previous PDF, and invalid EXE
    pdf2_bytes = b"%PDF-1.4 second invoice"
    res2 = client.post(
        "/api/v1/documents/upload",
        files=[
            ("files", ("clean_invoice.pdf", pdf2_bytes, "application/pdf")),
            ("files", ("clean_invoice_copy.pdf", pdf_bytes, "application/pdf")),
            ("files", ("notes.exe", b"MZ\x90\x00not a valid pdf", "application/octet-stream")),
        ],
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res2.status_code == 200
    actual = res2.json()
    assert_shape_matches(actual, expected)


# =====================================================================
# AREA 2: STATUS MACHINE TRANSITIONS
# =====================================================================

@pytest.mark.parametrize("invalid_status", ["queued", "processing", "approved", "failed", "duplicate"])
def test_approve_rejected_from_invalid_statuses(client: TestClient, db: Session, invalid_status: str) -> None:
    user, token = create_test_user(db, prefix=f"st-appr-{invalid_status}")
    doc = create_test_document(db, user, status=invalid_status)

    res = client.post(
        f"/api/v1/documents/{doc.id}/approve",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 409
    assert res.json()["error"]["code"] == "conflict"


def test_approve_succeeds_from_needs_review_without_blocking_errors(client: TestClient, db: Session) -> None:
    user, token = create_test_user(db, prefix="appr-ok")
    doc = create_test_document(db, user, status="needs_review", with_fields=False)

    res = client.post(
        f"/api/v1/documents/{doc.id}/approve",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    assert res.json()["status"] == "approved"


def test_approve_from_needs_review_with_blocking_errors_requires_force(client: TestClient, db: Session) -> None:
    user, token = create_test_user(db, prefix="appr-force")
    doc = create_test_document(db, user, status="needs_review", with_fields=True)  # has error issue

    # Without force -> 409
    res = client.post(
        f"/api/v1/documents/{doc.id}/approve",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 409
    assert res.json()["error"]["code"] == "conflict"

    # With force=True -> 200
    res_force = client.post(
        f"/api/v1/documents/{doc.id}/approve",
        json={"force": True},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_force.status_code == 200
    assert res_force.json()["status"] == "approved"


@pytest.mark.parametrize("invalid_status", ["approved", "queued", "processing", "failed", "duplicate"])
def test_patch_fields_rejected_from_invalid_statuses(client: TestClient, db: Session, invalid_status: str) -> None:
    user, token = create_test_user(db, prefix=f"st-ptch-{invalid_status}")
    doc = create_test_document(db, user, status=invalid_status)

    res = client.patch(
        f"/api/v1/documents/{doc.id}/fields",
        json={"fields": {"total": "11800.00"}},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 409
    assert res.json()["error"]["code"] == "conflict"


def test_patch_fields_succeeds_from_needs_review(client: TestClient, db: Session) -> None:
    user, token = create_test_user(db, prefix="ptch-ok")
    doc = create_test_document(db, user, status="needs_review", with_fields=True)

    res = client.patch(
        f"/api/v1/documents/{doc.id}/fields",
        json={"fields": {"total": "11800.00"}},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    body = res.json()
    field = next(f for f in body["fields"] if f["field_name"] == "total")
    assert field["reviewed_value"] == "11800.00"
    assert field["needs_review"] is False


@pytest.mark.parametrize("invalid_status", ["queued", "processing", "needs_review", "approved", "duplicate"])
def test_retry_rejected_from_invalid_statuses(client: TestClient, db: Session, invalid_status: str) -> None:
    user, token = create_test_user(db, prefix=f"st-rtry-{invalid_status}")
    doc = create_test_document(db, user, status=invalid_status)

    res = client.post(
        f"/api/v1/documents/{doc.id}/retry",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 409
    assert res.json()["error"]["code"] == "conflict"


def test_retry_succeeds_from_failed(client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    user, token = create_test_user(db, prefix="rtry-ok")
    doc = create_test_document(db, user, status="failed", job_status="failed")

    monkeypatch.setattr("app.routers.documents.process_document.delay", lambda *args, **kwargs: type("Task", (), {"id": "fake-task"})())

    res = client.post(
        f"/api/v1/documents/{doc.id}/retry",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "queued"
    assert body["job"]["status"] == "queued"
    assert body["job"]["attempts"] == 0


# =====================================================================
# AREA 3: AUTHORIZATION & CROSS-USER ISOLATION
# =====================================================================

def test_document_endpoints_return_404_for_other_users_document(client: TestClient, db: Session) -> None:
    user_a, _ = create_test_user(db, prefix="user-a")
    user_b, token_b = create_test_user(db, prefix="user-b")
    doc_a = create_test_document(db, user_a, status="needs_review", with_fields=True)

    headers_b = {"Authorization": f"Bearer {token_b}"}

    # GET
    res_get = client.get(f"/api/v1/documents/{doc_a.id}", headers=headers_b)
    assert res_get.status_code == 404
    assert res_get.json()["error"]["code"] == "not_found"

    # PATCH
    res_patch = client.patch(
        f"/api/v1/documents/{doc_a.id}/fields",
        json={"fields": {"total": "100.00"}},
        headers=headers_b,
    )
    assert res_patch.status_code == 404
    assert res_patch.json()["error"]["code"] == "not_found"

    # POST approve
    res_appr = client.post(f"/api/v1/documents/{doc_a.id}/approve", headers=headers_b)
    assert res_appr.status_code == 404
    assert res_appr.json()["error"]["code"] == "not_found"

    # POST retry (even if doc_a were failed)
    doc_a.status = "failed"
    db.commit()
    res_retry = client.post(f"/api/v1/documents/{doc_a.id}/retry", headers=headers_b)
    assert res_retry.status_code == 404
    assert res_retry.json()["error"]["code"] == "not_found"


def test_export_endpoint_hides_other_users_documents(client: TestClient, db: Session) -> None:
    user_a, _ = create_test_user(db, prefix="exp-a")
    user_b, token_b = create_test_user(db, prefix="exp-b")
    doc_a = create_test_document(db, user_a, status="approved", with_fields=True)

    res = client.get(
        f"/api/v1/export?format=json&ids={doc_a.id}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert res.status_code == 200
    assert res.json() == []


def test_protected_endpoints_return_401_without_token(client: TestClient) -> None:
    random_id = str(uuid4())
    protected_calls = [
        ("GET", "/api/v1/auth/me", None, None),
        ("POST", "/api/v1/documents/upload", None, None),
        ("GET", "/api/v1/documents", None, None),
        ("GET", f"/api/v1/documents/{random_id}", None, None),
        ("PATCH", f"/api/v1/documents/{random_id}/fields", {"fields": {}}, None),
        ("POST", f"/api/v1/documents/{random_id}/approve", None, None),
        ("POST", f"/api/v1/documents/{random_id}/retry", None, None),
        ("GET", "/api/v1/export?format=csv", None, None),
    ]

    for method, path, json_body, files in protected_calls:
        if method == "GET":
            res = client.get(path)
        elif method == "POST":
            res = client.post(path, json=json_body, files=files)
        elif method == "PATCH":
            res = client.patch(path, json=json_body)
        else:
            raise ValueError(f"Unsupported method: {method}")

        assert res.status_code == 401, f"{method} {path} returned {res.status_code}, expected 401"
        body = res.json()
        assert "error" in body
        assert body["error"]["code"] == "unauthorized"


def test_protected_endpoints_return_401_with_invalid_token(client: TestClient) -> None:
    headers = {"Authorization": "Bearer invalid.malformed.token"}
    res = client.get("/api/v1/documents", headers=headers)
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "unauthorized"


# =====================================================================
# AREA 4: FILE SECURITY
# =====================================================================

def test_presigned_url_expires(client: TestClient, db: Session) -> None:
    user, _ = create_test_user(db, prefix="presign-exp")
    test_key = f"users/{user.id}/presign-test-{uuid4()}"
    test_bytes = b"%PDF-1.4 presigned expiry test"

    storage.put_object(test_key, test_bytes, "application/pdf")
    try:
        # Generate presigned URL with 1-second expiry
        url = storage.presign_get_url(test_key, expires=1)

        # Immediate fetch should work
        immediate_resp = httpx.get(url)
        assert immediate_resp.status_code == 200
        assert immediate_resp.content == test_bytes

        # Wait for expiration
        time.sleep(2.5)

        # Expired fetch must fail with 403 Forbidden
        expired_resp = httpx.get(url)
        assert expired_resp.status_code == 403
    finally:
        storage.delete_object(test_key)


def test_storage_keys_never_contain_filename_or_traversal(client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    user, token = create_test_user(db, prefix="key-leak")
    monkeypatch.setattr("app.routers.documents.enqueue_document_processing", lambda *args, **kwargs: None)

    weird_filenames = [
        "top_secret_payroll_records.pdf",
        "../../../../etc/passwd.pdf",
        "invoice #123 & (final).pdf",
    ]

    for fname in weird_filenames:
        content = f"%PDF-1.4 content {uuid4()}".encode("utf-8")
        res = client.post(
            "/api/v1/documents/upload",
            files=[("files", (fname, content, "application/pdf"))],
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200
        doc_id = res.json()["results"][0]["document_id"]
        doc = db.query(Document).filter(Document.id == UUID(doc_id)).first()
        assert doc is not None

        # Filename must NOT appear in storage_key
        assert "payroll" not in doc.storage_key
        assert "passwd" not in doc.storage_key
        assert "invoice" not in doc.storage_key
        assert "etc" not in doc.storage_key

        # Storage key strictly conforms to: users/<user_id>/<uuid>
        pattern = rf"^users/{user.id}/[0-9a-f-]{{36}}$"
        assert re.match(pattern, doc.storage_key) is not None, f"Key {doc.storage_key} does not match {pattern}"


def test_storage_bucket_denies_anonymous_access(client: TestClient, db: Session) -> None:
    user, _ = create_test_user(db, prefix="anon-s3")
    key = f"users/{user.id}/anon-test-{uuid4()}"
    content = b"%PDF-1.4 sensitive content"
    storage.put_object(key, content, "application/pdf")

    try:
        raw_url = f"{settings.s3_endpoint_url.rstrip('/')}/{settings.s3_bucket}/{key}"
        res = httpx.get(raw_url)
        # MinIO/S3 private bucket denies unauthenticated direct requests
        assert res.status_code == 403
    finally:
        storage.delete_object(key)


def test_upload_rejects_renamed_executables(client: TestClient, db: Session) -> None:
    user, token = create_test_user(db, prefix="exe-sniff")

    malicious_payloads = [
        ("invoice.pdf", b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff"),  # Windows PE
        ("photo.jpg", b"\x7fELF\x02\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00"),  # Linux ELF
        ("scan.png", b"\xfe\xed\xfa\xce\x00\x00\x00\x00"),  # Mach-O
    ]

    for filename, payload in malicious_payloads:
        res = client.post(
            "/api/v1/documents/upload",
            files=[("files", (filename, payload, "application/pdf"))],
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200
        result = res.json()["results"][0]
        assert result["document_id"] is None
        assert result["status"] is None
        assert result["error"] == {
            "code": "unsupported_type",
            "message": "Only PDF, JPG, PNG allowed",
        }


# =====================================================================
# AREA 5: ERROR FORMAT & NO TRACEBACKS
# =====================================================================

def test_http_errors_match_contract_format_and_no_traceback(client: TestClient, db: Session) -> None:
    user, token = create_test_user(db, prefix="err-fmt")
    headers = {"Authorization": f"Bearer {token}"}

    # 404
    r404 = client.get(f"/api/v1/documents/{uuid4()}", headers=headers)
    assert r404.status_code == 404
    _verify_error_response(r404, expected_code="not_found")

    # 401
    r401 = client.get("/api/v1/documents")
    assert r401.status_code == 401
    _verify_error_response(r401, expected_code="unauthorized")

    # 409
    doc = create_test_document(db, user, status="approved")
    r409 = client.post(f"/api/v1/documents/{doc.id}/approve", headers=headers)
    assert r409.status_code == 409
    _verify_error_response(r409, expected_code="conflict")

    # 422
    r422 = client.post("/api/v1/auth/register", json={"email": "invalid-email", "password": "short"})
    assert r422.status_code == 422
    _verify_error_response(r422, expected_code="validation_error")

    # 400
    files = [("files", (f"file_{i}.pdf", b"%PDF-1.4", "application/pdf")) for i in range(21)]
    r400 = client.post("/api/v1/documents/upload", files=files, headers=headers)
    assert r400.status_code == 400
    _verify_error_response(r400, expected_code="validation_error")


def test_file_size_and_type_per_file_errors_match_format(client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    user, token = create_test_user(db, prefix="per-file-err")
    headers = {"Authorization": f"Bearer {token}"}

    monkeypatch.setattr(settings, "max_file_size_mb", 1)
    large_pdf = b"%PDF-1.4 " + (b"0" * (1024 * 1024 + 10))

    res = client.post(
        "/api/v1/documents/upload",
        files=[("files", ("big.pdf", large_pdf, "application/pdf"))],
        headers=headers,
    )
    assert res.status_code == 200
    result = res.json()["results"][0]
    assert result["error"] is not None
    assert result["error"]["code"] == "file_too_large"
    assert "exceeds" in result["error"]["message"].lower()


def test_internal_server_error_matches_contract_format_and_no_traceback(monkeypatch: pytest.MonkeyPatch) -> None:
    # Trigger an unexpected exception in an endpoint to test 500 handler
    from app.main import app
    client = TestClient(app, raise_server_exceptions=False)

    def boom(*args, **kwargs):
        raise RuntimeError("Simulated unhandled internal server error")

    monkeypatch.setattr("app.routers.auth.normalize_email", boom)

    res = client.post("/api/v1/auth/login", json={"email": "test@example.com", "password": "Password123"})
    assert res.status_code == 500
    _verify_error_response(res, expected_code="internal_error")


def _verify_error_response(response, expected_code: str) -> None:
    raw_text = response.text
    # No stack trace signatures
    assert "Traceback (most recent call last)" not in raw_text
    assert 'File "' not in raw_text
    assert "Exception:" not in raw_text

    data = response.json()
    assert "error" in data, f"Response missing 'error' key: {data}"
    err = data["error"]
    assert set(err.keys()) == {"code", "message"}, f"Error keys mismatch: {set(err.keys())}"
    assert err["code"] == expected_code
    assert isinstance(err["message"], str)
    assert len(err["message"]) > 0


# =====================================================================
# AREA 6: IDEMPOTENCY
# =====================================================================

def test_sequential_upload_idempotency_creates_one_primary_and_one_duplicate(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    user, token = create_test_user(db, prefix="idemp-seq")
    headers = {"Authorization": f"Bearer {token}"}
    monkeypatch.setattr("app.routers.documents.enqueue_document_processing", lambda *args, **kwargs: None)

    file_bytes = b"%PDF-1.4 sequential idempotency test payload"

    # 1st upload
    res1 = client.post(
        "/api/v1/documents/upload",
        files=[("files", ("invoice_primary.pdf", file_bytes, "application/pdf"))],
        headers=headers,
    )
    assert res1.status_code == 200
    item1 = res1.json()["results"][0]
    assert item1["status"] == "queued"
    assert item1["duplicate_of_id"] is None
    primary_id = item1["document_id"]

    # 2nd upload with identical bytes
    res2 = client.post(
        "/api/v1/documents/upload",
        files=[("files", ("invoice_duplicate.pdf", file_bytes, "application/pdf"))],
        headers=headers,
    )
    assert res2.status_code == 200
    item2 = res2.json()["results"][0]
    assert item2["status"] == "duplicate"
    assert item2["duplicate_of_id"] == primary_id

    # Verify database state
    docs = db.query(Document).filter(Document.user_id == user.id).all()
    assert len(docs) == 2
    primary = next(d for d in docs if d.status != "duplicate")
    duplicate = next(d for d in docs if d.status == "duplicate")

    assert str(primary.id) == primary_id
    assert duplicate.duplicate_of_id == primary.id
    assert duplicate.storage_key == primary.storage_key


def test_concurrent_upload_race_creates_single_primary_and_n_duplicates(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    user, token = create_test_user(db, prefix="idemp-race")
    headers = {"Authorization": f"Bearer {token}"}
    monkeypatch.setattr("app.routers.documents.enqueue_document_processing", lambda *args, **kwargs: None)

    file_bytes = f"%PDF-1.4 concurrent race payload {uuid4()}".encode("utf-8")
    num_concurrent = 6

    def upload_one(index: int) -> dict:
        r = client.post(
            "/api/v1/documents/upload",
            files=[("files", (f"concurrent_{index}.pdf", file_bytes, "application/pdf"))],
            headers=headers,
        )
        assert r.status_code == 200, f"Upload {index} failed: {r.text}"
        return r.json()["results"][0]

    with concurrent.futures.ThreadPoolExecutor(max_workers=num_concurrent) as executor:
        results = list(executor.map(upload_one, range(num_concurrent)))

    primary_results = [r for r in results if r["status"] == "queued"]
    duplicate_results = [r for r in results if r["status"] == "duplicate"]

    assert len(primary_results) == 1, f"Expected 1 primary, got {len(primary_results)}"
    assert len(duplicate_results) == num_concurrent - 1

    primary_id = primary_results[0]["document_id"]
    for dup in duplicate_results:
        assert dup["duplicate_of_id"] == primary_id

    # Verify DB consistency
    docs = db.query(Document).filter(Document.user_id == user.id).all()
    assert len(docs) == num_concurrent
    primaries = [d for d in docs if d.status != "duplicate"]
    duplicates = [d for d in docs if d.status == "duplicate"]

    assert len(primaries) == 1
    assert len(duplicates) == num_concurrent - 1
    for d in duplicates:
        assert str(d.duplicate_of_id) == primary_id
