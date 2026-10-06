import json
from datetime import date, timedelta
from pathlib import Path
import pytest

from app.extraction.types import ExtractionResult, FieldValue, LineItem
from app.extraction.validators import validate


def _build_result(
    vendor_name="Acme Traders",
    invoice_number="INV-001",
    invoice_date="2026-09-01",
    gstin="27AABCA1234F1Z5",
    currency="INR",
    subtotal="10000.00",
    tax="1800.00",
    total="11800.00",
    line_items=None,
):
    if line_items is None:
        line_items = [
            LineItem(description="Item 1", quantity="1", rate=subtotal, amount=subtotal, confidence=0.95)
        ]
    return ExtractionResult(
        document_type="invoice",
        fields={
            "vendor_name": FieldValue(value=vendor_name, confidence=0.95),
            "invoice_number": FieldValue(value=invoice_number, confidence=0.95),
            "invoice_date": FieldValue(value=invoice_date, confidence=0.95),
            "gstin": FieldValue(value=gstin, confidence=0.95),
            "currency": FieldValue(value=currency, confidence=0.95),
            "subtotal": FieldValue(value=subtotal, confidence=0.95),
            "tax": FieldValue(value=tax, confidence=0.95),
            "total": FieldValue(value=total, confidence=0.95),
        },
        line_items=line_items,
    )


def test_clean_invoice_passes_all_validations():
    res = _build_result()
    issues = validate(res)
    assert len(issues) == 0


def test_total_mismatch_exact_and_rounding():
    # Exact match -> pass
    res_exact = _build_result(subtotal="100.00", tax="18.00", total="118.00")
    assert len(validate(res_exact)) == 0

    # Diff == 0.01 -> pass
    res_001 = _build_result(subtotal="100.00", tax="18.00", total="118.01")
    assert len(validate(res_001)) == 0

    # Diff == 0.02 -> fail
    res_002 = _build_result(subtotal="100.00", tax="18.00", total="118.02")
    issues = validate(res_002)
    assert any(i.rule == "total_mismatch" and i.severity == "error" for i in issues)

    # Big mismatch
    res_mismatch = _build_result(subtotal="10000.00", tax="1800.00", total="11500.00")
    issues = validate(res_mismatch)
    total_issue = next(i for i in issues if i.rule == "total_mismatch")
    assert total_issue.field_name == "total"
    assert total_issue.severity == "error"
    assert "subtotal (10000.00) + tax (1800.00) = 11800.00 but total is 11500.00" in total_issue.message


def test_total_mismatch_skipped_when_values_missing():
    res_no_tax = _build_result(tax=None)
    issues = validate(res_no_tax)
    assert not any(i.rule == "total_mismatch" for i in issues)


def test_line_items_mismatch():
    items = [
        LineItem(description="A", quantity="1", rate="5000.00", amount="5000.00", confidence=0.9),
        LineItem(description="B", quantity="1", rate="4500.00", amount="4500.00", confidence=0.9),
    ]
    # Sum is 9500.00, subtotal is 10000.00
    res = _build_result(subtotal="10000.00", line_items=items)
    issues = validate(res)
    line_issue = next((i for i in issues if i.rule == "line_items_mismatch"), None)
    assert line_issue is not None
    assert line_issue.severity == "warning"
    assert line_issue.field_name == "subtotal"


def test_invalid_gstin():
    res_valid = _build_result(gstin="27AABCA1234F1Z5")
    assert not any(i.rule == "invalid_gstin" for i in validate(res_valid))

    res_invalid = _build_result(gstin="27INVALIDGSTIN99")
    issues = validate(res_invalid)
    gstin_issue = next((i for i in issues if i.rule == "invalid_gstin"), None)
    assert gstin_issue is not None
    assert gstin_issue.severity == "error"
    assert gstin_issue.field_name == "gstin"

    # Missing GSTIN should NOT produce invalid_gstin
    res_none = _build_result(gstin=None)
    assert not any(i.rule == "invalid_gstin" for i in validate(res_none))


def test_invalid_date():
    res_valid = _build_result(invoice_date="2026-09-01")
    assert not any(i.rule == "invalid_date" for i in validate(res_valid))

    # Tomorrow should pass
    tomorrow_str = (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")
    res_tomorrow = _build_result(invoice_date=tomorrow_str)
    assert not any(i.rule == "invalid_date" for i in validate(res_tomorrow))

    # 5 days in future should fail
    future_str = (date.today() + timedelta(days=5)).strftime("%Y-%m-%d")
    res_future = _build_result(invoice_date=future_str)
    issues = validate(res_future)
    assert any(i.rule == "invalid_date" and i.severity == "error" for i in issues)

    # Malformed date string
    res_malformed = _build_result(invoice_date="01/09/2026-bad")
    issues = validate(res_malformed)
    assert any(i.rule == "invalid_date" and i.severity == "error" for i in issues)


def test_missing_required():
    res = _build_result(vendor_name=None, total=None)
    issues = validate(res)
    missing_fields = [i.field_name for i in issues if i.rule == "missing_required"]
    assert "vendor_name" in missing_fields
    assert "total" in missing_fields
    assert "invoice_number" not in missing_fields


def test_samples_validation():
    from app.extraction.extractor import normalize_extraction_data

    # Test wrong_total.json
    samples_dir = Path(__file__).resolve().parent.parent.parent.parent.parent / "samples" / "expected"
    with open(samples_dir / "wrong_total.json", "r", encoding="utf-8") as f:
        wrong_total_data = json.load(f)
    res_wt = normalize_extraction_data(wrong_total_data)
    issues_wt = validate(res_wt)
    assert len(issues_wt) == 1
    assert issues_wt[0].rule == "total_mismatch"
    assert issues_wt[0].severity == "error"

    # Test bad_gstin.json
    with open(samples_dir / "bad_gstin.json", "r", encoding="utf-8") as f:
        bad_gstin_data = json.load(f)
    res_bg = normalize_extraction_data(bad_gstin_data)
    issues_bg = validate(res_bg)
    assert len(issues_bg) == 1
    assert issues_bg[0].rule == "invalid_gstin"
    assert issues_bg[0].severity == "error"

    # Test clean_invoice.json
    with open(samples_dir / "clean_invoice.json", "r", encoding="utf-8") as f:
        clean_data = json.load(f)
    res_clean = normalize_extraction_data(clean_data)
    issues_clean = validate(res_clean)
    assert len(issues_clean) == 0
