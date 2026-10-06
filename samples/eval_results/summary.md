# DocFlow V1: AI Extraction Quality & Cost Analysis

This report documents the extraction accuracy, latency benchmarks, human-in-the-loop review distribution, and operating cost analysis for **DocFlow V1** using Anthropic Claude Vision (`claude-sonnet-5-5` / `claude-3-5-sonnet`).

---

## 1. Quality & Accuracy Metrics

Across the 8 core invoice sample types (PDFs, skewed scans, smartphone photos, degraded images), extraction accuracy was evaluated against ground-truth JSON schemas across multiple live evaluation runs (note that model output and token counts vary slightly between runs):

| Document Category | Samples | Field Accuracy | Avg Confidence | Primary Behavior |
|---|---|---|---|---|
| **Clean Digital Invoices** | `clean_invoice.pdf`, `clean_invoice_copy.pdf`, `same_invoice_resaved.pdf` | **100.0%** (24/24 fields) | `0.99` | **Auto-approved** |
| **Physical Scans & Photos** | `scanned_invoice.pdf`, `photo_invoice.jpg` | **100.0%** (16/16 fields) | `0.87 - 0.89` | High accuracy; routed to review if artifacts drop confidence |
| **Validation Red Flags** | `wrong_total.pdf`, `bad_gstin.pdf` | **100.0%** (16/16 fields) | `0.94 - 0.99` | Correctly extracted literal text; flagged with `total_mismatch` / `invalid_gstin` |
| **Heavy Blur / Degraded** | `blurry_invoice.png` | **25.0% – 62.5%** (2/8 to 5/8 fields) | `0.24 - 0.27` | Safely assigned low confidence; zero false-confidence hallucinations |
| **Overall Dataset** | **8 documents** | **90.6% – 95.3%** (58/64 to 61/64 fields) | **0.90 – 0.93** (for correct) | **62.5% review routing** on test pack (designed to test flags) |

> **Key Takeaway:** Overall accuracy is **90.6% to 95.3% (58/64 and 61/64)** across live runs, with **100%** accuracy on all 7 legible samples. All misses occurred exclusively on `blurry_invoice.png` with low confidence. Model output varies slightly between runs.

---

## 2. Human-in-the-Loop & Review Routing

In production enterprise workloads with mostly standard invoices, DocFlow targets **80–90% auto-approval**:
- In our test pack (which is intentionally heavy with error cases and duplicates for judging):
  - **Auto-approved:** `37.5%` (3/8)
  - **Routed to Split-Screen Review (`needs_review`):** `62.5%` (5/8)
- **Zero Silent Failures:** 100% of mathematical mismatches (`total_mismatch`), format violations (`invalid_gstin`), and illegible documents were intercepted before reaching final export.

---

## 3. Performance & Processing Latency (Measured)

- **Average Processing Time:** **4.6 to 5.6 seconds per invoice** (measured live across samples).
- **Fastest Sample:** `3.05s` (`wrong_total.pdf`).
- **Worker Concurrency:** Scalable asynchronously via Celery worker pools without blocking API endpoints.

---

## 4. Cost Analysis (Per 100 Invoices)

### Pricing Assumptions:
- **Model:** `claude-sonnet-5-5`
- **Source:** [Anthropic Official Pricing](https://www.anthropic.com/pricing) (checked 2026-10-06)
  - **Input Tokens:** `$2.00 / million tokens` (`$0.002 / 1,000 tokens`)
  - **Output Tokens:** `$10.00 / million tokens` (`$0.010 / 1,000 tokens`)

### Token Usage per Invoice (Measured):
- **Average Input Tokens:** **2,007 tokens** (including document vision blocks and system prompt)
- **Average Output Tokens:** **457 tokens** (structured JSON response with line items)

### Estimated Cost per 100 Invoices:
$$\text{Input Cost} = 100 \times 2{,}007 \times \frac{\$2.00}{1{,}000{,}000} = \$0.4014$$
$$\text{Output Cost} = 100 \times 457 \times \frac{\$10.00}{1{,}000{,}000} = \$0.4570$$
$$\textbf{Total Cost per 100 Invoices} = \mathbf{\$0.86} \quad (\mathbf{\$0.0086\text{ per invoice}})$$

### Business Impact:
- **Manual Data Entry Cost:** ~\$0.50 – \$1.00 per invoice (5 minutes of manual typing at \$15–\$20/hr).
- **DocFlow Cost:** ~\$0.0086 per invoice.
- **Cost Reduction:** **~98–99% savings** while reducing processing time from minutes to seconds.

---

## 5. What We Learned & Key Takeaways

1. **Confidence Calibration is Highly Reliable:**
   - Correctly extracted fields averaged **0.930** confidence.
   - Illegible/blurred fields dropped to **0.175** confidence.
   - There were **0 instances of wrong-but-high-confidence hallucinations**.
2. **Deterministic Pre-Validation Saves API Cost:**
   - Pre-flight checks on empty bytes, encrypted PDFs, and corrupted files fail fast in `0.001s` with clear error messages before incurring LLM API token costs.
3. **Structured Normalization Bridge:**
   - Post-extraction normalization (stripping currency symbols, standardizing ISO `YYYY-MM-DD` dates, and `Decimal` arithmetic) bridges the gap between vision outputs and strict database/CSV schemas.
