from datetime import datetime, timezone
from decimal import Decimal
from hashlib import sha256
from pathlib import PurePath
from typing import Annotated, Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.security import get_current_user
from app.config import settings
from app.db import get_db
from app.extraction.types import ExtractionResult, FieldValue, LineItem as ExtractedLineItem
from app.extraction.validators import validate
from app.models import Document, ExtractedField, Job, LineItem, User, ValidationIssue
from app.schemas import ApproveDocumentRequest, PatchDocumentFieldsRequest
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


@router.get("")
def list_documents(
    status_filter: str | None = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    q: str | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    all_statuses = ["queued", "processing", "needs_review", "approved", "failed", "duplicate"]
    counts_query = (
        db.query(Document.status, func.count(Document.id))
        .filter(Document.user_id == current_user.id)
        .group_by(Document.status)
        .all()
    )
    counts_map = dict(counts_query)
    counts = {st: counts_map.get(st, 0) for st in all_statuses}

    base_query = db.query(Document).filter(Document.user_id == current_user.id)
    if status_filter:
        if status_filter not in all_statuses:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"code": "validation_error", "message": "Invalid document status"},
            )
        base_query = base_query.filter(Document.status == status_filter)
    if q:
        search_term = f"%{q}%"
        vendor_matches = (
            db.query(ExtractedField.document_id)
            .join(Document, Document.id == ExtractedField.document_id)
            .filter(
                Document.user_id == current_user.id,
                ExtractedField.field_name == "vendor_name",
                or_(
                    ExtractedField.value.ilike(search_term),
                    ExtractedField.reviewed_value.ilike(search_term),
                ),
            )
        )
        base_query = base_query.filter(
            or_(Document.filename.ilike(search_term), Document.id.in_(vendor_matches))
        )

    total = base_query.count()
    documents = (
        base_query.order_by(Document.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    items = []
    for doc in documents:
        field_rows = db.query(ExtractedField).filter(ExtractedField.document_id == doc.id).all()
        field_map = {
            f.field_name: (f.reviewed_value if f.reviewed_value is not None else f.value)
            for f in field_rows
        }

        issues_count = (
            db.query(ValidationIssue)
            .filter(ValidationIssue.document_id == doc.id)
            .count()
        )
        low_confidence_count = sum(1 for f in field_rows if f.needs_review)

        items.append({
            "id": str(doc.id),
            "filename": doc.filename,
            "status": doc.status,
            "auto_approved": doc.auto_approved,
            "vendor_name": field_map.get("vendor_name"),
            "invoice_number": field_map.get("invoice_number"),
            "total": field_map.get("total"),
            "issues_count": issues_count,
            "low_confidence_count": low_confidence_count,
            "created_at": _format_iso(doc.created_at),
            "updated_at": _format_iso(doc.updated_at),
        })

    return {
        "items": items,
        "page": page,
        "page_size": page_size,
        "total": total,
        "counts": counts,
    }


@router.get("/{document_id}")
def get_document(
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
    return serialize_document_detail(db, document)


@router.patch("/{document_id}/fields")
def update_document_fields(
    document_id: UUID,
    payload: PatchDocumentFieldsRequest,
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
    if document.status != "needs_review":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "conflict", "message": "Only documents in needs_review can be edited"},
        )

    # 1. Update fields
    if payload.fields:
        for fname, val in payload.fields.items():
            field_rec = (
                db.query(ExtractedField)
                .filter(ExtractedField.document_id == document.id, ExtractedField.field_name == fname)
                .first()
            )
            str_val = None if val is None else str(val)
            if field_rec is not None:
                field_rec.reviewed_value = str_val
                field_rec.needs_review = False
            else:
                db.add(
                    ExtractedField(
                        document_id=document.id,
                        field_name=fname,
                        value=str_val,
                        reviewed_value=str_val,
                        confidence=Decimal("1.0"),
                        needs_review=False,
                    )
                )

    # 2. Replace line items if provided
    if payload.line_items is not None:
        db.query(LineItem).filter(LineItem.document_id == document.id).delete()
        for idx, item in enumerate(payload.line_items, 1):
            db.add(
                LineItem(
                    document_id=document.id,
                    position=int(item.get("position", idx)),
                    description=item.get("description"),
                    quantity=_to_decimal(item.get("quantity")),
                    rate=_to_decimal(item.get("rate")),
                    amount=_to_decimal(item.get("amount")),
                    confidence=Decimal("1.0"),
                )
            )

    db.flush()

    # 3. Re-run validation
    all_fields = db.query(ExtractedField).filter(ExtractedField.document_id == document.id).all()
    all_items = db.query(LineItem).filter(LineItem.document_id == document.id).order_by(LineItem.position.asc()).all()

    extraction_fields = {
        f.field_name: FieldValue(
            value=f.reviewed_value if f.reviewed_value is not None else f.value,
            confidence=float(f.confidence),
        )
        for f in all_fields
    }
    extraction_items = [
        ExtractedLineItem(
            description=li.description,
            quantity=str(li.quantity) if li.quantity is not None else None,
            rate=str(li.rate) if li.rate is not None else None,
            amount=str(li.amount) if li.amount is not None else None,
            confidence=float(li.confidence) if li.confidence is not None else 1.0,
        )
        for li in all_items
    ]

    extraction_result = ExtractionResult(fields=extraction_fields, line_items=extraction_items)
    new_issues = validate(extraction_result)

    db.query(ValidationIssue).filter(ValidationIssue.document_id == document.id).delete()
    for issue in new_issues:
        db.add(
            ValidationIssue(
                document_id=document.id,
                rule=issue.rule,
                severity=issue.severity,
                field_name=issue.field_name,
                message=issue.message,
            )
        )

    document.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(document)
    return serialize_document_detail(db, document)


@router.post("/{document_id}/approve")
def approve_document(
    document_id: UUID,
    payload: ApproveDocumentRequest | None = None,
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
    if document.status != "needs_review":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "conflict", "message": "Only documents in needs_review can be approved"},
        )

    force = payload.force if payload is not None else False
    if not force:
        error_count = (
            db.query(ValidationIssue)
            .filter(ValidationIssue.document_id == document.id, ValidationIssue.severity == "error")
            .count()
        )
        if error_count > 0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"code": "conflict", "message": "Cannot approve document with blocking validation errors without force=true"},
            )

    now = datetime.now(timezone.utc)
    document.status = "approved"
    document.approved_at = now
    document.updated_at = now
    db.commit()
    db.refresh(document)
    return serialize_document_detail(db, document)



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


