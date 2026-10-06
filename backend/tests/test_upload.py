from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from uuid import uuid4

from sqlalchemy.orm import Session

from app.models import Document, Job, User

PDF_BYTES = b"%PDF-1.7\n%test pdf\n"
JPEG_BYTES = b"\xff\xd8\xff\xe0jpeg-data"
PNG_BYTES = b"\x89PNG\r\n\x1a\npng-data"
EXE_BYTES = b"MZ fake executable"


class FakeTaskResult:
    id = "fake-task-id"


class FakeStorage:
    def __init__(self) -> None:
        self.puts: list[tuple[str, bytes, str]] = []
        self.deleted: list[str] = []

    def put_object(self, key: str, body: bytes, content_type: str) -> None:
        self.puts.append((key, body, content_type))

    def delete_object(self, key: str) -> None:
        self.deleted.append(key)


def register_and_login(client, email: str | None = None) -> tuple[str, str]:
    email = email or f"upload-{uuid4().hex}@example.test"
    password = "Password123"
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": "Upload User"},
    )
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return email, response.json()["access_token"]


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def upload_files(client, token: str, files: list[tuple[str, bytes, str]]):
    return client.post(
        "/api/v1/documents/upload",
        headers=auth_header(token),
        files=[("files", (filename, BytesIO(content), content_type)) for filename, content, content_type in files],
    )


def patch_upload_dependencies(monkeypatch):
    fake_storage = FakeStorage()

    monkeypatch.setattr("app.routers.documents.storage", fake_storage)
    monkeypatch.setattr(
        "app.routers.documents.process_document.delay",
        lambda document_id: FakeTaskResult(),
    )
    return fake_storage


def test_valid_pdf_jpg_png_uploads_are_queued(client, db: Session, monkeypatch) -> None:
    fake_storage = patch_upload_dependencies(monkeypatch)
    email, token = register_and_login(client)
    user_id = db.query(User.id).filter(User.email == email).scalar()

    response = upload_files(
        client,
        token,
        [
            ("invoice.pdf", PDF_BYTES, "application/octet-stream"),
            ("photo.bin", JPEG_BYTES, "application/octet-stream"),
            ("scan.dat", PNG_BYTES, "application/octet-stream"),
        ],
    )

    assert response.status_code == 200
    results = response.json()["results"]
    assert [result["status"] for result in results] == ["queued", "queued", "queued"]
    assert [put[2] for put in fake_storage.puts] == [
        "application/pdf",
        "image/jpeg",
        "image/png",
    ]
    assert db.query(Document).filter(Document.user_id == user_id, Document.status == "queued").count() == 3
    assert db.query(Job).join(Document).filter(Document.user_id == user_id, Job.status == "queued").count() == 3


def test_exact_duplicate_is_recorded_without_storage_or_job(client, db: Session, monkeypatch) -> None:
    fake_storage = patch_upload_dependencies(monkeypatch)
    email, token = register_and_login(client)
    user_id = db.query(User.id).filter(User.email == email).scalar()

    first = upload_files(client, token, [("invoice.pdf", PDF_BYTES, "application/pdf")])
    second = upload_files(client, token, [("invoice-copy.pdf", PDF_BYTES, "application/pdf")])

    original_id = first.json()["results"][0]["document_id"]
    duplicate = second.json()["results"][0]
    assert duplicate["status"] == "duplicate"
    assert duplicate["duplicate_of_id"] == original_id
    assert len(fake_storage.puts) == 1
    assert db.query(Document).filter(Document.user_id == user_id, Document.status != "duplicate").count() == 1
    assert db.query(Document).filter(Document.user_id == user_id, Document.status == "duplicate").count() == 1
    assert db.query(Job).join(Document).filter(Document.user_id == user_id).count() == 1


def test_renamed_exe_as_pdf_is_unsupported(client, monkeypatch) -> None:
    fake_storage = patch_upload_dependencies(monkeypatch)
    _, token = register_and_login(client)

    response = upload_files(client, token, [("renamed.pdf", EXE_BYTES, "application/pdf")])

    assert response.status_code == 200
    result = response.json()["results"][0]
    assert result["document_id"] is None
    assert result["status"] is None
    assert result["error"]["code"] == "unsupported_type"
    assert fake_storage.puts == []


