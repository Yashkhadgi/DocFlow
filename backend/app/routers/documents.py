from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from hashlib import sha256
from pathlib import PurePath
from typing import Annotated
from uuid import UUID
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.security import get_current_user
from app.config import settings
from app.db import get_db
from app.models import Document, ExtractedField, Job, LineItem, User, ValidationIssue
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


@router.post("/{document_id}/retry")
def retry_document(
    document_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    document = (
        db.query(Document)
        .filter(Document.id == document_id, Document.user_id == current_user.id)
        .first()
    )
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "not_found", "message": "Document not found"},
        )
    if document.status != "failed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "conflict", "message": "Only failed documents can be retried"},
        )

    job = (
        db.query(Job)
        .filter(Job.document_id == document.id)
        .order_by(Job.created_at.desc())
        .first()
    )
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "conflict", "message": "Document has no processing job"},
        )

    now = datetime.now(timezone.utc)
    document.status = "queued"
    document.error_message = None
    document.updated_at = now
    job.status = "queued"
    job.attempts = 0
    job.last_error = None
    job.started_at = None
    job.finished_at = None
    db.commit()
    db.refresh(document)

    try:
        async_result = process_document.delay(str(document.id))
    except Exception:
        document.status = "failed"
        document.error_message = "Failed to enqueue document processing"
        job.status = "failed"
        job.last_error = document.error_message
        job.finished_at = datetime.now(timezone.utc)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "internal_error", "message": "Failed to enqueue document processing"},
        )

    job.celery_task_id = async_result.id
    db.commit()
    db.refresh(document)
    return serialize_document_detail(db, document)


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


def serialize_document_detail(db: Session, document: Document) -> dict:
    fields = (
        db.query(ExtractedField)
        .filter(ExtractedField.document_id == document.id)
        .order_by(ExtractedField.field_name.asc())
        .all()
    )
    line_items = (
        db.query(LineItem)
        .filter(LineItem.document_id == document.id)
        .order_by(LineItem.position.asc())
        .all()
    )
    issues = (
        db.query(ValidationIssue)
        .filter(ValidationIssue.document_id == document.id)
        .order_by(ValidationIssue.id.asc())
        .all()
    )
    job = (
        db.query(Job)
        .filter(Job.document_id == document.id)
        .order_by(Job.created_at.desc())
        .first()
    )
    return {
        "id": document.id,
        "filename": document.filename,
        "mime_type": document.mime_type,
        "size_bytes": document.size_bytes,
        "status": document.status,
        "auto_approved": document.auto_approved,
        "duplicate_of_id": document.duplicate_of_id,
        "duplicate_reason": document.duplicate_reason,
        "error_message": document.error_message,
        "file_url": storage.presign_get_url(document.storage_key),
        "fields": {
            field.field_name: {
                "value": field.reviewed_value if field.reviewed_value is not None else field.value,
                "confidence": float(field.confidence),
                "needs_review": field.needs_review,
                "reviewed_value": field.reviewed_value,
                "bbox": field.bbox,
            }
            for field in fields
        },
        "line_items": [
            {
                "position": item.position,
                "description": item.description,
                "quantity": _string_or_none(item.quantity),
                "rate": _string_or_none(item.rate),
                "amount": _string_or_none(item.amount),
                "confidence": _string_or_none(item.confidence),
            }
            for item in line_items
        ],
        "validation_issues": [
            {
                "rule": issue.rule,
                "severity": issue.severity,
                "field_name": issue.field_name,
                "message": issue.message,
            }
            for issue in issues
        ],
        "job": None
        if job is None
        else {
            "id": job.id,
            "status": job.status,
            "attempts": job.attempts,
            "max_attempts": job.max_attempts,
            "last_error": job.last_error,
            "started_at": job.started_at,
            "finished_at": job.finished_at,
        },
        "created_at": document.created_at,
        "updated_at": document.updated_at,
    }


def _string_or_none(value: Decimal | None) -> str | None:
    return None if value is None else str(value)


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
