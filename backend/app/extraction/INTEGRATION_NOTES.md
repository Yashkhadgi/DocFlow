# Person B to Person A: Integration Guide (DocFlow V1)

This document provides exact instructions for **Person A (Backend + Infra)** to integrate Person B's extraction module (`app.extraction`) into the FastAPI routes, database pipeline, and Celery workers during Phase 2 (Integration I1).

---

## 1. Importing the Frozen Interface

Import directly from `app.extraction`:

```python
from app.extraction import (
    extract,
    validate,
    needs_review,
    low_confidence_fields,
    find_business_duplicate,
    to_csv,
    to_json,
    ExtractionResult,
    FieldValue,
    LineItem,
    ValidationIssue,
    DuplicateMatch,
    ExtractionError,
)
```

---

## 2. Calling in Celery Worker (`app/workers/tasks.py`)

### Step 2.1: Run Vision LLM Extraction
> **IMPORTANT:** `extract()` makes blocking network calls to the Anthropic API (typical latency: **2–4 seconds**). Call it inside your Celery worker task, **never** in the synchronous FastAPI request thread.

```python
try:
    result: ExtractionResult = extract(file_bytes=file_bytes, mime_type=mime_type)
except ExtractionError as e:
    logger.error("Extraction failed for document %s: %s (retryable=%s)", document_id, e.message, e.retryable)
    if e.retryable:
        # Retry transient failures (rate limits, timeouts, 5xx) with backoff
        raise self.retry(exc=e, countdown=2 ** self.request.retries * 5)
    else:
        # Non-retryable errors (corrupted file, unencrypted PDF, 401/403)
        # Land immediately in 'failed' status with readable error message
        doc.status = "failed"
        doc.error_message = e.message
        db.commit()
        return
```

### Step 2.2: Run Validation Rules (Pure Function, Fast)
```python
issues: list[ValidationIssue] = validate(result)
```

### Step 2.3: Check Business-Level Duplicate
Before saving new rows, query the database for the user's other non-duplicate documents:
```python
# existing: list of dicts with 'id' (or 'document_id'), 'vendor_name', 'invoice_number'
existing_docs = [
    {"id": str(d.id), "vendor_name": d.vendor_name, "invoice_number": d.invoice_number}
    for d in user_other_documents
]

dup_match: DuplicateMatch | None = find_business_duplicate(result, existing_docs)
if dup_match:
    doc.status = "duplicate"
    doc.duplicate_of_id = dup_match.document_id
    doc.duplicate_reason = "same_invoice"
```

### Step 2.4: Decide Review Status
```python
if needs_review(result, issues):
    doc.status = "needs_review"
    doc.auto_approved = False
else:
    doc.status = "approved"
    doc.auto_approved = True
```

---

## 3. Review & Edit Endpoints (`PATCH /documents/{id}/fields`)

When a user edits fields in the split-screen UI:
1. Update `reviewed_value` on the field rows.
2. Reconstruct an `ExtractionResult` using the effective field values (`reviewed_value or value`).
3. Re-run `validate(result)` to refresh `validation_issues`.

---

## 4. Export Endpoint (`GET /export`)

For CSV and JSON export downloads:

```python
# Pass list of document dictionaries with resolved values:
export_docs = [
    {
        "document_id": str(doc.id),
        "filename": doc.filename,
        "fields": {
            "vendor_name": doc.vendor_name,       # final reviewed value
            "invoice_number": doc.invoice_number,
            "invoice_date": str(doc.invoice_date),
            "gstin": doc.gstin,
            "currency": doc.currency,
            "subtotal": str(doc.subtotal),
            "tax": str(doc.tax),
            "total": str(doc.total),
        },
        "line_items": [
            {
                "position": item.position,
                "description": item.description,
                "quantity": str(item.quantity),
                "rate": str(item.rate),
                "amount": str(item.amount),
            }
            for item in doc.line_items
        ]
    }
    for doc in approved_documents
]

if format == "csv":
    content = to_csv(export_docs)
    return Response(content=content, media_type="text/csv", headers={"Content-Disposition": 'attachment; filename="export.csv"'})
elif format == "json":
    content = to_json(export_docs)
    return Response(content=content, media_type="application/json", headers={"Content-Disposition": 'attachment; filename="export.json"'})
```

---

## 5. Required Environment Variables

Ensure these are configured in the worker environment:
- `ANTHROPIC_API_KEY`: API key with Claude vision access.
- `LLM_MODEL`: `claude-sonnet-5-5` (or model name used in deployment).
- `CONFIDENCE_THRESHOLD`: `0.85` (default threshold for human review routing).
