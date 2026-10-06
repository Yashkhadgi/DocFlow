# DocFlow V1 API Contract

Base path: `/api/v1`. JSON everywhere. All endpoints except `/auth/*` and `/health` require `Authorization: Bearer <jwt>`. Users can only access their own documents; return `404` for another user's document.

## Statuses

Exact document statuses:

```text
queued | processing | needs_review | approved | failed | duplicate
```

Valid transitions:

```text
queued -> processing -> needs_review | approved | failed | duplicate
failed -> queued
needs_review -> approved
```

## Error Format

```json
{ "error": { "code": "validation_error", "message": "Human readable message" } }
```

Codes: `unauthorized` (401), `not_found` (404), `validation_error` (422/400), `file_too_large` (413), `unsupported_type` (415), `conflict` (409), `internal_error` (500).

## Endpoints

### GET /health

Response `200`:

```json
{ "status": "ok" }
```

### POST /auth/register

Request:

```json
{ "email": "a@b.com", "password": "min8chars", "full_name": "Asha" }
```

Response `201`:

```json
{ "id": "uuid", "email": "a@b.com", "full_name": "Asha" }
```

### POST /auth/login

Request:

```json
{ "email": "a@b.com", "password": "..." }
```

Response `200`:

```json
{
  "access_token": "jwt...",
  "token_type": "bearer",
  "expires_in": 86400,
  "user": { "id": "uuid", "email": "a@b.com", "full_name": "Asha" }
}
```

### POST /documents/upload

`multipart/form-data`, field name `files`, multiple files allowed. Limits: max 20 files per request, max 10 MB per file, allowed types `application/pdf`, `image/jpeg`, `image/png`. Type must be verified by magic bytes.

Response `200`:

```json
{
  "results": [
    { "filename": "inv1.pdf", "document_id": "uuid", "status": "queued", "duplicate_of_id": null, "error": null },
    { "filename": "inv1_copy.pdf", "document_id": "uuid2", "status": "duplicate", "duplicate_of_id": "uuid", "error": null },
    {
      "filename": "notes.exe",
      "document_id": null,
      "status": null,
      "duplicate_of_id": null,
      "error": { "code": "unsupported_type", "message": "Only PDF, JPG, PNG allowed" }
    }
  ]
}
```

### GET /documents

Query params: `status`, `page`, `page_size`, `q`.

Response:

```json
{
  "items": [
    {
      "id": "uuid",
      "filename": "inv1.pdf",
      "status": "needs_review",
      "auto_approved": false,
      "vendor_name": "Acme Traders",
      "invoice_number": "INV-001",
      "total": "11800.00",
      "issues_count": 1,
      "low_confidence_count": 2,
      "created_at": "2026-10-06T10:00:00Z",
      "updated_at": "2026-10-06T10:00:20Z"
    }
  ],
  "page": 1,
  "page_size": 20,
  "total": 42,
  "counts": {
    "queued": 0,
    "processing": 1,
    "needs_review": 5,
    "approved": 30,
    "failed": 1,
    "duplicate": 5
  }
}
```

### GET /documents/{id}

Returns document metadata, a five-minute presigned `file_url`, fields, line items, validation issues, and job summary.

### PATCH /documents/{id}/fields

Allowed only when status is `needs_review`; otherwise `409`.

Request:

```json
{
  "fields": { "gstin": "27ABCDE1234F1Z5", "total": "11800.00" },
  "line_items": [
    { "position": 1, "description": "Steel rods", "quantity": "10", "rate": "1000", "amount": "10000" }
  ]
}
```

Behavior: set `reviewed_value`, clear `needs_review` on edited fields, replace line items when provided, re-run `validate()`, replace validation issues, return document detail.

### POST /documents/{id}/approve

Allowed only from `needs_review`. If blocking error issues remain, return `409` unless body is `{ "force": true }`. On success set status `approved` and `approved_at`, then return detail.

### POST /documents/{id}/retry

Allowed only from `failed`. Reset job attempts, set document status `queued`, enqueue task, return detail.

### GET /export

Query: `format=csv|json`, `status` default `approved`, optional comma-separated `ids`. Returns file download. Use final values: `reviewed_value` if present, else `value`.

CSV columns:

```text
document_id,filename,vendor_name,invoice_number,invoice_date,gstin,currency,subtotal,tax,total,item_position,item_description,item_quantity,item_rate,item_amount
```
