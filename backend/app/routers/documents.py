from __future__ import annotations

from hashlib import sha256
from pathlib import PurePath
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.security import get_current_user
from app.config import settings
from app.db import get_db
from app.models import Document, Job, User
from app.services.storage import storage
from app.workers.tasks import process_document

router = APIRouter(prefix="/documents", tags=["documents"])

CHUNK_SIZE = 1024 * 1024
MAGIC_BYTES: tuple[tuple[bytes, str], ...] = (
    (b"%PDF", "application/pdf"),
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"\x89PNG\r\n\x1a\n", "image/png"),
)


@router.post("/upload")
async def upload_documents(
    files: Annotated[list[UploadFile], File(...)],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, list[dict]]:
    if len(files) > settings.max_files_per_upload:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Maximum {settings.max_files_per_upload} files per upload",
        )

    results = []
    for upload in files:
        filename = sanitize_filename(upload.filename)
        result = await handle_one_upload(db, current_user, upload, filename)
        results.append(result)

    return {"results": results}


async def handle_one_upload(
    db: Session,
    current_user: User,
    upload: UploadFile,
    filename: str,
) -> dict:
    read_result = await read_limited_file(upload)
    if read_result["error"] is not None:
        return upload_result(filename, error=read_result["error"])

    file_bytes: bytes = read_result["bytes"]
    mime_type = sniff_mime_type(file_bytes)
    if mime_type is None:
        return upload_result(
            filename,
            error={"code": "unsupported_type", "message": "Only PDF, JPG, PNG allowed"},
        )

    file_hash = sha256(file_bytes).hexdigest()
    existing = find_existing_primary_document(db, current_user.id, file_hash)
    if existing is not None:
        duplicate = create_duplicate_document(db, current_user, filename, mime_type, len(file_bytes), file_hash, existing)
        return upload_result(
            filename,
            document_id=str(duplicate.id),
            status="duplicate",
            duplicate_of_id=str(existing.id),
        )

    storage_key = f"users/{current_user.id}/{uuid4()}"
    storage.put_object(storage_key, file_bytes, mime_type)

    document = Document(
        user_id=current_user.id,
        filename=filename,
        mime_type=mime_type,
        size_bytes=len(file_bytes),
        file_hash=file_hash,
        storage_key=storage_key,
        status="queued",
    )
    db.add(document)

    try:
        db.flush()
        job = Job(document_id=document.id, status="queued", max_attempts=settings.job_max_attempts)
        db.add(job)
        db.flush()
        db.commit()
    except IntegrityError:
        db.rollback()
        storage.delete_object(storage_key)
        existing = find_existing_primary_document(db, current_user.id, file_hash)
        if existing is None:
            raise
        duplicate = create_duplicate_document(db, current_user, filename, mime_type, len(file_bytes), file_hash, existing)
        return upload_result(
            filename,
            document_id=str(duplicate.id),
            status="duplicate",
            duplicate_of_id=str(existing.id),
        )

    db.refresh(document)
    enqueue_document_processing(db, document)
    return upload_result(filename, document_id=str(document.id), status=document.status)


async def read_limited_file(upload: UploadFile) -> dict:
    max_bytes = settings.max_file_size_mb * 1024 * 1024
    chunks: list[bytes] = []
    total = 0

    while True:
        chunk = await upload.read(CHUNK_SIZE)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            return {
                "bytes": b"",
                "error": {
                    "code": "file_too_large",
                    "message": f"File exceeds {settings.max_file_size_mb} MB limit",
                },
            }
        chunks.append(chunk)

    return {"bytes": b"".join(chunks), "error": None}


def sniff_mime_type(file_bytes: bytes) -> str | None:
    for prefix, mime_type in MAGIC_BYTES:
        if file_bytes.startswith(prefix):
            return mime_type
    return None


def sanitize_filename(filename: str | None) -> str:
    if not filename:
        return "upload"
    return PurePath(filename.replace("\\", "/")).name or "upload"


def find_existing_primary_document(db: Session, user_id, file_hash: str) -> Document | None:
    return (
        db.query(Document)
        .filter(
            Document.user_id == user_id,
            Document.file_hash == file_hash,
            Document.status != "duplicate",
        )
        .order_by(Document.created_at.asc())
        .first()
    )


def create_duplicate_document(
    db: Session,
    current_user: User,
    filename: str,
    mime_type: str,
    size_bytes: int,
    file_hash: str,
    original: Document,
) -> Document:
    duplicate = Document(
        user_id=current_user.id,
        filename=filename,
        mime_type=mime_type,
        size_bytes=size_bytes,
        file_hash=file_hash,
        storage_key=original.storage_key,
        status="duplicate",
        duplicate_of_id=original.id,
        duplicate_reason="same_file",
    )
    db.add(duplicate)
    db.commit()
    db.refresh(duplicate)
    return duplicate


def enqueue_document_processing(db: Session, document: Document) -> None:
    job = db.query(Job).filter(Job.document_id == document.id).order_by(Job.created_at.desc()).first()
    try:
        async_result = process_document.delay(str(document.id))
    except Exception as exc:
        document.status = "failed"
        document.error_message = "Failed to enqueue document processing"
        if job is not None:
            job.status = "failed"
            job.last_error = str(exc)
        db.commit()
        db.refresh(document)
        return

    if job is not None:
        job.celery_task_id = async_result.id
    db.commit()
    db.refresh(document)


def upload_result(
    filename: str,
    document_id: str | None = None,
    status: str | None = None,
    duplicate_of_id: str | None = None,
    error: dict | None = None,
) -> dict:
    return {
        "filename": filename,
        "document_id": document_id,
        "status": status,
        "duplicate_of_id": duplicate_of_id,
        "error": error,
    }
