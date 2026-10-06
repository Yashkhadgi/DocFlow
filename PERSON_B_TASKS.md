# PERSON B (AI + Data): Task Prompts for the AI Coding Assistant

> **Instructions for the AI assistant reading this file**
>
> I am **Person B (AI + Data)** on the DocFlow project. First read `V1_BUILD_PLAN.md` fully (it is in the repo root). This file contains my tasks **B1 to B8**, in order.
>
> ## Rules (non-negotiable)
> 1. Edit **only** `/backend/app/extraction` and `/samples` (plus `backend/scripts/eval_samples.py` as named in B3). Never touch other folders.
> 2. Contracts in Section 5 of `V1_BUILD_PLAN.md` (5.3 export format, 5.4 extraction JSON, 5.5 Python interface, 5.6 validation rules) are **frozen**. Do not rename fields, change types, or change function signatures. If something looks wrong, tell me, do not change it.
> 3. Python 3.11, Pydantic v2, `pytest` for tests, the official `anthropic` SDK for the LLM. Use `Decimal` for all money math, never floats.
> 4. Secrets only via env vars (`ANTHROPIC_API_KEY`, `LLM_MODEL`, `CONFIDENCE_THRESHOLD`). Never hardcode the model name or key. Never log full document contents.
> 5. Work on **one task at a time**. When a task is finished, **stop**, show me the exact commands to verify its "Done when" list, and **wait for me to say "next"** before starting the next task.
> 6. If a requirement is ambiguous, pick the simplest option that satisfies the contract and tell me your assumption in one line.
> 7. Keep each task small enough for a single PR (branch name suggestion is given per task).
>
> Start with **B1** when I say "start".

---

## B1. Sample pack (branch: `feat/b1-samples`)

**Goal:** Create the test data everything else is tested against.

**Do this:**
Create `/samples/invoices/` with these files:

| # | File | What it tests |
|---|---|---|
| 1 | `clean_invoice.pdf` | Clean digital invoice, valid GSTIN, correct totals, 3 line items |
| 2 | `scanned_invoice.pdf` | Scanned / slightly skewed look |
| 3 | `photo_invoice.jpg` | Phone-photo look of an invoice |
| 4 | `blurry_invoice.png` | Low quality, should produce low-confidence fields |
| 5 | `wrong_total.pdf` | total != subtotal + tax (everything else correct) |
| 6 | `bad_gstin.pdf` | Invalid GSTIN format (everything else correct) |
| 7 | `clean_invoice_copy.pdf` | **Byte-identical** copy of #1 (same-file duplicate test) |
| 8 | `same_invoice_resaved.pdf` | Same vendor name and invoice number as #1 but **different bytes** (business duplicate test) |
| 9 | `failme.pdf` | Any valid PDF, used for the retry demo |

Requirements:
- Realistic **fake** Indian invoices: INR currency, GSTIN in valid format (`^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$`), vendor names, invoice numbers, dates in the past. No real company data.
- Generate the digital PDFs from an HTML template (HTML to PDF, e.g. WeasyPrint or headless Chromium) via a small script I can re-run, saved as `/samples/generate_samples.py`.
- For `scanned`, `photo`, `blurry`: write an image-processing step in the same script (rasterize, add slight rotation/noise/perspective, heavy blur for blurry, save as PDF/JPG/PNG). Tell me honestly if any of these would look better done by hand (print and scan or photograph) and what I should do.
- Create `/samples/expected/<name>.json` for each sample in the exact **Section 5.4** format (ground truth). For `blurry_invoice.png` the expected values are still the true values.
- `wrong_total.pdf` and `bad_gstin.pdf` must trigger **only** their own rule.
- Write `/samples/README.md` listing what each file tests.

**Done when:** all files and expected JSONs exist, #7 is byte-identical to #1 (verify with `sha256sum`), #8 differs in bytes but has the same vendor + invoice number, and `samples/README.md` exists.

---

## B2. `extract()` basics (branch: `feat/b2-extract`)

**Goal:** Call the vision LLM and return a structured `ExtractionResult`.

**Do this:** Inside `backend/app/extraction/`:

