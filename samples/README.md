# DocFlow V1: Sample Invoices & Test Pack

This directory contains the sample test invoices, expected ground-truth JSON files, evaluation scripts, and live data preloaders for **DocFlow V1**.

---

## 1. Sample Files & Demo Script Mapping

| # | File | Format | What it tests | 3-Minute Demo Step | Expected Outcome |
|---|---|---|---|---|---|
| 1 | `clean_invoice.pdf` | Digital PDF | Clean digital invoice, valid GSTIN, 3 line items | **Demo Step 2 (Bulk Upload)** | Auto-approved / `approved` (`auto_approved=true`) |
| 2 | `scanned_invoice.pdf` | Raster PDF | Skewed scan layout, scanner contrast | **Demo Step 2 (Bulk Upload)** | High vision extraction accuracy |
| 3 | `photo_invoice.jpg` | JPEG | Mobile camera photo, perspective angle | **Demo Step 2 (Bulk Upload)** | Vision extraction extracts fields from phone photo |
| 4 | `blurry_invoice.png` | PNG | Low-resolution, heavy Gaussian blur | **Demo Step 2 (Bulk Upload)** | Low confidence (< 0.85); safely routes to `needs_review` |
| 5 | `wrong_total.pdf` | Digital PDF | Inconsistent totals (10000 + 1800 != 11500) | **Demo Step 3 (Review & Edit)** | Triggers red `total_mismatch` error; user fixes & approves |
| 6 | `bad_gstin.pdf` | Digital PDF | Invalid GSTIN format (`27INVALIDGSTIN99`) | **Demo Step 3 (Review & Edit)** | Triggers red `invalid_gstin` & yellow low-confidence GSTIN badge |
| 7 | `clean_invoice_copy.pdf` | Digital PDF | **Byte-identical** copy of #1 | **Demo Step 4 (Idempotency)** | Caught by SHA-256 hash (`status='duplicate'`, `duplicate_reason='same_file'`) |
| 8 | `same_invoice_resaved.pdf` | Digital PDF | Same vendor & invoice # as #1, **different bytes** | **Demo Step 4 (Idempotency)** | Caught by `find_business_duplicate` (`status='duplicate'`, `duplicate_reason='same_invoice'`) |
| 9 | `failme.pdf` | Digital PDF | Valid PDF triggering forced worker failure | **Demo Step 5 (Resilience)** | Retries with exponential backoff -> `failed` -> manual Retry |

---

## 2. Directory Structure

```
samples/
├── generate_samples.py      # Re-generates all 9 invoice files and expected JSONs
├── upload_samples.py        # Demo data seeder (authenticates and uploads via API)
├── README.md                # This documentation
├── eval_results/            # Benchmarks, accuracy reports, and cost analysis
│   ├── baseline.json / .md
│   ├── after_tuning.json / .md
│   └── summary.md
├── invoices/                # Sample invoice files for upload & CLI
│   ├── clean_invoice.pdf
│   ├── scanned_invoice.pdf
│   ├── photo_invoice.jpg
│   ├── blurry_invoice.png
│   ├── wrong_total.pdf
│   ├── bad_gstin.pdf
│   ├── clean_invoice_copy.pdf
│   ├── same_invoice_resaved.pdf
│   └── failme.pdf
└── expected/                # Ground truth JSONs matching Section 5.4 contract
    ├── clean_invoice.json
    ├── scanned_invoice.json
    ├── photo_invoice.json
    ├── blurry_invoice.json
    ├── wrong_total.json
    ├── bad_gstin.json
    ├── clean_invoice_copy.json
    ├── same_invoice_resaved.json
    └── failme.json
```

---

## 3. Pre-loading Data for the Live Demo (`upload_samples.py`)

To populate realistic documents under the demo account (`demo@docflow.app`) on the live deployed backend:

```bash
# Upload standard sample pack to local or live API
python samples/upload_samples.py --base-url "https://api.docflow.app/api/v1" --wait
```

### Live Demo Exclusions:
By default, `upload_samples.py` **excludes** the following 4 files during pre-seeding so they remain fresh for live interaction during the judge demo:
1. `wrong_total.pdf`: Uploaded live in **Demo Step 3** to show the red error flag, yellow GSTIN badge, and split-screen review/approve.
2. `clean_invoice_copy.pdf`: Uploaded live in **Demo Step 4** to demonstrate **same-file SHA-256 idempotency** (`duplicate`, `duplicate_reason='same_file'`).
3. `same_invoice_resaved.pdf`: Uploaded live in **Demo Step 4** to demonstrate **business duplicate detection** (`duplicate`, `duplicate_reason='same_invoice'`).
4. `failme.pdf`: Uploaded live in **Demo Step 5** to demonstrate **worker retry with backoff**, failure status, and the manual **Retry** button.

---

## 4. Verification & Re-generation

To re-generate all sample invoices and expected JSON ground truth:
```bash
python samples/generate_samples.py
```

To run the automated demo behavioral checklist:
```bash
python -m app.extraction.verify_demo
```
