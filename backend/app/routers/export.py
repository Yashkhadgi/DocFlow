from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session, selectinload

from app.auth.security import get_current_user
from app.db import get_db
from app.models import Document, User
from app.services.export_service import build_export_payload, get_export_formatter

router = APIRouter(tags=["export"])


@router.get("/export")
def export_documents(
    format: str = Query(..., description="Export format: csv or json"),
    status_filter: str = Query(
        default="approved",
        alias="status",
        description="Filter documents by status (default: approved)",
    ),
    ids: str | None = Query(default=None, description="Optional comma-separated document IDs"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    fmt = format.lower().strip()
    if fmt not in ("csv", "json"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid format. Must be 'csv' or 'json'",
        )

    query = (
        db.query(Document)
        .options(
            selectinload(Document.fields),
            selectinload(Document.line_items),
        )
        .filter(Document.user_id == current_user.id)
    )

    if status_filter:
        query = query.filter(Document.status == status_filter)

    if ids is not None:
        valid_uuids: list[UUID] = []
        for raw_id in ids.split(","):
            cleaned = raw_id.strip()
            if cleaned:
                try:
                    valid_uuids.append(UUID(cleaned))
                except ValueError:
                    # Ignore invalid UUID tokens
                    pass

        if not valid_uuids:
            # IDs were provided but none were valid, return empty export
            documents: list[Document] = []
        else:
            documents = (
                query.filter(Document.id.in_(valid_uuids))
                .order_by(Document.created_at.asc())
                .all()
            )
    else:
        documents = query.order_by(Document.created_at.asc()).all()

    formatter, media_type, ext = get_export_formatter(fmt)
    docs_payload = build_export_payload(documents)
    content = formatter(docs_payload)

    date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    filename = f"docflow_export_{date_str}.{ext}"

    headers = {
        "Content-Disposition": f'attachment; filename="{filename}"',
    }

    return Response(
        content=content,
        media_type=media_type,
        headers=headers,
    )
