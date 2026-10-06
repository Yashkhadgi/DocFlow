#!/usr/bin/env bash
set -euo pipefail

# scripts/create_issues.sh
# Automates creation of GitHub Issues for DocFlow V1 tasks from .github/ISSUES.md and V1_BUILD_PLAN.md.

DRY_RUN=false

for arg in "$@"; do
    case "$arg" in
        --dry-run|-d)
            DRY_RUN=true
            ;;
        --help|-h)
            echo "Usage: $0 [--dry-run]"
            echo ""
            echo "Options:"
            echo "  --dry-run, -d    Print issues and labels that would be created without calling GitHub API"
            echo "  --help, -h       Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown argument: $arg"
            echo "Usage: $0 [--dry-run]"
            exit 1
            ;;
    esac
done

echo "============================================================"
echo "DocFlow GitHub Issues Creator"
if [ "$DRY_RUN" = true ]; then
    echo "Mode: DRY RUN (no API calls will be made)"
else
    echo "Mode: LIVE (issues and labels will be created on GitHub)"
fi
echo "============================================================"

# Pre-flight check for gh CLI
if ! command -v gh >/dev/null 2>&1; then
    if [ "$DRY_RUN" = false ]; then
        echo "Error: 'gh' CLI is not installed or not in PATH."
        echo "Install GitHub CLI (https://cli.github.com/) and run 'gh auth login' before executing this script."
        exit 1
    else
        echo "Notice: 'gh' CLI not found on local PATH. Continuing in dry-run mode."
    fi
fi

# In live mode, verify gh authentication
if [ "$DRY_RUN" = false ]; then
    echo "Checking GitHub authentication status..."
    if ! gh auth status >/dev/null 2>&1; then
        echo "Error: You are not logged into GitHub CLI."
        echo "Please run 'gh auth login' first, then re-run this script."
        exit 1
    fi
    echo "Authenticated successfully."
fi

# Label definitions: name, color (hex without #), description
declare -a LABELS=(
    "lead:5319E7:Lead tasks and repository setup"
    "backend:1D76DB:Person A: Backend API, database, and infrastructure"
    "ai:0E8A16:Person B: AI extraction, prompts, and validation"
    "frontend:F9D0C4:Person C: React frontend, dashboard, and review UI"
    "integration:FBCA04:Phase 2: End-to-end integration tasks"
    "hardening:D93F0B:Phase 3: Security, evaluation, and release hardening"
)

ensure_labels() {
    echo ""
    echo "--- Step 1: Ensuring Labels Exist ---"
    for item in "${LABELS[@]}"; do
        IFS=':' read -r name color desc <<< "$item"
        if [ "$DRY_RUN" = true ]; then
            echo "[DRY-RUN] Ensure label '$name' (color: #$color, description: '$desc')"
        else
            echo "Checking label '$name'..."
            if ! gh label list --json name -q '.[].name' 2>/dev/null | grep -Fxq "$name"; then
                gh label create "$name" --color "$color" --description "$desc"
                echo "  Created label: $name"
            else
                echo "  Label '$name' already exists."
            fi
        fi
    done
}

get_label_for_task() {
    local id="$1"
    case "$id" in
        L*|l*)         echo "lead" ;;
        A*|a*)         echo "backend" ;;
        B*|b*)         echo "ai" ;;
        C*|c*)         echo "frontend" ;;
        I*|i*)         echo "integration" ;;
        H*|h*)         echo "hardening" ;;
        *)             echo "backend" ;;
    esac
}

TOTAL_CREATED=0

create_task_issue() {
    local id="$1"
    local title="$2"
    local desc="$3"
    local checklist="$4"

    local label
    label=$(get_label_for_task "$id")
    local full_title="[$id] $title"

    local body
    body=$(cat <<EOF
## Description
$desc

## Done When
$checklist
EOF
)

    TOTAL_CREATED=$((TOTAL_CREATED + 1))

    if [ "$DRY_RUN" = true ]; then
        echo ""
        echo "============================================================"
        echo "[DRY-RUN] Issue #$TOTAL_CREATED: $full_title"
        echo "Label: $label"
        echo "Body:"
        echo "$body"
        echo "============================================================"
    else
        echo "Creating issue #$TOTAL_CREATED: $full_title [$label]..."
        gh issue create \
            --title "$full_title" \
            --label "$label" \
            --body "$body"
    fi
}

ensure_labels

