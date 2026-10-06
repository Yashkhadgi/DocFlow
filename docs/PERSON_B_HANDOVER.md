# Person B Handover & Integration Guide

**Status:** Person B (AI & Data) has completed tasks **B1 through B8**. The extraction module (`app.extraction`) is ready for Phase 2 integration.

---

## 1. Handover Summary

| Attribute | Details |
|---|---|
| **Module** | `backend/app/extraction` |
| **Owner** | Person B (AI & Data) |
| **Model** | `claude-sonnet-5-5` (Anthropic Vision Messages API) |
| **Latency** | ~3.5s to 6.0s per invoice |
| **Estimated Cost** | ~$1.19 per 100 invoices |
| **Phase / Task** | Phase 2: Integration (**Task I1**) |

---

## 2. Public Interface & Imports

Person A can import all required extraction, validation, and export functions directly from `app.extraction`:

```python
from app.extraction import (
    extract,                  # (file_bytes: bytes, mime_type: str) -> ExtractionResult
    validate,                 # (result: ExtractionResult) -> list[ValidationIssue]
    needs_review,             # (result: ExtractionResult, issues: list, threshold: float | None) -> bool
    low_confidence_fields,    # (result: ExtractionResult, threshold: float | None) -> list[str]
    find_business_duplicate,  # (result: ExtractionResult, existing: list[dict]) -> DuplicateMatch | None
    to_csv,                   # (docs: list[dict]) -> str
    to_json,                  # (docs: list[dict]) -> str
    ExtractionError,          # Custom exception for extraction failures
)
```

---

## 3. Required Environment Variables

Ensure these are configured in `.env` (and cloud environment settings on Render):

```env
# AI Extraction (Anthropic)
ANTHROPIC_API_KEY=sk-ant-...       # Dedicated production key with spend alerts enabled
LLM_MODEL=claude-sonnet-5-5        # Default vision LLM model
CONFIDENCE_THRESHOLD=0.85          # Threshold below which fields require human review

# Extractor Switch (False = live AI, True = local stub)
USE_STUB_EXTRACTOR=false
```

---

## 4. Exception Handling & Celery Retry Pattern

`extract()` raises `ExtractionError` with a crucial boolean property: **`exc.retryable`**.

Celery workers must use this attribute to distinguish between temporary infrastructure errors and permanent file failures:

```python
from celery.exceptions import MaxRetriesExceededError
from app.extraction import ExtractionError

try:
    result = extract(file_bytes, document.mime_type)
except ExtractionError as exc:
    if getattr(exc, "retryable", False):
        # Transient failure (rate limits, network timeout, 5xx from LLM)
        # Apply exponential backoff (e.g., 5s, 20s, 60s)
        countdown = 5 * (2 ** self.request.retries)
        try:
            raise self.retry(exc=exc, countdown=countdown, max_retries=settings.job_max_attempts)
        except MaxRetriesExceededError:
            _mark_document_failed(db, document, error_message=str(exc))
    else:
        # Non-retryable failure (corrupted file, unreadable payload) -> Fail immediately
        _mark_document_failed(db, document, error_message=str(exc))
```

---

## 5. Integration Action Checklist

### For Member A (Backend + Infra)
- [ ] **Task A5 (Retries & Backoff)**: Integrate `exc.retryable` logic inside `app.workers.tasks.process_document`.
- [ ] **Task A6 (Read/Review)**: Finish `GET /documents`, `GET /documents/{id}`, `PATCH /documents/{id}/fields`, `POST /documents/{id}/approve`, and `POST /documents/{id}/retry`.
- [ ] **Task A7 (Export)**: Wire `to_csv` and `to_json` into the `GET /api/v1/export` endpoint.
- [ ] **Task I1 (Integration Swap)**: Set `USE_STUB_EXTRACTOR=false`, test with the 8 sample files in `/samples/invoices/`, and verify end-to-end processing.

### For Team Lead (Yash)
- [ ] Update the GitHub Project board: move **B1 through B8** to **Done**.
- [ ] Move **I1 (A + B Swap)** to **In Progress** when ready to test.
- [ ] Ensure `ANTHROPIC_API_KEY` is provisioned and shared with the worker runtime.