1. `types.py`: Pydantic v2 models: `FieldValue(value: str | None, confidence: float, bbox: dict | None)`, `LineItem(description, quantity, rate, amount, confidence)` (money/qty as strings), `ExtractionResult(document_type="invoice", fields: dict[str, FieldValue], line_items: list[LineItem], raw_model_output: str | None)`, `ValidationIssue(rule, severity, field_name, message)`, `DuplicateMatch(document_id, reason)`, and `ExtractionError(Exception)`. Must serialize to exactly the Section 5.4 JSON. Field names: `vendor_name, invoice_number, invoice_date, gstin, currency, subtotal, tax, total`. Confidence must be between 0 and 1.
2. `extractor.py`: `extract(file_bytes: bytes, mime_type: str) -> ExtractionResult`.
   - PDF goes as a `document` content block (base64, `application/pdf`); JPG/PNG go as `image` blocks (base64 with correct media_type).
   - Read `ANTHROPIC_API_KEY` and `LLM_MODEL` from env. Use temperature 0, a sensible `max_tokens`, and a request timeout.
   - Force JSON-only output, parse it into `ExtractionResult`.
   - After parsing, **normalize**: dates to ISO `YYYY-MM-DD`, money to plain decimal strings (dot, no thousands separators, no currency symbols). Missing field => `value: null`, `confidence: 0.0`.
   - Use a minimal placeholder system prompt for now (B3 replaces it).
3. `cli.py`: `python -m app.extraction.cli <file>` prints the JSON result (and validation issues if `validate` exists yet, otherwise skip gracefully).
4. `.env.example` is owned by the Lead, so do not edit it. Just read the env vars.

**Done when:** `python -m app.extraction.cli samples/invoices/<each of the 8 files>` returns valid JSON in the 5.4 shape for all 8 samples. Show me the commands and what a correct output looks like.

---

## B3. Prompt design and robustness (branch: `feat/b3-prompts`)

**Goal:** Reliable, well-calibrated extraction.

**Do this:**
1. `prompts.py`: a system prompt that
   - defines every field precisely (vendor_name, invoice_number, invoice_date, gstin, currency, subtotal, tax, total, and line items),
   - says "return `null` and confidence `0` when a field is not present, never guess",
   - defines **confidence calibration** (explain what ~0.95, ~0.7, ~0.4 mean; low for blurry/ambiguous text),
   - requires ISO dates and plain decimal money strings,
   - requires JSON only, no prose, no markdown.