echo ""
echo "--- Step 2: Creating Issues from .github/ISSUES.md ---"

# ============================================================
# Lead Tasks
# ============================================================
create_task_issue "L1" "Create repo structure and placeholder files" \
"Create the repository structure from Section 4 of V1_BUILD_PLAN.md. Add empty placeholder files so every role has a folder ready for parallel work." \
"- [ ] Root directory structure created (/contracts, /backend/app, /backend/app/extraction, /frontend, /docs, /samples, /scripts)
- [ ] Placeholder files committed in each team-owned folder"

create_task_issue "L2" "Commit frozen contracts and fixtures" \
"Copy Sections 5.1 to 5.6 into /contracts (schema.sql, extraction_schema.json, API_CONTRACT.md). Create fixtures in /contracts/fixtures/ using example payloads in Section 5.3 (one for each status)." \
"- [ ] contracts/schema.sql committed
- [ ] contracts/extraction_schema.json committed
- [ ] contracts/API_CONTRACT.md committed
- [ ] Mock fixtures created for all 6 document statuses (queued, processing, needs_review, approved, failed, duplicate)"

create_task_issue "L3" "Add docker-compose local stack" \
"Configure docker-compose.yml with services: db (postgres:15), redis, minio (+ bucket auto-creation), api (uvicorn, port 8000), worker (celery), and frontend (vite dev, port 5173). Use environment variables from .env.example." \
"- [ ] docker-compose.yml configures db, redis, minio, api, worker, and frontend
- [ ] .env.example documents all required environment variables
- [ ] Local stack boots cleanly with 'docker compose up'"

create_task_issue "L4" "Configure GitHub branch protection, CODEOWNERS, PR template, issues, and project board" \
"Set up GitHub repository infrastructure: protect main branch (no direct push, PR required, 1 approval, no force push), .github/CODEOWNERS, PR template, issues for all task IDs, and Project board with To do / In progress / In review / Done." \
"- [ ] Branch protection rules configured on main
- [ ] .github/CODEOWNERS committed
- [ ] .github/pull_request_template.md committed
- [ ] GitHub issues created for all tasks
- [ ] Project board set up with To do / In progress / In review / Done columns"

create_task_issue "L5" "Announce contract freeze" \
"Announce contract freeze to the team: 'Contracts are frozen. Any change requires opening an issue, Lead approval, and team notification.'" \
"- [ ] Contract freeze communicated to all team members
- [ ] Team agreement established that contracts are locked"

create_task_issue "L6" "Create deployment and service accounts" \
"Provision cloud infrastructure: Neon DB, Upstash/Render Redis, Cloudflare R2 bucket, Anthropic API key, Render API/worker, and Vercel frontend projects." \
"- [ ] Neon PostgreSQL database provisioned
- [ ] Redis instance provisioned
- [ ] Cloudflare R2 storage bucket provisioned
- [ ] Anthropic API key acquired and distributed
- [ ] Render and Vercel projects initialized"

