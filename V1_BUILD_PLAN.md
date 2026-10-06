# DocFlow: Document Processing and Automation SaaS: V1 Build Plan

> **READ THIS FIRST (instructions for the AI assistant reading this file)**
>
> This file is the single source of truth for building V1 of this project. A team of 3 developers plus 1 team lead is building it in parallel, each with their own AI assistant. Every person gives you this same file and tells you which role they are (A, B, C, or Lead).
>
> Rules for you, the AI:
> 1. Work **only** on the tasks and folders assigned to your person's role. Do not edit another role's folders.
> 2. The **contracts in Section 5** (statuses, schema, API, extraction JSON, Python interfaces) are frozen. Implement them exactly. Do not rename fields, change types, or invent new endpoints. If something seems wrong or missing, tell the user to raise it with the Lead instead of silently changing it.
> 3. Build against **mocks/stubs** for the other roles' work (Section 6 to 8), so no one is blocked.
> 4. Finish tasks in the listed order. Each task has a "Done when" checklist. Do not call a task finished until every item is satisfied, and tell the user how to verify it.
> 5. Write tests for the logic you own. Keep PRs small (one task each).
> 6. Never commit secrets. Use environment variables from `.env.example`.
> 7. If a requirement is ambiguous, pick the simplest option that satisfies the contract, state your assumption in the PR description, and continue.
> 8. V1 scope is **only** what is in this file. Ideas beyond it go in `V2_IDEAS.md`. Do not build them now.

---

## 1. Project Overview

**Product:** A web SaaS where a user bulk-uploads invoices (PDF/JPG/PNG), the system extracts structured data with a vision LLM in the background, validates it, flags uncertain fields for human review, and exports clean data as CSV/JSON.

**Problem it solves:** Manual invoice processing causes delays and inconsistent data. An accountant types hundreds of invoices by hand.

**Scope decision for V1:** Support **invoices only** (not contracts or forms). One document type done well beats three done badly.

**What judges evaluate (design for these explicitly):**

| Criterion | How V1 demonstrates it |
|---|---|
| Idempotency | Re-uploading the same file is detected by SHA-256 hash and not processed twice. Re-delivered or retried jobs do not create duplicate rows. |
| Retries | Failed jobs retry with exponential backoff, then land in `failed` with a manual Retry button. |
| File security | Type/size/magic-byte validation, random storage keys, private bucket, short-lived presigned URLs, per-user access checks. |
| Validation | Business rules (totals, GSTIN, date) produce visible red flags. |
| Understandability | Split-screen review UI and a clear 3-minute demo story. |

**Hard deliverables for V1:** working prototype, real database (PostgreSQL), **deployed on public URLs**, README, architecture diagram, sample documents, demo script.

---

## 2. Tech Stack (fixed, do not substitute)

| Layer | Choice |
|---|---|
| Frontend | React + TypeScript + Vite + Tailwind CSS |
| Backend API | Python 3.11 + FastAPI + SQLAlchemy 2.x + Alembic |
| Queue | Celery with Redis as broker and result backend (RabbitMQ is intentionally replaced by Redis for easier free deployment; mention this in the README) |
| Database | PostgreSQL 15+ |
| Object storage | S3-compatible (Cloudflare R2 in production, MinIO in local docker-compose), accessed via `boto3` |
| AI extraction | Anthropic Claude API with vision (PDFs and images), model name read from env var `LLM_MODEL` |
| Auth | Email + password, bcrypt hashes, JWT (HS256) access tokens |
| Local dev | Docker Compose |
| Deploy | Frontend on Vercel; API + Celery worker on Render (or Railway); Postgres on Neon; Redis on Upstash or Render Redis; storage on Cloudflare R2 |

---

## 3. Roles and Ownership

**Current assignment for this repo:** Yash is both **Lead** and **Person A**. That means he owns all Lead responsibilities plus Backend + Infra delivery. In practice, he should complete Lead Step 0 first, then implement A1 to A8, while coordinating B and C and running integration/final QA.

| Role | Name | Owns (folders) | Summary |
|---|---|---|---|
| **Lead** | Yash / Team lead | `/contracts`, `/.github`, `docker-compose.yml`, `.env.example`, `V2_IDEAS.md`, merges and final QA | Repo setup, freezes contracts, integration, merges |
| **A** | Yash / Backend + Infra | `/backend/app` (everything except `/backend/app/extraction`) | API, DB, auth, upload, storage, queue, retries, security, **deployment of backend** |
| **B** | AI + Data | `/backend/app/extraction`, `/samples` | Extraction, confidence, validation, duplicate helper, export, sample documents |
| **C** | Frontend + Story | `/frontend`, `/docs` | UI, mock API, review screen, README, diagram, slides, demo script, **deployment of frontend** |

---

## 4. Repository Structure