def _format_iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat().replace("+00:00", "Z")


def _to_decimal(val: Any) -> Decimal | None:
    if val is None:
        return None
    s = str(val).strip()
    if not s:
        return None
    try:
        return Decimal(s)
    except Exception:
        return None


def _string_or_none(value: Decimal | None) -> str | None:
    return None if value is None else str(value)


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

    file_url = None
    if document.status != "duplicate" and document.storage_key:
        try:
            file_url = storage.presign_get_url(document.storage_key)
        except Exception:
            file_url = None

    return {
        "id": str(document.id),
        "filename": document.filename,
        "mime_type": document.mime_type,
        "status": document.status,
        "auto_approved": document.auto_approved,
        "duplicate_of_id": str(document.duplicate_of_id) if document.duplicate_of_id else None,
        "duplicate_reason": document.duplicate_reason,
        "error_message": document.error_message,
        "file_url": file_url,
        "fields": [
            {
                "field_name": field.field_name,
                "value": field.value,
                "reviewed_value": field.reviewed_value,
                "confidence": float(field.confidence),
                "needs_review": field.needs_review,
                "bbox": field.bbox,
            }
            for field in fields
        ],
        "line_items": [
            {
                "position": item.position,
                "description": item.description,
                "quantity": _string_or_none(item.quantity),
                "rate": _string_or_none(item.rate),
                "amount": _string_or_none(item.amount),
                "confidence": float(item.confidence) if item.confidence is not None else None,
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
        if (job is None or document.status == "duplicate")
        else {
            "status": job.status,
            "attempts": job.attempts,
            "max_attempts": job.max_attempts,
            "last_error": job.last_error,
        },
        "created_at": _format_iso(document.created_at),
        "updated_at": _format_iso(document.updated_at),
    }



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
