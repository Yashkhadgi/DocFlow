# DocFlow Extraction Package (`app.extraction`)

This package is owned by **Person B (AI + Data)**. It contains the core AI vision extraction engine, schema validation rules, confidence calibration, duplicate detection, and CSV/JSON export formatters for DocFlow V1.

---

## 1. Public API Interface (`app.extraction`)

The package exports the frozen Python contracts defined in **Section 5.5 of `V1_BUILD_PLAN.md`**:

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

### Function Specifications

| Function | Signature | Description |
|---|---|---|
| `extract` | `(file_bytes: bytes, mime_type: str) -> ExtractionResult` | Calls Anthropic Claude Vision API (`LLM_MODEL`). Validates inputs (corrupted/encrypted PDFs, empty files, size limits) before API call. Retries up to 2 times internally on malformed JSON. Normalizes ISO dates (`YYYY-MM-DD`) and plain decimals (`10000.00`). Raises `ExtractionError` with `retryable=True/False`. |
| `validate` | `(result: ExtractionResult) -> list[ValidationIssue]` | **Pure function (no I/O)**. Evaluates business rules (`total_mismatch`, `line_items_mismatch`, `invalid_gstin`, `invalid_date`, `missing_required`) using `Decimal` precision. |
| `needs_review` | `(result: ExtractionResult, issues: list[ValidationIssue], threshold: float \| None = None) -> bool` | Returns `True` if any `ValidationIssue` has `severity == 'error'`, or if any counted field falls strictly below the confidence threshold (`CONFIDENCE_THRESHOLD`, default 0.85). |
| `low_confidence_fields` | `(result: ExtractionResult, threshold: float \| None = None) -> list[str]` | Returns list of counted field names (`vendor_name`, `invoice_number`, `invoice_date`, `total`, `gstin`, `subtotal`, `tax`) with confidence `< threshold`. |
| `find_business_duplicate` | `(result: ExtractionResult, existing: list[dict]) -> DuplicateMatch \| None` | **Pure function**. Normalizes vendor name (lowercase, legal suffix stripping) and invoice number (alphanumeric tokenization, leading zero stripping) and returns the first matching document ID. |
| `to_csv` | `(docs: list[dict]) -> str` | Generates RFC 4180 CSV matching Section 5.3 columns with one row per line item. Uses final reviewed values over raw values. |
| `to_json` | `(docs: list[dict]) -> str` | Formats documents and line items into Section 5.3 JSON array. |

---

## 2. Environment Variables

| Variable | Default | Purpose |
|---|---|---|
| `ANTHROPIC_API_KEY` | *(Required)* | Anthropic API key for Vision LLM extraction. |
| `LLM_MODEL` | `claude-sonnet-5-5` | Vision model identifier used for extraction. |
| `CONFIDENCE_THRESHOLD` | `0.85` | Float threshold between `0.0` and `1.0` determining whether a field routes to human review. |

---

## 3. Accuracy Benchmarks & Latency

- **Overall Accuracy:** **90.6% to 95.3%** (58/64 to 61/64 fields matched across the 8 sample documents). Model output varies slightly between runs.
  - **100.0%** across all 7 legible, clean, scanned, photographed, and flagged invoices.
  - **All misses occurred exclusively on `blurry_invoice.png`** where heavy Gaussian blur made text unreadable, correctly assigning low confidence and safely routing to review.
- **Confidence Calibration:**
  - Average confidence on correct fields: **0.90 to 0.93**
  - Average confidence on unreadable/blurred fields: **0.17 to 0.24**
  - **Zero instances of false high-confidence hallucinations.**
- **Average Processing Latency:** **4.6 to 5.6 seconds** per document (measured live).
- **Token Usage (Avg):** ~2,000 input tokens / ~450 output tokens per document.
- **Operating Cost:** **$0.86 per 100 invoices** ($0.0086 per invoice based on Anthropic pricing for `claude-sonnet-5-5` at $2.00/1M input and $10.00/1M output tokens; source: https://www.anthropic.com/pricing, checked 2026-10-06).

---

## 4. Execution & Verification Commands

```powershell
# Set PYTHONPATH to backend
$env:PYTHONPATH="backend"

# 1. Run live extraction CLI on an invoice
python -m app.extraction.cli samples/invoices/clean_invoice.pdf

# 2. Run the 3-minute demo verification script
python -m app.extraction.verify_demo

# 3. Run the evaluation & benchmarking suite
python backend/scripts/eval_samples.py

# 4. Run the full pytest test suite (52 tests)
python -m pytest backend/app/extraction/tests/
```

---

## 5. Troubleshooting & Error Handling

| Scenario | Symptom / Error | Resolution |
|---|---|---|
| **Missing API Key** | `ExtractionError: ANTHROPIC_API_KEY environment variable is not set` | Ensure `.env` exists in repo root with `ANTHROPIC_API_KEY=sk-ant-...`. |
| **Rate Limit Exceeded (429)** | `ExtractionError: Anthropic API rate limit exceeded (retryable=True)` | The Celery worker will automatically retry with exponential backoff. |
| **Request Timeout** | `ExtractionError: Anthropic API request timed out (retryable=True)` | Automatic worker retry with backoff. |
| **Corrupted / Invalid File** | `ExtractionError: Invalid PDF header / corrupted (retryable=False)` | Landed immediately in `failed` state with user-facing message; no wasted worker retries. |
| **Encrypted PDF** | `ExtractionError: PDF is password-protected (retryable=False)` | Prompts user in UI to upload an unlocked PDF. |

---

## 6. Known Limitations in V1

- **Bounding Boxes (`bbox`):** In V1, `bbox` fields are optional and set to `null`. The split-screen UI renders gracefully without them.
- **Handwritten Invoices:** Heavy cursive handwriting may score lower confidence (< 0.85) and automatically route to human review (`needs_review`).
- **Multi-page Invoices:** Invoices with up to 100 pages are supported; line items are extracted sequentially with totals captured from the summary page.
- **Currencies:** Defaults to Indian GST invoices (`INR`), but dynamically adapts to global currency codes (`USD`, `EUR`, `GBP`).
