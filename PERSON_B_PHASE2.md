# PERSON B (AI + Data): Phase 2 Prompts (after B1 to B8)

> **Instructions for the AI assistant reading this file**
>
> I am **Person B (AI + Data)** on DocFlow. B1 to B8 are done. Read `V1_BUILD_PLAN.md` again (especially Sections 5.3 to 5.6, 8, 10, 11 and the demo script in Section 9), then do the tasks below, **one at a time, in order**.
>
> ## Rules (same as before)
> 1. Edit **only** `/backend/app/extraction` and `/samples` (plus `backend/scripts/eval_samples.py`, which already exists). Do not edit A's or C's code or any file in `/contracts`.
> 2. Contracts (Section 5) are frozen. Do not change function signatures, field names, or types. If a contract looks wrong, tell me and stop.
> 3. `Decimal` for money. Secrets only from env vars. Never log API keys or full document contents.
> 4. After each task: stop, show me the exact commands to verify it (PowerShell on Windows), say what a good result looks like, and **wait for me to say "next"**.
> 5. If something is ambiguous, pick the simplest option consistent with the contract and tell me your assumption in one line.
>
> Start with **P1** when I say "start".

---

## P1. Eval and tuning loop (branch: `feat/p1-tuning`)

**Goal:** Reach the accuracy target from B3 with evidence, not guesses.

**Do this:**
1. Run `python backend/scripts/eval_samples.py` with my real key (I load `.env` into the shell myself) and save the full results to `samples/eval_results/baseline.json` and a short readable table to `samples/eval_results/baseline.md` (per sample, per field: expected, got, confidence, match yes/no).
2. List every miss, and for each one say why it probably happened (OCR issue, ambiguous label, date format, GST vs tax confusion, number formatting, etc.).
3. Change **only `prompts.py`** (and normalization code in `extractor.py` if a miss is a formatting issue, not a model issue) to fix the misses. Do not special-case sample filenames or hardcode expected values. The fixes must generalize to unseen invoices.
4. Re-run the eval and save `after_tuning.json` / `after_tuning.md`. Show a before/after comparison.
5. Targets: at least **90%** field accuracy on `clean`, `scanned`, `photo`; `blurry_invoice.png` must show **visibly lower confidence** (several counted fields below 0.85) rather than confidently wrong values. Wrong-but-high-confidence is the worst failure, so report any such cases separately.
6. Calibration check: print the average confidence for correct fields vs incorrect fields across all samples. Incorrect fields should have clearly lower confidence. If not, tighten the calibration wording in the prompt.