```
/
├── README.md                      (C writes final version)
├── V1_BUILD_PLAN.md               (this file)
├── V2_IDEAS.md                    (Lead; anyone can add ideas via PR)
├── docker-compose.yml             (Lead)
├── .env.example                   (Lead)
├── .github/
│   ├── CODEOWNERS
│   └── pull_request_template.md
├── contracts/                     (Lead only; changes need PR + all approvals)
│   ├── API_CONTRACT.md            (summary; Section 5.3 is the source)
│   ├── schema.sql
│   ├── extraction_schema.json
│   └── fixtures/
│       ├── auth_login.json
│       ├── documents_list.json
│       ├── document_detail_needs_review.json
│       ├── document_detail_approved.json
│       ├── document_detail_failed.json
│       ├── document_detail_duplicate.json
│       └── upload_response.json
├── backend/
│   ├── pyproject.toml / requirements.txt
│   ├── Dockerfile
│   ├── alembic/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── db.py
│   │   ├── models.py
│   │   ├── schemas.py             (Pydantic models, shared types)
│   │   ├── auth/
│   │   ├── routers/
│   │   ├── services/              (storage.py, documents.py, export_service.py)
│   │   ├── workers/               (celery_app.py, tasks.py)
│   │   └── extraction/            ← OWNED BY B
│   │       ├── __init__.py        (exports extract, validate, find_business_duplicate, needs_review, to_csv, to_json)
│   │       ├── types.py           (ExtractionResult, ValidationIssue, ...)
│   │       ├── extractor.py
│   │       ├── prompts.py
│   │       ├── validators.py
│   │       ├── duplicates.py
│   │       ├── export.py
│   │       ├── cli.py             (python -m app.extraction.cli samples/invoice1.pdf)
│   │       └── tests/
│   └── tests/
├── frontend/
│   ├── package.json
│   ├── src/
│   │   ├── api/                   (client.ts, types.ts, mock/)
│   │   ├── pages/
│   │   ├── components/
│   │   └── main.tsx
│   └── Dockerfile (optional)
├── samples/                       (B)
│   ├── invoices/                  (the sample files)
│   └── expected/                  (expected JSON per sample)
└── docs/                          (C)
    ├── architecture.md / architecture.png
    ├── demo_script.md
    └── slides/
```

---

## 5. Frozen Contracts (the shared language between all roles)

### 5.1 Document statuses (exact strings)

```
queued | processing | needs_review | approved | failed | duplicate
```

| Status | Meaning |
|---|---|
| `queued` | File stored, job waiting for a worker |
| `processing` | Worker is running extraction |
| `needs_review` | Extraction done, but at least one field is below the confidence threshold OR a validation error exists. Waiting for a human |
| `approved` | Human approved, OR auto-approved (all fields confident and no validation errors; `auto_approved = true`) |
| `failed` | Job failed after all retries. Can be retried manually |
| `duplicate` | Same file hash already uploaded by this user, OR same (vendor + invoice number) as an existing document. `duplicate_of_id` points to the original |

Valid transitions:
`queued → processing → (needs_review | approved | failed | duplicate)`,
`failed → queued` (via retry),
`needs_review → approved` (via approve).

### 5.2 Database schema (`contracts/schema.sql`)

```sql
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE users (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email         TEXT NOT NULL UNIQUE,
  password_hash TEXT NOT NULL,
  full_name     TEXT,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE documents (
  id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id          UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  filename         TEXT NOT NULL,
  mime_type        TEXT NOT NULL,
  size_bytes       BIGINT NOT NULL,
  file_hash        CHAR(64) NOT NULL,              -- SHA-256 hex
  storage_key      TEXT NOT NULL,                   -- random key, never the filename
  status           TEXT NOT NULL CHECK (status IN
                   ('queued','processing','needs_review','approved','failed','duplicate')),
  auto_approved    BOOLEAN NOT NULL DEFAULT FALSE,
  duplicate_of_id  UUID REFERENCES documents(id),
  duplicate_reason TEXT,                            -- 'same_file' | 'same_invoice'
  error_message    TEXT,
  approved_at      TIMESTAMPTZ,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);
-- Idempotency: one non-duplicate document per (user, file hash)
CREATE UNIQUE INDEX uq_documents_user_hash_primary
  ON documents (user_id, file_hash) WHERE status <> 'duplicate';
CREATE INDEX idx_documents_user_status ON documents (user_id, status, created_at DESC);

CREATE TABLE jobs (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  document_id   UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  celery_task_id TEXT,
  status        TEXT NOT NULL CHECK (status IN ('queued','processing','succeeded','failed')),
  attempts      INT NOT NULL DEFAULT 0,
  max_attempts  INT NOT NULL DEFAULT 3,
  last_error    TEXT,
  started_at    TIMESTAMPTZ,
  finished_at   TIMESTAMPTZ,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_jobs_document ON jobs (document_id);

CREATE TABLE extracted_fields (
  id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  document_id    UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  field_name     TEXT NOT NULL,   -- vendor_name | invoice_number | invoice_date | gstin | subtotal | tax | total | currency
  value          TEXT,            -- value as extracted (string form)
  confidence     NUMERIC(4,3) NOT NULL CHECK (confidence BETWEEN 0 AND 1),
  needs_review   BOOLEAN NOT NULL DEFAULT FALSE,
  reviewed_value TEXT,            -- set when a human edits
  bbox           JSONB,           -- optional: {"page":1,"x":0.1,"y":0.2,"w":0.3,"h":0.05} normalized 0..1
  UNIQUE (document_id, field_name)
);

CREATE TABLE line_items (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  document_id  UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  position     INT NOT NULL,
  description  TEXT,
  quantity     NUMERIC(14,3),
  rate         NUMERIC(14,2),
  amount       NUMERIC(14,2),
  confidence   NUMERIC(4,3)
);

CREATE TABLE validation_issues (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  document_id  UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  rule         TEXT NOT NULL,     -- total_mismatch | line_items_mismatch | invalid_gstin | invalid_date | missing_required
  severity     TEXT NOT NULL CHECK (severity IN ('error','warning')),
  field_name   TEXT,
  message      TEXT NOT NULL
);
```

### 5.3 REST API contract