# ============================================================
# Person A: Backend + Infra
# ============================================================
create_task_issue "A1" "Project skeleton and database" \
"FastAPI app with /api/v1 prefix, /health, CORS from CORS_ORIGINS, and centralized error handler producing Section 5.3 format. SQLAlchemy models matching schema.sql exactly (including partial unique index uq_documents_user_hash_primary); Alembic initial migration equal to schema.sql. Dockerfile wired into docker-compose." \
"- [ ] docker compose up starts db, redis, minio, api with no crash loops
- [ ] GET /api/v1/health returns {\"status\":\"ok\"}
- [ ] Migration applies cleanly on an empty DB
- [ ] Models-vs-schema.sql sanity test passes"

create_task_issue "A2" "Auth" \
"POST /auth/register, POST /auth/login; bcrypt password hashing; JWT HS256 tokens; dependency get_current_user. Seed script scripts/seed.py that creates demo user demo@docflow.app / Demo@1234." \
"- [ ] Register and login endpoints work per contract
- [ ] Protected route returns 401 without token
- [ ] Unit tests cover wrong password, duplicate email, and expired token
- [ ] Demo user seed script runs idempotently"

create_task_issue "A3" "Storage service and upload endpoint" \
"services/storage.py: put_object, get_object, presign_get_url(key, expires), private bucket, auto-create bucket in local. POST /documents/upload exactly as in 5.3: magic-byte type check (%PDF, JPEG, PNG), size limit (10MB), file-count limit (20), SHA-256 computation, random keys (users/{user_id}/{uuid4}), same-file duplicate detection, and per-file results array." \
"- [ ] Uploading a PDF, duplicate PDF, and renamed .exe gives queued / duplicate / unsupported_type
- [ ] Concurrent upload of same file twice does not create duplicate non-duplicate rows (relies on unique index)
- [ ] Presigned URLs generated with short expiration"

create_task_issue "A4" "Celery worker and job lifecycle" \
"workers/celery_app.py, task process_document(document_id). Flow: load document, set processing and job processing (increment attempts), download file from storage, call extractor (stub or real), run validate(), business-duplicate check via find_business_duplicate(), persist fields/line items/issues, decide status: needs_review if needs_review() is true, else approved with auto_approved=true. Mark job succeeded. Idempotent task with acks_late=True." \
"- [ ] Uploading a file drives it to needs_review or approved using the stub
- [ ] Killing and restarting worker mid-job does not corrupt or duplicate rows
- [ ] Re-executed task replaces rows in single transaction"

create_task_issue "A5" "Retries, backoff, failure handling" \
"On exception: retry with exponential backoff (e.g. 5s, 20s, 60s) up to JOB_MAX_ATTEMPTS; each retry updates jobs.attempts and last_error; after last attempt set document failed with readable error_message. Debug env flag FORCE_FAIL_FILENAME_CONTAINS=failme. POST /documents/{id}/retry per contract." \
"- [ ] File named failme.pdf transitions: processing -> retries with attempts count -> failed
- [ ] POST /documents/{id}/retry resets attempts, sets status queued, and re-enqueues task
- [ ] Retry completes when failure condition is removed"

create_task_issue "A6" "Read/review endpoints" \
"GET /documents (filters, pagination, counts, search), GET /documents/{id} (with presigned file_url, 404 for other users' docs), PATCH /documents/{id}/fields (sets reviewed_value, clears needs_review, re-runs validate()), and POST /documents/{id}/approve (with force flag), all exactly per Section 5.3." \
"- [ ] Responses validate against contracts/fixtures shapes
- [ ] PATCH re-validates and updates validation issues
- [ ] Other users' documents return 404, not 403
- [ ] Approve blocked when error-severity issues exist without force"

create_task_issue "A7" "Export endpoint" \
"GET /export using to_csv / to_json from B (minimal local fallback until B delivers). Uses final values (reviewed_value over value). Both formats download with Content-Disposition: attachment. CSV columns match Section 5.3 exactly (one row per line item)." \
"- [ ] CSV and JSON formats download with correct headers and content for approved documents
- [ ] CSV columns match Section 5.3 contract exactly"

create_task_issue "A8" "Backend deployment" \
"Deploy API and worker to Render from the same Dockerfile. Connect Neon Postgres (sslmode=require), Redis, Cloudflare R2 (S3_ENDPOINT_URL). Run migrations on deploy; run seed script once. Set CORS_ORIGINS to frontend Vercel URL." \
"- [ ] Public GET /health works on live URL
- [ ] Login with demo user works on live URL
- [ ] Upload on live URL reaches needs_review/approved via live worker"

# ============================================================
# Person B: AI + Data
# ============================================================
create_task_issue "B1" "Sample pack" \
"Create /samples/invoices/ with 8 diverse files and matching /samples/expected/<name>.json ground truth files in 5.4 format (clean, scanned, photo, blurry, wrong total, bad GSTIN, clean copy, same invoice resaved) plus failme.pdf. Document in samples/README.md." \
"- [ ] All 8 invoice sample files and expected JSONs exist
- [ ] failme.pdf included for retry demo
- [ ] samples/README.md lists what each sample tests"

create_task_issue "B2" "extract()" \
"types.py: Pydantic models FieldValue, LineItem, ExtractionResult, ValidationIssue, DuplicateMatch, ExtractionError. extractor.py: send file to Anthropic Messages API using LLM_MODEL, force JSON output, parse into ExtractionResult. Normalize dates to ISO and money to decimal strings. cli.py to test." \
"- [ ] CLI 'python -m app.extraction.cli <file>' returns valid JSON and issues for all 8 samples
- [ ] Normalized ISO dates and decimal strings parsed accurately"

create_task_issue "B3" "Prompt design and robustness" \
"prompts.py: system prompt defining fields, null handling, calibrated confidence scores, ISO dates, and JSON-only output. Retry up to 2 times on malformed JSON; strip markdown fences; raise ExtractionError on failure. Create eval script scripts/eval_samples.py." \
"- [ ] scripts/eval_samples.py compares output to /samples/expected and prints per-field accuracy
- [ ] Target >= 90% accuracy on clean/scanned/photo samples
- [ ] Blurry invoice correctly yields lower confidence scores"

create_task_issue "B4" "validate()" \
"Implement every validation rule in Section 5.6 using Decimal math: total_mismatch, line_items_mismatch, invalid_gstin, invalid_date, missing_required. Unit tests for each rule (pass, fail, edge cases)." \
"- [ ] wrong_total.pdf yields total_mismatch
- [ ] bad_gstin.pdf yields invalid_gstin
- [ ] Clean sample yields no validation errors
- [ ] All unit tests pass using Decimal calculations"

create_task_issue "B5" "Review rules" \
"needs_review() and low_confidence_fields() per Section 5.5; threshold from CONFIDENCE_THRESHOLD env (default 0.85). Required fields plus gstin, subtotal, and tax count toward threshold." \
"- [ ] Unit tests cover threshold boundaries
- [ ] Error-severity validation issue forces needs_review to true
- [ ] low_confidence_fields() returns names of fields below threshold"

create_task_issue "B6" "find_business_duplicate()" \
"find_business_duplicate(result, existing): normalize vendor (lowercase, strip punctuation and suffixes like pvt/ltd/llp) and invoice number (uppercase, strip spaces and leading zeros); both must match." \
"- [ ] Matches 'Acme Traders Pvt. Ltd.' vs 'ACME TRADERS PVT LTD'
- [ ] Matches 'INV-001' vs 'inv 001'
- [ ] Unit tests pass for normalization edge cases"

create_task_issue "B7" "Export helpers" \
"to_csv() and to_json() exactly per Section 5.3 export specification (columns, order, one row per line item, csv quoting). Input rows use final values." \
"- [ ] Output opens correctly in Excel/Sheets with correct header order
- [ ] JSON output structured properly with final values
- [ ] Unit tests verify headers and row counts"

create_task_issue "B8" "Package and document extraction module" \
"__init__.py exports exactly the functions in Section 5.5 (extract, validate, needs_review, low_confidence_fields, find_business_duplicate, to_csv, to_json). backend/app/extraction/README.md covers CLI, eval script, tests, env vars, limitations." \
"- [ ] Person A can import all extraction functions with no changes
- [ ] Extraction README is complete and accurate"

# ============================================================
# Person C: Frontend + Story
# ============================================================
create_task_issue "C1" "Setup, routing, API client, mock layer" \
"Vite + React + TypeScript + Tailwind CSS; React Router; TanStack Query. src/api/types.ts for Section 5.3 responses. src/api/client.ts with auth header handling and 401 redirect. Mock layer serving /contracts/fixtures toggled by VITE_USE_MOCK." \
"- [ ] App runs with mock on and off via VITE_USE_MOCK
- [ ] Authenticated routing configured
- [ ] Mock simulates realistic upload -> queued -> processing -> needs_review progression"

create_task_issue "C2" "Login and upload" \
"Login page and register option. Protected routes. Navbar layout. Upload page: drag-and-drop zone, file picker, client-side checks (types, 10MB, max 20 files), per-file status list after submit using results array." \
"- [ ] Login and register work against mock and real API
- [ ] Mixed upload batch shows per-file outcomes clearly (queued / duplicate / unsupported_type)"

create_task_issue "C3" "Dashboard" \
"Summary cards from counts. Documents table with status badges, issue indicators, filter tabs, search, and pagination. Auto-refresh polling every 3 seconds while items are queued/processing. Retry button for failed documents; link to duplicate originals." \
"- [ ] All 6 statuses render with designated color badges
- [ ] Auto-refresh polling updates live without flicker
- [ ] Clicking a document row opens the review page"

create_task_issue "C4" "Split-screen review page" \
"Split-screen review page: left document viewer (PDF iframe/image zoom), right form of fields. Confidence badges, yellow highlight for needs_review, red border for validation issues. Editable line items table. Save changes (PATCH) and Approve buttons (with force option). Read-only view for approved, duplicate, and failed documents." \
"- [ ] Full review flow works on document_detail_needs_review.json in mock mode
- [ ] Editing fields re-validates and clears issues
- [ ] Approving transitions document to approved state"

create_task_issue "C5" "Export, polish, and states" \
"Export buttons to download CSV/JSON for approved documents (calls GET /export). Toast notifications for success/error, skeleton loaders, empty states, and user-friendly error screen." \
"- [ ] CSV and JSON export downloads work from UI
- [ ] Loading, empty, and failure states handled on every view"

create_task_issue "C6" "Frontend deployment" \
"Deploy to Vercel with VITE_API_BASE_URL and VITE_USE_MOCK=false. Provide URL to Person A and Lead for CORS setup." \
"- [ ] Public Vercel URL loads properly
- [ ] Login and dashboard function against live backend API"

create_task_issue "C7" "Documentation and story assets" \
"Complete root README.md (problem, solution, architecture diagram, stack, local setup, deployed URLs, demo credentials, design decisions, limitations). Create docs/architecture.md, docs/demo_script.md, and 4 slide decks in docs/slides/." \
"- [ ] README is comprehensive and understandable for newcomers
- [ ] Architecture diagram and 3-minute demo script completed
- [ ] 4 presentation slides created"

create_task_issue "C8" "Demo preparation" \
"Rehearse 3-minute demo script with real sample pack. Record backup demo screen video on live URL. Take screenshots for slides and documentation." \
"- [ ] Backup video recording exists
- [ ] Demo script rehearsed twice successfully on live URL"

# ============================================================
# Phase 2: Integration
# ============================================================
create_task_issue "I1" "A + B swap stub for real extractor" \
"A sets USE_STUB_EXTRACTOR=false, imports real extraction functions, and swaps in B's to_csv/to_json. Fix any caller-side type mismatches without modifying contracts." \
"- [ ] All 8 sample invoices process end-to-end through the live worker
- [ ] Fields, line items, issues, and duplicates persist accurately in DB"

create_task_issue "I2" "A + C connect the real API" \
"C sets VITE_USE_MOCK=false. Connect frontend to running FastAPI backend. Fix any payload or response handling mismatches." \
"- [ ] Full UI flow (upload -> dashboard -> review -> approve -> export) works locally against real API
- [ ] Presigned file URLs load documents correctly in viewer"

create_task_issue "I3" "Full end-to-end live URL checklist" \
"Lead runs comprehensive verification checklist on live URLs: register, bulk upload of 8 samples + failme.pdf, review and approve with mismatch fix, duplicate handling, retry flow, export downloads, and security verification." \
"- [ ] All 11 checklist items in Section 10 pass on live URLs
- [ ] End-to-end user workflow functions cleanly"

# ============================================================
# Phase 3: Hardening
# ============================================================
create_task_issue "H1" "A file-security and retry pass" \
"Verify magic-byte validation, size limits, private bucket policies, presigned URL expiry (5 min), endpoint authorization, worker recovery on mid-job crash, and structured logging with document_id and job attempts." \
"- [ ] Direct storage access without signature is denied
- [ ] Cross-user access returns 404
- [ ] Worker restart recovers jobs cleanly without duplicate records"

create_task_issue "H2" "B live LLM evaluation and demo data tuning" \
"Run evaluation script on live Anthropic API. Fine-tune prompts for blurry/photo samples. Ensure demo files behave consistently with demo script expectations. Seed demo user with realistic invoice data." \
"- [ ] Live LLM extraction meets accuracy goals on sample pack
- [ ] Demo files behave predictably for 3-minute pitch"

create_task_issue "H3" "C UI polish, docs, slides, demo rehearsal" \
"Polish UI interactions and animations. Rehearse demo on live URL. Finalize slides, README, and backup recording." \
"- [ ] UI looks clean, modern, and professional
- [ ] Live demo rehearsed with backup recording ready"

create_task_issue "H4" "Lead final regression and v1.0.0 tag" \
"Lead manages bug triage board, merges remaining fixes, executes final regression run of I3 checklist, and tags release v1.0.0." \
"- [ ] All blocking bugs resolved
- [ ] Final regression checklist passes
- [ ] Git release tag v1.0.0 pushed"

echo ""
echo "============================================================"
if [ "$DRY_RUN" = true ]; then
    echo "Dry run completed successfully! Total issues previewed: $TOTAL_CREATED"
    echo "To create these issues on GitHub, run: ./scripts/create_issues.sh"
else
    echo "Completed successfully! Total issues created on GitHub: $TOTAL_CREATED"
fi
echo "============================================================"