2. In `extractor.py`: strip markdown fences if present; if output is not valid JSON or fails the Pydantic model, **retry up to 2 times**, including the parse/validation error in the retry message; after that raise `ExtractionError`.
3. Handle timeouts and API errors (rate limit, connection, 5xx) by raising `ExtractionError` with a clear message (A's worker will retry at its level).
4. Never log full document contents (log only filename-free metadata such as size, mime type, attempt number).
5. Create `backend/scripts/eval_samples.py` (path as named in the plan): runs `extract()` on every file in `/samples/invoices`, compares with `/samples/expected/*.json`, and prints **per-field accuracy** plus average confidence per sample. Money compared as `Decimal`; dates as ISO; strings compared case-insensitively and whitespace-trimmed.
6. Tests: mock the Anthropic client to test fence stripping, retry-on-bad-JSON (success on 2nd attempt, failure after 3 attempts raising `ExtractionError`), and API error handling.

**Done when:** the eval script runs and prints a per-field accuracy table; accuracy is **at least 90%** on clean/scanned/photo samples; the blurry sample shows visibly lower confidence; mocked retry tests pass.

---

## B4. `validate()` (branch: `feat/b4-validate`)

**Goal:** Business rules that produce visible red/amber flags.

**Do this:** `validators.py` with `validate(result: ExtractionResult) -> list[ValidationIssue]`, a **pure function (no I/O)**, implementing exactly Section 5.6:

| Rule | Severity | Logic |
|---|---|---|
| `total_mismatch` | error | `abs((subtotal + tax) - total) > 0.01` (skip if any of the three is missing) |
| `line_items_mismatch` | warning | `abs(sum(line amounts) - subtotal) > 0.01` (skip if no line items or no subtotal) |
| `invalid_gstin` | error | GSTIN present and not matching `^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$` |
| `invalid_date` | error | `invoice_date` present but not a valid ISO date, or more than 1 day in the future |
| `missing_required` | error | any of `vendor_name, invoice_number, invoice_date, total` has no value |

- Use `Decimal` only. Each issue has `field_name` set where relevant, and `total_mismatch` message in the form: `subtotal (10000.00) + tax (1800.00) = 11800.00 but total is 11500.00`.
- Unit tests in `backend/app/extraction/tests/` for each rule: a pass case, a fail case, plus edge cases (missing values, difference exactly 0.01 passes, 0.02 fails, bad date strings, date tomorrow vs 3 days ahead).

**Done when:** tests pass; running validate on the `wrong_total.pdf` extraction gives `total_mismatch`, `bad_gstin.pdf` gives `invalid_gstin`, and the clean sample gives no errors. Wire `validate` into `cli.py` output as well.

---

## B5. Review rules (branch: `feat/b5-review`)

**Goal:** Decide what needs a human.

**Do this:** (e.g. `review.py`)
- `needs_review(result, issues, threshold: float | None = None) -> bool`: True if any field **below threshold** among the counted fields, or any issue has severity `error`.
- `low_confidence_fields(result, threshold=None) -> list[str]`: names of counted fields below the threshold.
- Threshold default is env `CONFIDENCE_THRESHOLD` (default `0.85`), overridable by argument.
- Only these fields count toward the threshold: `vendor_name, invoice_number, invoice_date, total` (required) plus `gstin, subtotal, tax`.
- A missing field has confidence 0.0, so it falls below the threshold naturally. Decide handling for `gstin`: assume it counts like the others and tell me if you see a problem.
- Unit tests: value exactly at threshold (not low, since "below" means strictly less), just under, env override, argument override, error severity forces review even with all high confidence, warning alone does not force review.

**Done when:** all boundary tests pass.

---

## B6. `find_business_duplicate()` (branch: `feat/b6-duplicates`)

**Goal:** Catch the same invoice re-saved as a different file.

**Do this:** `duplicates.py`:
`find_business_duplicate(result, existing: list[dict]) -> DuplicateMatch | None` where `existing` items are `{"id": str, "vendor_name": str|None, "invoice_number": str|None}`. Pure function. Returns `DuplicateMatch(document_id=<id>, reason="same_invoice")`.

Normalization:
- **vendor:** lowercase, strip punctuation, collapse spaces, remove legal suffixes (pvt, private, ltd, limited, llp, inc, etc.).
- **invoice number:** uppercase, strip spaces; treat separators consistently; strip leading zeros after the prefix (so `INV-001` and `inv 001` and `INV-1` match).
- **Both** must match. If either side's vendor or invoice number is missing or empty, **no match**.

Tests: `"Acme Traders Pvt. Ltd."` vs `"ACME TRADERS PVT LTD"` with `"INV-001"` vs `"inv 001"` matches; different invoice number no match; same invoice number but different vendor no match; missing values no match; empty `existing` list returns None; returns the first match deterministically.

**Done when:** all unit tests pass.

---

## B7. Export (branch: `feat/b7-export`)

**Goal:** Clean CSV/JSON output exactly per Section 5.3.

**Do this:** `export.py`:
- `to_csv(docs: list[dict]) -> str` and `to_json(docs: list[dict]) -> str`.
- Input: each doc is `{"document_id", "filename", "fields": {final values by field_name}, "line_items": [{"position","description","quantity","rate","amount"}]}`. Values are already final (reviewed_value over value, resolved by the caller).
- CSV columns **exactly, in this order:**
  `document_id,filename,vendor_name,invoice_number,invoice_date,gstin,currency,subtotal,tax,total,item_position,item_description,item_quantity,item_rate,item_amount`
- One row **per line item**; a document with no line items yields **one** row with empty item columns. Use the `csv` module (proper quoting for commas, quotes and newlines). Missing field values become empty strings.
- JSON: array of `{ document_id, filename, fields: {...}, line_items: [...] }`.
- Tests: header order, row count (3 items => 3 rows; 0 items => 1 row), quoting of descriptions with commas/quotes, empty list input (CSV outputs just the header), JSON structure.

**Done when:** tests pass and the CSV opens correctly in Excel/Google Sheets (give me a quick way to check, e.g. write a sample CSV file).

---

## B8. Package and document (branch: `feat/b8-package`)

**Goal:** A can import everything with zero changes.

**Do this:**
1. `backend/app/extraction/__init__.py` exports **exactly**: `extract, validate, needs_review, low_confidence_fields, find_business_duplicate, to_csv, to_json` and the types `ExtractionResult, ValidationIssue, DuplicateMatch` (plus `ExtractionError`). Signatures exactly as in Section 5.5.
2. `backend/app/extraction/README.md`: how to run the CLI, the eval script, the tests; env vars used (`ANTHROPIC_API_KEY`, `LLM_MODEL`, `CONFIDENCE_THRESHOLD`); how each function behaves; known limitations (e.g. bbox always null in V1, handwriting, multi-page invoices, non-INR formats).
3. Verify `from app.extraction import extract, validate, needs_review, find_business_duplicate, to_csv, to_json` works from `backend/` with no changes, and that importing does **not** fail when `ANTHROPIC_API_KEY` is unset (the client must be created lazily inside `extract`).
4. Run the full test suite and the eval script one last time and show me the results.

**Done when:** the import line above works, all tests pass, README is complete.

---

## After B8 (only if I ask)
- **Stretch:** ask the model for bounding boxes and fill the optional `bbox` field (must stay optional, `null` is always valid).
- **H2 (hardening):** tune prompts for blurry/photo samples, make sure the demo files behave exactly as the demo script expects.