def test_file_over_size_limit_returns_per_file_error(client, monkeypatch) -> None:
    patch_upload_dependencies(monkeypatch)
    monkeypatch.setattr("app.routers.documents.settings.max_file_size_mb", 0)
    _, token = register_and_login(client)

    response = upload_files(client, token, [("too-big.pdf", PDF_BYTES, "application/pdf")])

    assert response.status_code == 200
    result = response.json()["results"][0]
    assert result["error"]["code"] == "file_too_large"
    assert result["document_id"] is None


def test_too_many_files_returns_validation_error(client, monkeypatch) -> None:
    patch_upload_dependencies(monkeypatch)
    monkeypatch.setattr("app.routers.documents.settings.max_files_per_upload", 1)
    _, token = register_and_login(client)

    response = upload_files(
        client,
        token,
        [
            ("one.pdf", PDF_BYTES, "application/pdf"),
            ("two.pdf", PDF_BYTES + b"2", "application/pdf"),
        ],
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "validation_error"


def test_empty_file_is_unsupported(client, monkeypatch) -> None:
    patch_upload_dependencies(monkeypatch)
    _, token = register_and_login(client)

    response = upload_files(client, token, [("empty.pdf", b"", "application/pdf")])

    assert response.status_code == 200
    assert response.json()["results"][0]["error"]["code"] == "unsupported_type"


def test_filename_path_components_are_stripped(client, db: Session, monkeypatch) -> None:
    fake_storage = patch_upload_dependencies(monkeypatch)
    _, token = register_and_login(client)

    response = upload_files(client, token, [("../../x.pdf", PDF_BYTES, "application/pdf")])

    assert response.status_code == 200
    document = db.get(Document, response.json()["results"][0]["document_id"])
    assert document.filename == "x.pdf"
    assert "x.pdf" not in document.storage_key
    assert document.storage_key.startswith(f"users/{document.user_id}/")
    assert fake_storage.puts[0][0] == document.storage_key


def test_concurrent_same_file_upload_creates_one_primary_document(client, db: Session, monkeypatch) -> None:
    patch_upload_dependencies(monkeypatch)
    email, token = register_and_login(client)
    user_id = db.query(User.id).filter(User.email == email).scalar()

    def do_upload():
        return upload_files(client, token, [("race.pdf", PDF_BYTES, "application/pdf")]).json()

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: do_upload(), range(2)))

    statuses = [result["results"][0]["status"] for result in results]
    assert sorted(statuses) == ["duplicate", "queued"]
    assert db.query(Document).filter(Document.user_id == user_id, Document.status != "duplicate").count() == 1
    assert db.query(Document).filter(Document.user_id == user_id, Document.status == "duplicate").count() == 1


def test_same_bytes_from_different_users_are_not_duplicates(client, db: Session, monkeypatch) -> None:
    patch_upload_dependencies(monkeypatch)
    email_a, token_a = register_and_login(client, "user-a@example.test")
    email_b, token_b = register_and_login(client, "user-b@example.test")

    first = upload_files(client, token_a, [("invoice.pdf", PDF_BYTES, "application/pdf")])
    second = upload_files(client, token_b, [("invoice.pdf", PDF_BYTES, "application/pdf")])

    assert first.json()["results"][0]["status"] == "queued"
    assert second.json()["results"][0]["status"] == "queued"
    user_ids = db.query(User.id).filter(User.email.in_([email_a, email_b])).all()
    assert db.query(Document).filter(
        Document.user_id.in_([user_id for (user_id,) in user_ids]),
        Document.status != "duplicate",
    ).count() == 2


def test_upload_requires_auth(client, monkeypatch) -> None:
    patch_upload_dependencies(monkeypatch)

    response = client.post(
        "/api/v1/documents/upload",
        files=[("files", ("invoice.pdf", BytesIO(PDF_BYTES), "application/pdf"))],
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


def test_storage_key_does_not_contain_filename(client, db: Session, monkeypatch) -> None:
    patch_upload_dependencies(monkeypatch)
    _, token = register_and_login(client)

    response = upload_files(client, token, [("secret-name.pdf", PDF_BYTES, "application/pdf")])

    document = db.get(Document, response.json()["results"][0]["document_id"])
    assert "secret-name.pdf" not in document.storage_key
    assert document.storage_key.startswith(f"users/{document.user_id}/")