Base path: `/api/v1`. JSON everywhere. All endpoints except `/auth/*` and `/health` require header `Authorization: Bearer <jwt>`. Users can only access their own documents (return `404` for other users' documents, not `403`).

**Error format (all errors):**
```json
{ "error": { "code": "validation_error", "message": "Human readable message" } }
```
Codes: `unauthorized` (401), `not_found` (404), `validation_error` (422/400), `file_too_large` (413), `unsupported_type` (415), `conflict` (409), `internal_error` (500).

#### `GET /health`
`200 {"status":"ok"}`

#### `POST /auth/register`
Request: `{"email":"a@b.com","password":"min8chars","full_name":"Asha"}`
Response `201`: `{"id":"uuid","email":"a@b.com","full_name":"Asha"}`

#### `POST /auth/login`
Request: `{"email":"a@b.com","password":"..."}`
Response `200`:
```json
{ "access_token": "jwt...", "token_type": "bearer", "expires_in": 86400,
  "user": { "id": "uuid", "email": "a@b.com", "full_name": "Asha" } }
```

#### `POST /documents/upload`
`multipart/form-data`, field name `files` (multiple). Limits: max 20 files per request, max 10 MB per file, allowed types `application/pdf`, `image/jpeg`, `image/png`. Type is verified by **magic bytes**, not just the extension or the header.
Response `207`-style but returned as `200`, one result per file:
```json
{
  "results": [
    { "filename": "inv1.pdf", "document_id": "uuid", "status": "queued", "duplicate_of_id": null, "error": null },
    { "filename": "inv1_copy.pdf", "document_id": "uuid2", "status": "duplicate", "duplicate_of_id": "uuid", "error": null },
    { "filename": "notes.exe", "document_id": null, "status": null, "duplicate_of_id": null,
      "error": { "code": "unsupported_type", "message": "Only PDF, JPG, PNG allowed" } }
  ]
}
```
Behavior: compute SHA-256; if the same user already has a non-duplicate document with this hash, create a row with `status='duplicate'`, `duplicate_reason='same_file'`, and do **not** store the file again or enqueue a job. Otherwise store the file, create the document (`queued`) and job, enqueue the Celery task.

#### `GET /documents`
Query: `status` (optional, one of the statuses), `page` (default 1), `page_size` (default 20, max 100), `q` (optional filename/vendor search).
Response:
```json
{
  "items": [
    { "id":"uuid","filename":"inv1.pdf","status":"needs_review","auto_approved":false,
      "vendor_name":"Acme Traders","invoice_number":"INV-001","total":"11800.00",
      "issues_count":1,"low_confidence_count":2,
      "created_at":"2026-10-06T10:00:00Z","updated_at":"2026-10-06T10:00:20Z" }
  ],
  "page":1,"page_size":20,"total":42,
  "counts": { "queued":0,"processing":1,"needs_review":5,"approved":30,"failed":1,"duplicate":5 }
}
```

#### `GET /documents/{id}`
```json
{
  "id":"uuid","filename":"inv1.pdf","mime_type":"application/pdf","status":"needs_review",
  "auto_approved":false,"duplicate_of_id":null,"duplicate_reason":null,"error_message":null,
  "file_url":"https://...presigned, expires in 5 minutes...",
  "fields": [
    { "field_name":"vendor_name","value":"Acme Traders","reviewed_value":null,"confidence":0.97,
      "needs_review":false,"bbox":{"page":1,"x":0.1,"y":0.05,"w":0.3,"h":0.04} },
    { "field_name":"gstin","value":"27ABCDE1234F1Z5","reviewed_value":null,"confidence":0.62,
      "needs_review":true,"bbox":null }
  ],
  "line_items": [
    { "position":1,"description":"Steel rods","quantity":"10.000","rate":"1000.00","amount":"10000.00","confidence":0.95 }
  ],
  "validation_issues": [
    { "rule":"total_mismatch","severity":"error","field_name":"total",
      "message":"subtotal (10000.00) + tax (1800.00) = 11800.00 but total is 11500.00" }
  ],
  "job": { "status":"succeeded","attempts":1,"max_attempts":3,"last_error":null },
  "created_at":"...","updated_at":"..."
}
```

#### `PATCH /documents/{id}/fields`
Request (any subset): 
```json
{ "fields": { "gstin": "27ABCDE1234F1Z5", "total": "11800.00" },
  "line_items": [ { "position":1,"description":"Steel rods","quantity":"10","rate":"1000","amount":"10000" } ] }
```
Behavior: sets `reviewed_value` for each field, clears `needs_review` for edited fields, replaces line items if provided, **re-runs `validate()`** and replaces `validation_issues`. Returns the same shape as `GET /documents/{id}`. Allowed only when status is `needs_review`; otherwise `409 conflict`.

#### `POST /documents/{id}/approve`
Allowed only from `needs_review`. If blocking `error`-severity validation issues remain, return `409 conflict` with message listing them, unless body is `{"force": true}`. On success sets `approved`, `approved_at`. Returns document detail.

#### `POST /documents/{id}/retry`
Allowed only from `failed`. Resets job attempts, sets status `queued`, enqueues task. Returns document detail.

#### `GET /export`
Query: `format=csv|json` (required), `status` (default `approved`), `ids` (optional comma-separated). Returns a file download (`Content-Disposition: attachment`). Uses the **final value** of each field (`reviewed_value` if present, else `value`).

CSV columns (one row per **line item**; invoices with no line items yield one row with empty item columns):
```
document_id,filename,vendor_name,invoice_number,invoice_date,gstin,currency,subtotal,tax,total,item_position,item_description,item_quantity,item_rate,item_amount
```
JSON: array of `{ document_id, filename, fields:{...final values}, line_items:[...] }`.

### 5.4 Extraction JSON (`contracts/extraction_schema.json`)

This is what `extract()` returns (as a Pydantic model that serializes to this JSON):

```json
{
  "document_type": "invoice",
  "fields": {
    "vendor_name":    { "value": "Acme Traders",   "confidence": 0.97, "bbox": {"page":1,"x":0.1,"y":0.05,"w":0.3,"h":0.04} },
    "invoice_number": { "value": "INV-2026-001",   "confidence": 0.99, "bbox": null },
    "invoice_date":   { "value": "2026-10-01",     "confidence": 0.95, "bbox": null },
    "gstin":          { "value": "27ABCDE1234F1Z5","confidence": 0.62, "bbox": null },
    "currency":       { "value": "INR",            "confidence": 0.90, "bbox": null },
    "subtotal":       { "value": "10000.00",       "confidence": 0.96, "bbox": null },
    "tax":            { "value": "1800.00",        "confidence": 0.94, "bbox": null },
    "total":          { "value": "11800.00",       "confidence": 0.97, "bbox": null }
  },
  "line_items": [
    { "description": "Steel rods", "quantity": "10", "rate": "1000.00", "amount": "10000.00", "confidence": 0.95 }
  ],
  "raw_model_output": "...optional, for debugging, never shown to users..."
}
```
Rules: dates are ISO `YYYY-MM-DD`; money values are decimal strings with a dot and no thousands separators or currency symbols; a field the model cannot find has `value: null` and `confidence: 0.0`; `bbox` is optional and may always be `null` in V1 (the UI must work without it).

### 5.5 Python interface (B implements, A calls)

File: `backend/app/extraction/__init__.py` must export exactly these:

```python
from .types import ExtractionResult, ValidationIssue, DuplicateMatch

def extract(file_bytes: bytes, mime_type: str) -> ExtractionResult:
    """Call the vision LLM, return structured result. Raises ExtractionError on unrecoverable failure
    (A's worker catches it and retries). Must retry internally (max 2) on malformed JSON from the model."""

def validate(result: ExtractionResult) -> list[ValidationIssue]:
    """Pure function. Business rules. No I/O."""

def needs_review(result: ExtractionResult, issues: list[ValidationIssue], threshold: float | None = None) -> bool:
    """True if any required field confidence < threshold (default from env CONFIDENCE_THRESHOLD=0.85),
    or any issue has severity 'error'."""

def low_confidence_fields(result: ExtractionResult, threshold: float | None = None) -> list[str]:
    """Names of fields below threshold."""

def find_business_duplicate(result: ExtractionResult, existing: list[dict]) -> DuplicateMatch | None:
    """`existing` is a list of {"id": str, "vendor_name": str|None, "invoice_number": str|None}.
    Match on normalized vendor_name + normalized invoice_number. Pure function."""

def to_csv(docs: list[dict]) -> str: ...
def to_json(docs: list[dict]) -> str: ...
```

`ValidationIssue` fields: `rule`, `severity` (`error`|`warning`), `field_name`, `message`.
`DuplicateMatch` fields: `document_id`, `reason` (`"same_invoice"`).
`ExtractionError` is defined in `types.py`.

**Required fields** (for missing_required and review rules): `vendor_name`, `invoice_number`, `invoice_date`, `total`.

### 5.6 Validation rules (B implements in `validators.py`)

| Rule id | Severity | Logic |
|---|---|---|
| `total_mismatch` | error | `abs((subtotal + tax) - total) > 0.01` (skip if any of the three is missing) |
| `line_items_mismatch` | warning | `abs(sum(line amounts) - subtotal) > 0.01` (skip if no line items or no subtotal) |
| `invalid_gstin` | error | GSTIN present and does not match `^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$` |
| `invalid_date` | error | `invoice_date` present but not a valid ISO date, or is in the future by more than 1 day |
| `missing_required` | error | any required field has no value |

Use `Decimal` for all money math, never floats.

### 5.7 Environment variables (`.env.example`, Lead maintains)

```
# App
APP_ENV=local
SECRET_KEY=change-me
ACCESS_TOKEN_EXPIRE_MINUTES=1440
CORS_ORIGINS=http://localhost:5173
# DB
DATABASE_URL=postgresql+psycopg2://docflow:docflow@db:5432/docflow
# Redis / Celery
REDIS_URL=redis://redis:6379/0
# Storage (MinIO locally, Cloudflare R2 in prod)
S3_ENDPOINT_URL=http://minio:9000
S3_REGION=auto
S3_ACCESS_KEY=minioadmin
S3_SECRET_KEY=minioadmin
S3_BUCKET=docflow-documents
PRESIGNED_URL_EXPIRES_SECONDS=300
# Upload limits
MAX_FILE_SIZE_MB=10
MAX_FILES_PER_UPLOAD=20
# AI
ANTHROPIC_API_KEY=
LLM_MODEL=claude-sonnet-5-5
CONFIDENCE_THRESHOLD=0.85
# Worker
JOB_MAX_ATTEMPTS=3
# Frontend (frontend/.env)
VITE_API_BASE_URL=http://localhost:8000/api/v1
VITE_USE_MOCK=true
```

---

## 6. Lead Tasks (Step 0, do before others start, about 30 minutes)

**L1: Create the repo and structure** from Section 4. Add empty placeholder files so every role has a folder.

**L2: Commit contracts.** Copy Sections 5.1 to 5.6 into `/contracts` (`schema.sql`, `extraction_schema.json`, `API_CONTRACT.md`). Create the fixtures in `/contracts/fixtures/` using the example payloads in Section 5.3 (one for each status listed in the structure). These fixtures are what C builds against.

**L3: `docker-compose.yml`** with services: `db` (postgres:15), `redis`, `minio` (+ bucket creation), `api` (uvicorn, port 8000), `worker` (celery), `frontend` (vite dev, port 5173, optional). Use env vars from `.env.example`.

**L4: GitHub setup**
- Protect `main`: no direct push, PR required, 1 approval, no force push.
- `CODEOWNERS`:
  ```
  /contracts/                      @lead
  /backend/app/extraction/         @person-b
  /samples/                        @person-b
  /backend/                        @person-a
  /frontend/                       @person-c
  /docs/                           @person-c
  ```
- PR template: *What changed / Which task ID / How to verify / Contract changes? (yes/no)*.
- Create GitHub Issues for every task ID below (A1 to A8, B1 to B8, C1 to C8, I1 to I3, H1 to H4) and a Project board with To do / In progress / In review / Done.
- Branch naming: `feat/a1-skeleton`, `feat/b2-extract`, `feat/c4-review-ui`.

**L5: Contract freeze announcement.** Tell the team: "Contracts are frozen. Any change = open an issue, Lead approves, everyone is notified."

**L6: Accounts** (Lead or A creates): Neon DB, Upstash/Render Redis, Cloudflare R2 bucket, Anthropic API key (share with B and with the deployed worker), Render and Vercel projects.

**Lead during the build:** review and merge PRs quickly (target under 30 minutes), unblock questions, keep `V2_IDEAS.md` updated, run the Integration phase (Section 9).

---

## 7. Person A: Backend + Infra

**Your folder:** `/backend/app` (except `/backend/app/extraction`).
**You are NOT blocked by B:** until B delivers, use `stub_extract()` (below). **You are NOT blocked by C:** your API follows the contract and fixtures.

### Stub for B's work (put in `backend/app/workers/stubs.py`)

```python
def stub_extract(file_bytes, mime_type):
    # Return a hardcoded ExtractionResult matching Section 5.4 (copy contracts/fixtures values).
    # Randomly make 1 in 3 results have a low-confidence gstin so needs_review is exercised.
    ...
```
Make the worker choose via env `USE_STUB_EXTRACTOR=true|false`. When false, import the real functions from `app.extraction`. If the real module is not ready yet, the import must still work with the stub path.

### Tasks (in order)

**A1. Project skeleton and database**
- FastAPI app with `/api/v1` prefix, `/health`, CORS from `CORS_ORIGINS`, centralized error handler producing the error format in 5.3.
- SQLAlchemy models matching `schema.sql` exactly; Alembic initial migration that equals `schema.sql`.
- `Dockerfile`, wired into docker-compose.
- Done when: `docker-compose up` starts db, redis, minio, api; `GET /api/v1/health` returns ok; migration applies cleanly on an empty DB.

**A2. Auth**
- `POST /auth/register`, `POST /auth/login`; bcrypt; JWT HS256; dependency `get_current_user`.
- Seed script `scripts/seed.py` that creates demo user `demo@docflow.app` / `Demo@1234`.
- Done when: register/login work; protected route returns 401 without token; unit tests cover wrong password and expired token.

**A3. Storage service and upload endpoint**
- `services/storage.py`: `put_object`, `get_object`, `presign_get_url(key, expires)`, private bucket, auto-create bucket in local.
- `POST /documents/upload` exactly as in 5.3: magic-byte type check (`%PDF`, JPEG `FF D8 FF`, PNG `89 50 4E 47`), size limit, file-count limit, SHA-256, random key like `users/{user_id}/{uuid4}` (never use the original filename in the key), same-file duplicate detection, per-file results.
- Done when: uploading a PDF, a duplicate of it, and a `.exe` renamed to `.pdf` gives queued / duplicate / unsupported_type. Concurrent upload of the same file twice does not create two non-duplicate rows (rely on the unique index and handle `IntegrityError` by converting to duplicate).

**A4. Celery worker and job lifecycle**
- `workers/celery_app.py`, task `process_document(document_id)`.
- Flow: load document, set `processing` and job `processing` (increment attempts), download file from storage, call extractor (stub or real), run `validate()`, **business-duplicate check** via `find_business_duplicate()` against the user's other non-duplicate documents (mark `duplicate` + `duplicate_of_id` + `duplicate_reason='same_invoice'` if matched), persist fields/line items/issues, decide status: `needs_review` if `needs_review()` is true, else `approved` with `auto_approved=true`. Mark job `succeeded`.
- **Idempotent task:** if the document is already beyond `queued/processing` (i.e. approved, needs_review, duplicate), exit without changes. Replace (not append) extracted rows inside a single transaction so a redelivered task cannot duplicate data. Set `acks_late=True`.
- Done when: uploading a file drives it to `needs_review` or `approved` using the stub; killing and restarting the worker mid-job does not corrupt or duplicate rows.

**A5. Retries, backoff, failure handling**
- On exception: retry with exponential backoff (e.g. 5s, 20s, 60s) up to `JOB_MAX_ATTEMPTS`; each retry updates `jobs.attempts` and `last_error`; after the last attempt set document `failed` with a readable `error_message`.
- Add a debug env flag `FORCE_FAIL_FILENAME_CONTAINS=failme` which makes the stub raise (used in the demo to show retries).
- `POST /documents/{id}/retry` per contract.
- Done when: a file named `failme.pdf` goes processing → retries (visible attempts count) → `failed`; clicking retry (after unsetting the flag or renaming logic) completes it.

**A6. Read/review endpoints**
- `GET /documents` (filters, pagination, counts, search), `GET /documents/{id}` (with presigned `file_url`, 404 for other users' docs), `PATCH /documents/{id}/fields` (re-runs `validate()`), `POST /documents/{id}/approve` (with `force`), all exactly per 5.3.
- Done when: responses validate against the fixtures' shapes (write a test that loads each fixture and compares keys/types).

**A7. Export endpoint**
- `GET /export` using `to_csv` / `to_json` from B (until B delivers, a minimal local fallback; swap later). Uses final values (`reviewed_value` over `value`).
- Done when: both formats download with correct headers and content for approved documents.

**A8. Deployment (target: complete early; do not leave to the end)**
- Deploy API and worker to Render (two services from the same Dockerfile, different start commands), connect Neon (`sslmode=require`), Redis (use `rediss://` if TLS), Cloudflare R2 (set `S3_ENDPOINT_URL`, path-style addressing if required).
- Run migrations on deploy; run seed script once.
- Set `CORS_ORIGINS` to the Vercel URL once C has one.
- Done when: public `GET /health` works; login with the demo user works on the live URL; an upload on the live URL reaches `needs_review`/`approved` via the live worker.
- Note: Render free instances sleep; document a "warm-up" step in README.

**A's quality bar:** every endpoint matches the contract; no endpoint ever leaks another user's data; no file is ever publicly readable; secrets only via env; logs include document_id and job attempts.

---

## 8. Person B: AI + Data

**Your folders:** `/backend/app/extraction` and `/samples`.
**You are NOT blocked by anyone:** you need no DB, queue, API or UI. Everything is plain Python plus a CLI. You only need an Anthropic API key.

### Tasks (in order)

**B1. Sample pack (do first, everything else is tested against it)**
Create `/samples/invoices/` with 8 files and matching `/samples/expected/<name>.json` (ground truth in the 5.4 format):
1. `clean_invoice.pdf`: clean digital invoice, valid GSTIN, correct totals, 3 line items
2. `scanned_invoice.pdf`: scanned/slightly skewed
3. `photo_invoice.jpg`: phone photo of an invoice
4. `blurry_invoice.png`: low quality (should produce low-confidence fields)
5. `wrong_total.pdf`: total deliberately inconsistent with subtotal + tax
6. `bad_gstin.pdf`: invalid GSTIN format
7. `clean_invoice_copy.pdf`: byte-identical copy of #1 (tests same-file duplicate)
8. `same_invoice_resaved.pdf`: same vendor and invoice number as #1 but different bytes (tests business duplicate)
Also one file named `failme.pdf` (any valid PDF) for the retry demo.
Use realistic fake data (Indian invoices with GSTIN, INR). Do not use real company data. Generate them with HTML-to-PDF or a template; photos can be created by screenshotting/printing and photographing a document.
- Done when: all files and expected JSONs exist and a `samples/README.md` lists what each file tests.

**B2. `extract()`**
- `types.py`: Pydantic models `FieldValue(value, confidence, bbox)`, `LineItem`, `ExtractionResult`, `ValidationIssue`, `DuplicateMatch`, and `ExtractionError`.
- `extractor.py`: send the file (PDF as a document block, images as image blocks, base64) to the Anthropic Messages API using `LLM_MODEL`; force JSON-only output; parse into `ExtractionResult`. Normalize dates to ISO and money to plain decimal strings after parsing.
- `cli.py`: `python -m app.extraction.cli <file>` prints the JSON result and validation issues.
- Done when: CLI returns valid output for all 8 samples.

**B3. Prompt design and robustness**
- `prompts.py`: system prompt that defines every field, says "return `null` and confidence 0 when not present, never guess", defines confidence calibration (explain what 0.95, 0.7, 0.4 mean), requires ISO dates and plain decimals, and requires JSON only.
- If output is not valid JSON or fails the Pydantic model, retry up to 2 times with the parse error included; then raise `ExtractionError`.
- Strip markdown fences; handle timeouts and API errors by raising `ExtractionError` with a clear message (A's worker will retry).
- Never log full document contents.
- Done when: a script `scripts/eval_samples.py` compares output to `/samples/expected` and prints per-field accuracy; target at least 90% on clean/scanned/photo samples and visibly lower confidence on the blurry one.

**B4. `validate()`**: implement every rule in Section 5.6 with `Decimal`. Unit tests for each rule (pass and fail case) plus edge cases (missing values, rounding within 0.01).
- Done when: `wrong_total.pdf` yields `total_mismatch`, `bad_gstin.pdf` yields `invalid_gstin`, clean sample yields no errors.

**B5. Review rules**: `needs_review()` and `low_confidence_fields()` per 5.5; threshold from `CONFIDENCE_THRESHOLD` env (default 0.85), overridable by argument; only required fields plus `gstin`, `subtotal`, `tax` count toward the threshold.
- Done when: unit tests cover threshold boundaries and error-severity-forces-review.

**B6. `find_business_duplicate()`**: normalize vendor (lowercase, strip punctuation and legal suffixes such as pvt/ltd/llp) and invoice number (uppercase, strip spaces and leading zeros after prefix); both must match.
- Done when: unit tests pass for "Acme Traders Pvt. Ltd." vs "ACME TRADERS PVT LTD" with "INV-001" vs "inv 001".

**B7. Export**: `to_csv()` and `to_json()` exactly per the export section in 5.3 (columns, order, one row per line item). Use the `csv` module (proper quoting). Input rows use final values.
- Done when: output opens correctly in Excel/Sheets and unit tests check header order and row counts.

**B8. Package and document**
- `__init__.py` exports exactly the functions in 5.5.
- `backend/app/extraction/README.md`: how to run CLI, eval script, tests, env vars, known limitations.
- Done when: A can `from app.extraction import extract, validate, needs_review, find_business_duplicate, to_csv, to_json` with no changes.

**Stretch (only after B8):** return bounding boxes in the model output so the UI can highlight fields. Keep `bbox` optional.

---

## 9. Person C: Frontend + Story

**Your folders:** `/frontend` and `/docs`.
**You are NOT blocked by A:** run the whole app in mock mode (`VITE_USE_MOCK=true`) driven by `/contracts/fixtures`. Switching to the real API is a config change only.

### Design guidance
Clean, modern, professional SaaS look using Tailwind. Status colors: queued gray, processing blue (animated), needs_review amber, approved green, failed red, duplicate purple. Every screen must have loading, empty and error states. Keep it responsive at laptop widths; mobile is not required.

### Tasks (in order)

**C1. Setup, routing, API client, mock layer**
- Vite + React + TypeScript + Tailwind; React Router; TanStack Query (or simple hooks).
- `src/api/types.ts`: TypeScript types for every response in 5.3. `src/api/client.ts`: one function per endpoint; token stored in memory + localStorage; 401 redirects to login.
- Mock layer (MSW or an in-memory fake) that serves `/contracts/fixtures` and simulates behavior: upload creates items that progress `queued → processing → needs_review` over a few seconds; approve changes status; retry re-queues; duplicate filenames containing "copy" return `duplicate`.
- Done when: app runs with mock on and off via `VITE_USE_MOCK`.

**C2. Login and Upload**
- Login page (and a register option). Protected routes. Layout with navbar (logo, Dashboard, Upload, Export, user menu).
- Upload page: drag-and-drop zone and file picker, client-side checks (type, 10 MB, max 20 files), per-file list with status after submit using the `results` array (queued / duplicate / error with message).
- Done when: mixed batch shows per-file outcomes clearly.

**C3. Dashboard**
- Summary cards from `counts`; table of documents (filename, vendor, invoice no., total, status badge, issue/low-confidence indicators, time); filter tabs by status; search box; pagination.
- Auto-refresh by polling `GET /documents` every 3 seconds while any item is `queued` or `processing`; stop otherwise.
- Row click opens the review page. `failed` rows show a Retry button; `duplicate` rows show a link to the original.
- Done when: all 6 statuses render and update live in mock mode.

**C4. Split-screen Review page (the key screen)**
- Left: document viewer using `file_url` (PDF via `<iframe>`/pdf viewer, images via `<img>`, zoom in/out). Right: form of fields.
- Each field shows its label, input prefilled with `reviewed_value ?? value`, a confidence badge, **yellow highlight when `needs_review` is true**, and red border + message for fields tied to validation issues.
- Validation issues panel at top (errors red, warnings amber).
- Line items editable table (add/remove row).
- Buttons: **Save changes** (`PATCH`), **Approve** (disabled while blocking errors exist; show a "Approve anyway" option that sends `force: true` after confirmation), **Back**. After saving, refresh issues from the response.
- If a field has `bbox`, clicking the field highlights that region over the document; if not, skip gracefully.
- Read-only view for `approved`, `duplicate` (show the link to the original and the reason), and `failed` (show error message and Retry).
- Done when: the full review flow works on `document_detail_needs_review.json` in mock mode, including fixing the total mismatch and approving.

**C5. Export, polish and states**
- Export page or dashboard buttons: download CSV / JSON for approved documents (calls `GET /export`, handles auth header via fetch + blob download).
- Toasts for success/error, skeleton loaders, empty states ("No documents yet. Upload your first invoice"), friendly error screen.
- Done when: every screen handles loading, empty and failure.

**C6. Frontend deployment (early)**
- Deploy to Vercel with `VITE_API_BASE_URL` and `VITE_USE_MOCK=false` for production (deploy first with mock on if the backend isn't live yet, then flip). Provide the URL to A and Lead for CORS.
- Done when: public URL loads and login works against the live API.

**C7. Documentation and story assets** (`/docs`)
- `README.md` (root): problem, solution, features, architecture, tech stack, how to run locally with `docker-compose up`, env vars, deployed URLs, demo credentials, design decisions (idempotency via SHA-256 + unique index, retries with backoff, file security measures, why Redis instead of RabbitMQ, confidence threshold logic), known limitations, V2 roadmap link.
- `docs/architecture.md` plus diagram (Mermaid is fine, also exported as PNG): `Browser → API → Storage + DB → Redis queue → Worker → LLM → Validation → DB → Review UI → Export`.
- `docs/demo_script.md`: the 3-minute script below, with exact files to use and exact things to click.
- `docs/slides/`: 4 slides: Problem, Solution (screenshot), How it works and technical depth, Impact and roadmap.
- Done when: a stranger can clone, run, and understand the project from the README alone.

**C8. Demo preparation**
- Record a backup demo video (screen recording of the full flow on the live URL).
- Take screenshots for the slides.
- Done when: video exists and the demo script was rehearsed twice with the real sample pack.

### Demo script (3 minutes; C maintains this in `docs/demo_script.md`)
1. **Problem (20s):** "An accountant types hundreds of invoices by hand: slow and error-prone."
2. **Bulk upload (30s):** upload 6 sample files at once; dashboard shows statuses moving live.
3. **Review (60s):** open the invoice with the wrong total; show the red flag and a yellow low-confidence GSTIN; fix it in the split-screen; approve.
4. **Idempotency (20s):** re-upload `clean_invoice_copy.pdf` → "Duplicate" with a link to the original; mention business-level duplicate for `same_invoice_resaved.pdf`.
5. **Resilience (30s):** upload `failme.pdf`; show retries counting up, then Failed; click Retry.
6. **Export + impact (20s):** export CSV; "5 minutes of typing became 20 seconds".

---

## 10. Phase 2: Integration (Lead coordinates; start when each person's core tasks are done: A1 to A6, B1 to B8, C1 to C5)

**I1. A + B: swap stub for real extractor.** A sets `USE_STUB_EXTRACTOR=false`, imports the real functions, and swaps in B's `to_csv`/`to_json`. Fix any type mismatches in A's code, not by changing the contract. Done when: all 8 samples process end-to-end through the worker.

**I2. A + C: connect the real API.** C sets `VITE_USE_MOCK=false`. Fix mismatches (usually field names or null handling). Done when: the full UI flow works locally against the real API.

**I3. Full end-to-end on the live URLs (Lead runs this checklist)**
- [ ] Register/login on the live site
- [ ] Bulk upload of the 8 samples + `failme.pdf`
- [ ] Statuses progress live; clean sample is `approved` (auto) or `needs_review` as expected
- [ ] `wrong_total.pdf` shows a red `total_mismatch`; edit and approve works
- [ ] `blurry_invoice.png` shows yellow low-confidence fields
- [ ] `clean_invoice_copy.pdf` becomes `duplicate (same_file)`
- [ ] `same_invoice_resaved.pdf` becomes `duplicate (same_invoice)`
- [ ] `failme.pdf` retries then fails; Retry works
- [ ] CSV and JSON export download with correct data
- [ ] A different user cannot open the first user's document URL (404)
- [ ] Opening the stored file URL directly without a presigned signature is denied

**Checkpoint rule:** if one document cannot go upload → review → approve → export on the live URL, all new feature work stops until that is fixed.

---

## 11. Phase 3: Hardening (parallel again)

**H1. A:** file-security pass (verify magic-byte check, size limits, private bucket, presigned expiry, authorization on every endpoint, rate limit on login if time permits); worker-kill and retry demo verified on the live worker; structured logging.

**H2. B:** run the eval script on the live LLM; tune prompts for blurry/photo samples; make sure the demo files behave exactly as the demo script expects; load realistic seed data into the live DB (via A's seed script extension or API uploads under the demo user).

**H3. C:** polish UI, fix visual bugs, rehearse demo on the live URL, finish slides and README, record the backup video, add screenshots.

**H4. Lead:** bug triage board, merge fixes, final regression run of the I3 checklist, tag release `v1.0.0`.

**Feature freeze** happens when Phase 3 starts. After that, only bug fixes and demo practice.

---

## 12. Working Rules (everyone, including your AI)

1. One task = one branch = one small PR. Merge at least every 40 minutes of work.
2. Only touch your own folders. Need a change elsewhere? Open a GitHub issue assigned to the owner.
3. Contracts are frozen. Contract change request = issue + Lead approval + message to all.
4. Do not block on others: use stubs/mocks until Integration.
5. Every PR states how to verify it. Include test output or a screenshot.
6. Secrets never go in git. Update `.env.example` (via Lead) when adding a new variable.
7. If something is unclear, choose the simplest option consistent with the contract and note the assumption in the PR.
8. Nothing outside this file's scope gets built. Add ideas to `V2_IDEAS.md`.

**Cut list if time runs short (cut in this order):** bbox highlighting → analytics/summary cards → search box → "Approve anyway" force option → login rate limiting.
**Never cut:** deployment, database, async queue, review screen, duplicate detection, retry demo, validation flags, export, README.

---

## 13. V1 Definition of Done (Lead signs off)

- [ ] Public frontend URL and public API URL both live; login works; demo user documented in README
- [ ] Bulk upload of PDF/JPG/PNG with per-file results
- [ ] Async processing through Celery + Redis with live status updates in UI
- [ ] LLM extraction with per-field confidence
- [ ] Validation rules produce visible flags
- [ ] Split-screen review with edit, save, approve
- [ ] Same-file and same-invoice duplicate detection
- [ ] Retries with backoff, failed state, manual Retry button
- [ ] File security measures in place (magic-byte check, size limit, private storage, presigned URLs, per-user authorization)
- [ ] CSV and JSON export of approved documents
- [ ] PostgreSQL schema matches `contracts/schema.sql`
- [ ] README, architecture diagram, sample pack, demo script, 4 slides, backup video
- [ ] I3 checklist fully passes on the live URLs
- [ ] `v1.0.0` tag created

---

## 14. V2 Parking Lot (do NOT build now)

Record ideas in `V2_IDEAS.md` as bullet points with a one-line reason. Starting candidates: multi-tenant organizations and roles, custom field templates, DOCX export, audit log of edits, analytics dashboard (auto-approval rate, time saved), contracts and forms document types, webhook/ERP integrations, domain-specific customization based on the team's expertise, bounding-box highlight improvements, RabbitMQ migration, WebSocket/SSE live updates.

---

## 15. Quick Start Prompts (each person pastes one of these with this file)

**Lead + Person A (Yash):**
> "I am both the Team Lead and Person A (Backend + Infra). Read V1_BUILD_PLAN.md fully. First complete Lead Step 0 artifacts and freeze the contracts. Then implement tasks A1 to A8 in order, following the frozen contracts exactly and using the stub extractor until B's module is integrated. Also coordinate integration, merges, deployment checks, and final QA as Lead. After each task, show me how to verify it against its 'Done when' list."

**Lead:**
> "I am the Lead. Using V1_BUILD_PLAN.md, generate all Step 0 artifacts: repo structure, `contracts/schema.sql`, `contracts/extraction_schema.json`, `contracts/API_CONTRACT.md`, all fixtures in `contracts/fixtures/`, `docker-compose.yml`, `.env.example`, `CODEOWNERS`, PR template, and a list of GitHub issues for every task ID."

**Person A:**
> "I am Person A (Backend + Infra). Read V1_BUILD_PLAN.md fully. Implement tasks A1 to A8 in order, following the frozen contracts exactly, using the stub extractor until B's module is integrated. After each task, show me how to verify it against its 'Done when' list."

**Person B:**
> "I am Person B (AI + Data). Read V1_BUILD_PLAN.md fully. Implement tasks B1 to B8 in order inside `backend/app/extraction` and `/samples`, with the exact function signatures from Section 5.5 and the validation rules from Section 5.6. After each task, show me how to verify it against its 'Done when' list."

**Person C:**
> "I am Person C (Frontend + Story). Read V1_BUILD_PLAN.md fully. Implement tasks C1 to C8 in order in `/frontend` and `/docs`, using a mock API built from `/contracts/fixtures` until the backend is ready. After each task, show me how to verify it against its 'Done when' list."