**Done when:** before/after files exist, targets are met (or I'm told clearly which target is not met and why), and no sample-specific hacks exist.

---

## P2. Demo-file behaviour check (branch: `feat/p2-demo-check`)

**Goal:** Make sure every demo file behaves exactly as the demo script expects.

**Do this:** Create `backend/app/extraction/verify_demo.py`, runnable as `python -m app.extraction.verify_demo`. It runs the real pipeline functions on the sample pack and prints a PASS/FAIL checklist:

| Check | Expected |
|---|---|
| `clean_invoice.pdf` | no `error` issues; fields confident; `needs_review()` is False (so it auto-approves) |
| `wrong_total.pdf` | `total_mismatch` error present; `needs_review()` True |
| `bad_gstin.pdf` | `invalid_gstin` error present; `needs_review()` True |
| `blurry_invoice.png` | at least 2 counted fields below threshold; `needs_review()` True |
| `clean_invoice_copy.pdf` vs `clean_invoice.pdf` | identical SHA-256 |
| `same_invoice_resaved.pdf` | different SHA-256 from clean, but `find_business_duplicate()` matches the clean invoice's vendor + invoice number |
| `failme.pdf` | is a valid PDF (file starts with `%PDF`) |
| `photo_invoice.jpg`, `scanned_invoice.pdf` | extraction succeeds; report `needs_review()` and low-confidence fields |

Also: the demo script wants a **yellow low-confidence GSTIN** next to a red flag on one invoice. Check whether any sample currently shows a low-confidence `gstin` (confidence below threshold). If none does, tell me, and suggest which sample (a mildly degraded copy of `wrong_total.pdf` is a good candidate) to adjust so the demo works honestly, without faking confidence values. Do not change the model output artificially.

**Done when:** the script runs and every demo behaviour is PASS, or each FAIL has a clear proposed fix.

---

## P3. Contract compatibility tests for integration (branch: `feat/p3-contract-tests`)

**Goal:** Make I1 (A swapping the stub for my module) smooth.

**Do this:** In `backend/app/extraction/tests/`:
1. A test that loads `contracts/fixtures/*.json` (read-only) and `contracts/extraction_schema.json` if it exists, and checks that an `ExtractionResult` serializes to the Section 5.4 shape: the 8 field names exactly, `document_type == "invoice"`, `fields.*.value` is `str | None`, confidence in 0..1, `bbox` optional, `line_items` items have `description, quantity, rate, amount, confidence`, money values are strings.
2. A test for every function signature in Section 5.5 (use `inspect.signature`): names, parameters, defaults.
3. A test that building an `ExtractionResult` from the fixture's `fields` + `line_items` values passes `validate()` without exceptions, and that `validate()` / `needs_review()` / `low_confidence_fields()` never raise on edge input (all-null fields, empty line items, confidence 0.0 everywhere).
4. A test that `to_csv` / `to_json` accept the dict shape A will pass (document_id, filename, fields with final values, line_items with position), including missing optional keys, `None` values, and fields not present at all.
5. Write `backend/app/extraction/INTEGRATION_NOTES.md` for Person A: how to call each function, what exceptions to expect (`ExtractionError` only from `extract`), what `existing` must look like for `find_business_duplicate`, that `extract` is blocking (so call it in the Celery worker, not in the API request), expected time per call, and required env vars.

**Done when:** all contract tests pass and `INTEGRATION_NOTES.md` exists.

---

## P4. Robustness for real-world files (branch: `feat/p4-robustness`)

**Goal:** The worker should never get a confusing crash from a bad file.

**Do this:**
1. In `extract()`, validate inputs before calling the API: empty bytes, unsupported mime type, corrupted PDF, password-protected PDF, PDF over the API limits (check the current Anthropic docs for page and size limits and handle them), image too large. Each raises `ExtractionError` with a clear, human-readable message (these messages show up in the UI as `error_message`).
2. Distinguish errors that are **worth retrying** (timeouts, rate limits, 5xx, connection errors) from errors that are **not** (corrupted file, unsupported type, auth error / invalid key). Add an attribute such as `ExtractionError.retryable: bool` (default True) **without changing the constructor signature in a breaking way**. Document it in `INTEGRATION_NOTES.md`.
3. Multi-page invoices: make sure the prompt handles totals appearing on the last page, and line items spanning pages. Add a test sample only if it's easy to generate; otherwise note it as a known limitation.
4. Confirm the Anthropic client is created lazily and the key is never logged or included in exceptions. Add a test for that (set a fake key, trigger an error, assert the key string is not in the message or logs).
5. Add timing and token-usage logging (metadata only: mime type, size in bytes, attempt number, duration, input/output tokens; no content, no filename) so cost per invoice can be reported.
6. Tests with a mocked client for each error class above.

**Done when:** every bad-input case raises a clear `ExtractionError`, the retryable flag works, and tests pass.

---

## P5. Demo data loader (branch: `feat/p5-demo-loader`)

**Goal:** Realistic data on the live site without touching the DB directly (the plan says use A's seed script or API uploads under the demo user).

**Do this:** Create `samples/upload_samples.py`:
- Args: `--base-url` (e.g. `https://<live-api>/api/v1`), `--email` (default `demo@docflow.app`), `--password` from env `DEMO_PASSWORD` or a prompt (never hardcoded in the file), `--dir` (default `samples/invoices`), `--only` (optional list), `--exclude` (e.g. exclude the duplicate demo files so they stay fresh for the live demo), `--wait` (poll `GET /documents` until nothing is queued/processing, with a timeout).
- Uses `requests` against the contract endpoints only: `POST /auth/login`, `POST /documents/upload` (multipart field `files`, max 20 per request), `GET /documents`. Prints the per-file result from the upload response and a final status summary from `counts`.
- Handle the Render free-tier cold start (first request may take 30 to 60 seconds): retry the health check with backoff before starting.
- Write a short section in `samples/README.md` explaining how to use it, and **which files to keep out of the pre-load** so the live demo can show them fresh (`clean_invoice_copy.pdf`, `same_invoice_resaved.pdf`, `failme.pdf`, and one invoice for the review step).

**Done when:** I can run it against my local API (when A's server is up) and see per-file results and final counts. If A's API isn't ready yet, make it testable with a mocked HTTP layer.

---

## P6. Cost and quality report (branch: `feat/p6-report`)

**Goal:** Numbers for the README and slides.

**Do this:** Extend the eval output (or a small separate script) to produce `samples/eval_results/summary.md` with:
- accuracy per sample type, overall field accuracy, and the share of samples that would **auto-approve** vs **need review** (the plan's impact story),
- average seconds per document,
- average input/output tokens per document and an estimated cost per 100 invoices using the **current published pricing for the model in `LLM_MODEL`** (tell me where you got the prices; if you can't verify them, leave the price as an input variable I can fill in rather than guessing),
- a short "what we learned" list (failure types, how confidence correlated with correctness).

**Done when:** `summary.md` exists with all of the above and clearly states the assumptions.

---

## P7. Hardening support and handoff (branch: `feat/p7-handoff`)

**Do this:**
1. Update `backend/app/extraction/README.md` with: final eval numbers, how to run `verify_demo`, known limitations (bbox is `null` in V1, handwriting, non-INR and non-GST invoices, very long multi-page invoices, rotated pages), and troubleshooting (missing key, rate limit, timeouts).
2. Write `samples/README.md` updates so a teammate understands every file and which demo step uses it.
3. Draft **PR descriptions** (What changed / Task ID / How to verify / Contract changes: no) for P1 to P6 in a single file `PR_DESCRIPTIONS_B.md` (this file is for my own use, don't commit it), so I can paste them.
4. Draft a short message I can send to Person A and the Lead: what's ready, how to import, which env vars the deployed worker needs (`ANTHROPIC_API_KEY`, `LLM_MODEL`, `CONFIDENCE_THRESHOLD`), a reminder to use a **separate production key** with a spend limit, and the expected processing time per document (so the demo plans for it).
5. Run the full test suite, `verify_demo`, and the eval one last time and show me the final results.

**Done when:** docs are updated, drafts exist, and all tests/checks pass.

---

## P8. Stretch (only if I say so): bounding boxes (branch: `feat/p8-bbox`)

- Ask the model to return normalized bounding boxes (`{"page","x","y","w","h"}`, values 0..1) for each field **as optional output**; the prompt must say to return `null` when unsure.
- Validate boxes (values in range, page >= 1); invalid boxes become `null` rather than raising.
- Must never reduce extraction accuracy: re-run the eval and compare with P1. If accuracy or reliability drops, revert and tell me.
- `bbox` stays optional everywhere, since the UI works without it. Do not change contracts.

**Done when:** eval accuracy is unchanged or better and bboxes appear on at least the clean sample (spot-check by drawing them on the page image and showing me).
