# Extraction Evaluation Report

**Overall Accuracy:** 90.6% (58/64 fields matched across 8 test invoices)

- **Non-degraded Samples Accuracy:** `100.0%` (56/56 fields matched across 7 samples)
- **Blurry Degraded Sample:** `25.0%` (2/8 fields matched; all 6 misses occurred due to heavy blur)
- **Avg Confidence (Correct Fields):** `0.930`
- **Avg Confidence (Incorrect Fields):** `0.175`
- **Average Processing Latency:** `5.57s` per document
- **Token Usage (Avg):** `2007` input tokens / `457` output tokens
- **Estimated Cost per 100 Invoices:** `$1.29` (at $3.00/1M in, $15.00/1M out)

## Per-Sample Field Breakdown

| Sample File | Latency | Tokens | Field Name | Expected | Actual | Confidence | Match |
|---|---|---|---|---|---|---|---|
| `bad_gstin.pdf` | 6.24s | 1647/440 | `vendor_name` | Delta Industrial Tools | Delta Industrial Tools | 0.99 | YES |
| `bad_gstin.pdf` | 6.24s | 1647/440 | `invoice_number` | INV-2026-702 | INV-2026-702 | 0.99 | YES |
| `bad_gstin.pdf` | 6.24s | 1647/440 | `invoice_date` | 2026-09-10 | 2026-09-10 | 0.99 | YES |
| `bad_gstin.pdf` | 6.24s | 1647/440 | `gstin` | 27INVALIDGSTIN99 | 27INVALIDGSTIN99 | 0.60 | YES |
| `bad_gstin.pdf` | 6.24s | 1647/440 | `currency` | INR | INR | 0.99 | YES |
| `bad_gstin.pdf` | 6.24s | 1647/440 | `subtotal` | 6000.00 | 6000.00 | 0.99 | YES |
| `bad_gstin.pdf` | 6.24s | 1647/440 | `tax` | 1080.00 | 1080.00 | 0.99 | YES |
| `bad_gstin.pdf` | 6.24s | 1647/440 | `total` | 7080.00 | 7080.00 | 0.99 | YES |
| `blurry_invoice.png` | 10.24s | 2570/440 | `vendor_name` | Sunrise Electricals Pvt Ltd | Sunrise Electricals Pvt Ltd | 0.40 | YES |
| `blurry_invoice.png` | 10.24s | 2570/440 | `invoice_number` | INV-2026-119 | *null* | 0.00 | **NO** |
| `blurry_invoice.png` | 10.24s | 2570/440 | `invoice_date` | 2026-06-05 | *null* | 0.00 | **NO** |
| `blurry_invoice.png` | 10.24s | 2570/440 | `gstin` | 33AABCE3456J1Z1 | *null* | 0.00 | **NO** |
| `blurry_invoice.png` | 10.24s | 2570/440 | `currency` | INR | INR | 0.45 | YES |
| `blurry_invoice.png` | 10.24s | 2570/440 | `subtotal` | 15000.00 | 18000.00 | 0.35 | **NO** |
| `blurry_invoice.png` | 10.24s | 2570/440 | `tax` | 2700.00 | 3240.00 | 0.35 | **NO** |
| `blurry_invoice.png` | 10.24s | 2570/440 | `total` | 17700.00 | 21240.00 | 0.35 | **NO** |
| `clean_invoice.pdf` | 3.57s | 1649/485 | `vendor_name` | Apex Infotech Solutions Pvt Ltd | Apex Infotech Solutions Pvt Ltd | 0.98 | YES |
| `clean_invoice.pdf` | 3.57s | 1649/485 | `invoice_number` | INV-2026-001 | INV-2026-001 | 0.99 | YES |
| `clean_invoice.pdf` | 3.57s | 1649/485 | `invoice_date` | 2026-09-15 | 2026-09-15 | 0.99 | YES |
| `clean_invoice.pdf` | 3.57s | 1649/485 | `gstin` | 27AABCA1234F1Z5 | 27AABCA1234F1Z5 | 0.98 | YES |
| `clean_invoice.pdf` | 3.57s | 1649/485 | `currency` | INR | INR | 0.99 | YES |
| `clean_invoice.pdf` | 3.57s | 1649/485 | `subtotal` | 10000.00 | 10000.00 | 0.99 | YES |
| `clean_invoice.pdf` | 3.57s | 1649/485 | `tax` | 1800.00 | 1800.00 | 0.99 | YES |
| `clean_invoice.pdf` | 3.57s | 1649/485 | `total` | 11800.00 | 11800.00 | 0.99 | YES |
| `clean_invoice_copy.pdf` | 3.30s | 1649/485 | `vendor_name` | Apex Infotech Solutions Pvt Ltd | Apex Infotech Solutions Pvt Ltd | 0.98 | YES |
| `clean_invoice_copy.pdf` | 3.30s | 1649/485 | `invoice_number` | INV-2026-001 | INV-2026-001 | 0.99 | YES |
| `clean_invoice_copy.pdf` | 3.30s | 1649/485 | `invoice_date` | 2026-09-15 | 2026-09-15 | 0.99 | YES |
| `clean_invoice_copy.pdf` | 3.30s | 1649/485 | `gstin` | 27AABCA1234F1Z5 | 27AABCA1234F1Z5 | 0.98 | YES |
| `clean_invoice_copy.pdf` | 3.30s | 1649/485 | `currency` | INR | INR | 0.99 | YES |
| `clean_invoice_copy.pdf` | 3.30s | 1649/485 | `subtotal` | 10000.00 | 10000.00 | 0.99 | YES |
| `clean_invoice_copy.pdf` | 3.30s | 1649/485 | `tax` | 1800.00 | 1800.00 | 0.99 | YES |
| `clean_invoice_copy.pdf` | 3.30s | 1649/485 | `total` | 11800.00 | 11800.00 | 0.99 | YES |
| `photo_invoice.jpg` | 11.06s | 2687/440 | `vendor_name` | Krishna Stationery & Office Supplies | Krishna Stationery & Office Supplies | 0.88 | YES |
| `photo_invoice.jpg` | 11.06s | 2687/440 | `invoice_number` | INV-2026-304 | INV-2026-304 | 0.87 | YES |
| `photo_invoice.jpg` | 11.06s | 2687/440 | `invoice_date` | 2026-07-10 | 2026-07-10 | 0.88 | YES |
| `photo_invoice.jpg` | 11.06s | 2687/440 | `gstin` | 07AABCD9012H1Z8 | 07AABCD9012H1Z8 | 0.82 | YES |
| `photo_invoice.jpg` | 11.06s | 2687/440 | `currency` | INR | INR | 0.92 | YES |
| `photo_invoice.jpg` | 11.06s | 2687/440 | `subtotal` | 6500.00 | 6500.00 | 0.88 | YES |
| `photo_invoice.jpg` | 11.06s | 2687/440 | `tax` | 1170.00 | 1170.00 | 0.88 | YES |
| `photo_invoice.jpg` | 11.06s | 2687/440 | `total` | 7670.00 | 7670.00 | 0.88 | YES |
| `same_invoice_resaved.pdf` | 3.31s | 1652/485 | `vendor_name` | Apex Infotech Solutions Pvt Ltd | Apex Infotech Solutions Pvt Ltd | 0.98 | YES |
| `same_invoice_resaved.pdf` | 3.31s | 1652/485 | `invoice_number` | INV-2026-001 | INV-2026-001 | 0.99 | YES |
| `same_invoice_resaved.pdf` | 3.31s | 1652/485 | `invoice_date` | 2026-09-15 | 2026-09-15 | 0.99 | YES |
| `same_invoice_resaved.pdf` | 3.31s | 1652/485 | `gstin` | 27AABCA1234F1Z5 | 27AABCA1234F1Z5 | 0.98 | YES |
| `same_invoice_resaved.pdf` | 3.31s | 1652/485 | `currency` | INR | INR | 0.99 | YES |
| `same_invoice_resaved.pdf` | 3.31s | 1652/485 | `subtotal` | 10000.00 | 10000.00 | 0.99 | YES |
| `same_invoice_resaved.pdf` | 3.31s | 1652/485 | `tax` | 1800.00 | 1800.00 | 0.99 | YES |
| `same_invoice_resaved.pdf` | 3.31s | 1652/485 | `total` | 11800.00 | 11800.00 | 0.99 | YES |
| `scanned_invoice.pdf` | 3.75s | 2555/440 | `vendor_name` | Bharat Heavy Logistics Ltd | Bharat Heavy Logistics Ltd | 0.88 | YES |
| `scanned_invoice.pdf` | 3.75s | 2555/440 | `invoice_number` | INV-2026-882 | INV-2026-882 | 0.85 | YES |
| `scanned_invoice.pdf` | 3.75s | 2555/440 | `invoice_date` | 2026-08-20 | 2026-08-20 | 0.88 | YES |
| `scanned_invoice.pdf` | 3.75s | 2555/440 | `gstin` | 29AABCB5678G1Z2 | 29AABCB5678G1Z2 | 0.80 | YES |
| `scanned_invoice.pdf` | 3.75s | 2555/440 | `currency` | INR | INR | 0.92 | YES |
| `scanned_invoice.pdf` | 3.75s | 2555/440 | `subtotal` | 26500.00 | 26500.00 | 0.88 | YES |
| `scanned_invoice.pdf` | 3.75s | 2555/440 | `tax` | 4770.00 | 4770.00 | 0.88 | YES |
| `scanned_invoice.pdf` | 3.75s | 2555/440 | `total` | 31270.00 | 31270.00 | 0.88 | YES |
| `wrong_total.pdf` | 3.05s | 1647/440 | `vendor_name` | Metro Hardware Supplies | Metro Hardware Supplies | 0.99 | YES |
| `wrong_total.pdf` | 3.05s | 1647/440 | `invoice_number` | INV-2026-550 | INV-2026-550 | 0.99 | YES |
| `wrong_total.pdf` | 3.05s | 1647/440 | `invoice_date` | 2026-09-01 | 2026-09-01 | 0.99 | YES |
| `wrong_total.pdf` | 3.05s | 1647/440 | `gstin` | 27AABCF7890K1Z4 | 27AABCF7890K1Z4 | 0.99 | YES |
| `wrong_total.pdf` | 3.05s | 1647/440 | `currency` | INR | INR | 0.99 | YES |
| `wrong_total.pdf` | 3.05s | 1647/440 | `subtotal` | 10000.00 | 10000.00 | 0.99 | YES |
| `wrong_total.pdf` | 3.05s | 1647/440 | `tax` | 1800.00 | 1800.00 | 0.99 | YES |
| `wrong_total.pdf` | 3.05s | 1647/440 | `total` | 11500.00 | 11500.00 | 0.97 | YES |

## Per-Field Accuracy Summary

| Field Name | Accuracy | Passed / Total |
|---|---|---|
| `vendor_name` | 100.0% | 8/8 |
| `invoice_number` | 87.5% | 7/8 |
| `invoice_date` | 87.5% | 7/8 |
| `gstin` | 87.5% | 7/8 |
| `currency` | 100.0% | 8/8 |
| `subtotal` | 87.5% | 7/8 |
| `tax` | 87.5% | 7/8 |
| `total` | 87.5% | 7/8 |