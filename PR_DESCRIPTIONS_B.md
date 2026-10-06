# Person B (AI + Data): PR Descriptions

Use these drafted PR descriptions when creating pull requests for Person B tasks.

---

## PR 1: Sample Pack & Evaluation Foundation (Tasks B1, P1)
**Branch:** `feat/b1-samples`
- **What changed:**
  - Created 9 sample test invoices (`samples/invoices/`) and matching Section 5.4 ground-truth JSON files (`samples/expected/`).
  - Implemented `samples/generate_samples.py` for reproducible sample generation.
  - Implemented `backend/scripts/eval_samples.py` generating detailed baseline and tuned accuracy reports (`samples/eval_results/`).
  - Tuned vision prompt calibration achieving 90.6% to 95.3% overall accuracy (100% on all 7 legible samples, with all misses on `blurry_invoice.png`), 0.90 to 0.93 average confidence for correct fields, and zero false-confidence hallucinations (model output varies slightly between runs).
- **Task IDs:** B1, P1
- **How to verify:**
  `python samples/generate_samples.py`
  `python backend/scripts/eval_samples.py`
- **Contract changes?** No.

---

## PR 2: Vision Extraction Engine & Pydantic Schemas (Tasks B2, B3)
**Branch:** `feat/b2-extract`
- **What changed:**
  - Implemented Pydantic v2 schemas (`FieldValue`, `LineItem`, `ExtractionResult`, `ValidationIssue`, `DuplicateMatch`, `ExtractionError`) in `types.py`.
  - Implemented Anthropic Claude Vision extractor (`extractor.py`) with automatic date and decimal normalization.
  - Built CLI interface (`cli.py`) for command-line document extraction.
  - Added self-correcting retry engine (up to 2 retries on malformed JSON) and API error wrapping.
- **Task IDs:** B2, B3
- **How to verify:**
  `$env:PYTHONPATH="backend"; python -m pytest backend/app/extraction/tests/test_b2_extract.py backend/app/extraction/tests/test_b3_prompts_and_robustness.py`
  `python -m app.extraction.cli samples/invoices/clean_invoice.pdf`
- **Contract changes?** No.

---

## PR 3: Business Validation, Review Routing, & Duplicate Detection (Tasks B4, B5, B6)
**Branch:** `feat/b4-validate`
- **What changed:**
  - Built pure validation engine (`validators.py`) executing rules (`total_mismatch`, `line_items_mismatch`, `invalid_gstin`, `invalid_date`, `missing_required`) using `Decimal` precision.
  - Implemented review routing (`review.py`) evaluating threshold boundaries across counted fields.
  - Implemented business duplicate detection (`duplicates.py`) with vendor legal suffix stripping and invoice number normalization.
- **Task IDs:** B4, B5, B6
- **How to verify:**
  `$env:PYTHONPATH="backend"; python -m pytest backend/app/extraction/tests/test_b4_validate.py backend/app/extraction/tests/test_b5_review.py backend/app/extraction/tests/test_b6_duplicates.py`
- **Contract changes?** No.

---

## PR 4: Export Formatters & Integration Contracts (Tasks B7, B8, P3)
**Branch:** `feat/b7-export`
- **What changed:**
  - Implemented `to_csv` and `to_json` export formatters matching Section 5.3 contract.
  - Finalized `__init__.py` exporting frozen Section 5.5 interface with zero-dependency lazy client initialization.
  - Added integration contract compatibility tests (`test_p3_contract_compatibility.py`) checking signatures and fixture compatibility.
  - Created `INTEGRATION_NOTES.md` guiding Person A through Celery worker and route integration.
- **Task IDs:** B7, B8, P3
- **How to verify:**
  `$env:PYTHONPATH="backend"; python -m pytest backend/app/extraction/tests/test_b7_export.py backend/app/extraction/tests/test_p3_contract_compatibility.py`
- **Contract changes?** No.

---

## PR 5: Real-World File Robustness, Demo Verification & Quality Report (Tasks P2, P4, P5, P6, P7)
**Branch:** `feat/p4-robustness`
- **What changed:**
  - Added pre-flight input validation in `extractor.py` (empty files, size limits, encrypted/corrupt PDFs, oversized images).
  - Added `retryable` classification to `ExtractionError` and automatic API key redaction.
  - Created `verify_demo.py` automated behavioral test suite for the 3-minute demo script.
  - Created `upload_samples.py` demo data seeder with Render cold-start handling and demo exclusions.
  - Produced comprehensive quality, latency (4.6 to 5.6s avg), and cost ($0.86 / 100 invoices at $2.00/$10.00 per 1M tokens; source: https://www.anthropic.com/pricing, checked 2026-10-06) report (`summary.md`).
- **Task IDs:** P2, P4, P5, P6, P7
- **How to verify:**
  `$env:PYTHONPATH="backend"; python -m pytest backend/app/extraction/tests/`
  `python -m app.extraction.verify_demo`
  `python samples/upload_samples.py --dry-run`
- **Contract changes?** No.
