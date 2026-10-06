# Extraction Evaluation Report

**Overall Accuracy:** 90.6% (58/64 fields matched)

- **Avg Confidence (Correct Fields):** `0.932`
- **Avg Confidence (Incorrect Fields):** `0.000`

## Per-Sample Field Breakdown

| Sample File | Field Name | Expected | Actual | Confidence | Match |
|---|---|---|---|---|---|
| `bad_gstin.pdf` | `vendor_name` | Delta Industrial Tools | Delta Industrial Tools | 0.98 | YES |
| `bad_gstin.pdf` | `invoice_number` | INV-2026-702 | INV-2026-702 | 0.99 | YES |
| `bad_gstin.pdf` | `invoice_date` | 2026-09-10 | 2026-09-10 | 0.99 | YES |
| `bad_gstin.pdf` | `gstin` | 27INVALIDGSTIN99 | 27INVALIDGSTIN99 | 0.60 | YES |
| `bad_gstin.pdf` | `currency` | INR | INR | 0.99 | YES |
| `bad_gstin.pdf` | `subtotal` | 6000.00 | 6000.00 | 0.99 | YES |
| `bad_gstin.pdf` | `tax` | 1080.00 | 1080.00 | 0.99 | YES |
| `bad_gstin.pdf` | `total` | 7080.00 | 7080.00 | 0.99 | YES |
| `blurry_invoice.png` | `vendor_name` | Sunrise Electricals Pvt Ltd | Sunrise Electricals Pvt Ltd | 0.40 | YES |
| `blurry_invoice.png` | `invoice_number` | INV-2026-119 | *null* | 0.00 | **NO** |
| `blurry_invoice.png` | `invoice_date` | 2026-06-05 | *null* | 0.00 | **NO** |
| `blurry_invoice.png` | `gstin` | 33AABCE3456J1Z1 | *null* | 0.00 | **NO** |
| `blurry_invoice.png` | `currency` | INR | INR | 0.50 | YES |
| `blurry_invoice.png` | `subtotal` | 15000.00 | *null* | 0.00 | **NO** |
| `blurry_invoice.png` | `tax` | 2700.00 | *null* | 0.00 | **NO** |
| `blurry_invoice.png` | `total` | 17700.00 | *null* | 0.00 | **NO** |
| `clean_invoice.pdf` | `vendor_name` | Apex Infotech Solutions Pvt Ltd | Apex Infotech Solutions Pvt Ltd | 0.98 | YES |
| `clean_invoice.pdf` | `invoice_number` | INV-2026-001 | INV-2026-001 | 0.99 | YES |
| `clean_invoice.pdf` | `invoice_date` | 2026-09-15 | 2026-09-15 | 0.99 | YES |
| `clean_invoice.pdf` | `gstin` | 27AABCA1234F1Z5 | 27AABCA1234F1Z5 | 0.99 | YES |
| `clean_invoice.pdf` | `currency` | INR | INR | 0.99 | YES |
| `clean_invoice.pdf` | `subtotal` | 10000.00 | 10000.00 | 0.99 | YES |
| `clean_invoice.pdf` | `tax` | 1800.00 | 1800.00 | 0.99 | YES |
| `clean_invoice.pdf` | `total` | 11800.00 | 11800.00 | 0.99 | YES |
| `clean_invoice_copy.pdf` | `vendor_name` | Apex Infotech Solutions Pvt Ltd | Apex Infotech Solutions Pvt Ltd | 0.99 | YES |
| `clean_invoice_copy.pdf` | `invoice_number` | INV-2026-001 | INV-2026-001 | 0.99 | YES |
| `clean_invoice_copy.pdf` | `invoice_date` | 2026-09-15 | 2026-09-15 | 0.99 | YES |
| `clean_invoice_copy.pdf` | `gstin` | 27AABCA1234F1Z5 | 27AABCA1234F1Z5 | 0.99 | YES |
| `clean_invoice_copy.pdf` | `currency` | INR | INR | 0.99 | YES |
| `clean_invoice_copy.pdf` | `subtotal` | 10000.00 | 10000.00 | 0.99 | YES |
| `clean_invoice_copy.pdf` | `tax` | 1800.00 | 1800.00 | 0.99 | YES |
| `clean_invoice_copy.pdf` | `total` | 11800.00 | 11800.00 | 0.99 | YES |
| `photo_invoice.jpg` | `vendor_name` | Krishna Stationery & Office Supplies | Krishna Stationery & Office Supplies | 0.88 | YES |
| `photo_invoice.jpg` | `invoice_number` | INV-2026-304 | INV-2026-304 | 0.88 | YES |
| `photo_invoice.jpg` | `invoice_date` | 2026-07-10 | 2026-07-10 | 0.88 | YES |
| `photo_invoice.jpg` | `gstin` | 07AABCD9012H1Z8 | 07AABCD9012H1Z8 | 0.82 | YES |
| `photo_invoice.jpg` | `currency` | INR | INR | 0.92 | YES |
| `photo_invoice.jpg` | `subtotal` | 6500.00 | 6500.00 | 0.88 | YES |
| `photo_invoice.jpg` | `tax` | 1170.00 | 1170.00 | 0.88 | YES |
| `photo_invoice.jpg` | `total` | 7670.00 | 7670.00 | 0.88 | YES |
| `same_invoice_resaved.pdf` | `vendor_name` | Apex Infotech Solutions Pvt Ltd | Apex Infotech Solutions Pvt Ltd | 0.98 | YES |
| `same_invoice_resaved.pdf` | `invoice_number` | INV-2026-001 | INV-2026-001 | 0.99 | YES |
| `same_invoice_resaved.pdf` | `invoice_date` | 2026-09-15 | 2026-09-15 | 0.99 | YES |
| `same_invoice_resaved.pdf` | `gstin` | 27AABCA1234F1Z5 | 27AABCA1234F1Z5 | 0.99 | YES |
| `same_invoice_resaved.pdf` | `currency` | INR | INR | 0.99 | YES |
| `same_invoice_resaved.pdf` | `subtotal` | 10000.00 | 10000.00 | 0.99 | YES |
| `same_invoice_resaved.pdf` | `tax` | 1800.00 | 1800.00 | 0.99 | YES |
| `same_invoice_resaved.pdf` | `total` | 11800.00 | 11800.00 | 0.99 | YES |
| `scanned_invoice.pdf` | `vendor_name` | Bharat Heavy Logistics Ltd | Bharat Heavy Logistics Ltd | 0.88 | YES |
| `scanned_invoice.pdf` | `invoice_number` | INV-2026-882 | INV-2026-882 | 0.85 | YES |
| `scanned_invoice.pdf` | `invoice_date` | 2026-08-20 | 2026-08-20 | 0.88 | YES |
| `scanned_invoice.pdf` | `gstin` | 29AABCB5678G1Z2 | 29AABCB5678G1Z2 | 0.80 | YES |
| `scanned_invoice.pdf` | `currency` | INR | INR | 0.95 | YES |
| `scanned_invoice.pdf` | `subtotal` | 26500.00 | 26500.00 | 0.88 | YES |
| `scanned_invoice.pdf` | `tax` | 4770.00 | 4770.00 | 0.88 | YES |
| `scanned_invoice.pdf` | `total` | 31270.00 | 31270.00 | 0.88 | YES |
| `wrong_total.pdf` | `vendor_name` | Metro Hardware Supplies | Metro Hardware Supplies | 0.99 | YES |
| `wrong_total.pdf` | `invoice_number` | INV-2026-550 | INV-2026-550 | 0.99 | YES |
| `wrong_total.pdf` | `invoice_date` | 2026-09-01 | 2026-09-01 | 0.99 | YES |
| `wrong_total.pdf` | `gstin` | 27AABCF7890K1Z4 | 27AABCF7890K1Z4 | 0.98 | YES |
| `wrong_total.pdf` | `currency` | INR | INR | 0.99 | YES |
| `wrong_total.pdf` | `subtotal` | 10000.00 | 10000.00 | 0.99 | YES |
| `wrong_total.pdf` | `tax` | 1800.00 | 1800.00 | 0.99 | YES |
| `wrong_total.pdf` | `total` | 11500.00 | 11500.00 | 0.97 | YES |

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