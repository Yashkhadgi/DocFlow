import pytest

from app.extraction.types import ExtractionResult, FieldValue, DuplicateMatch
from app.extraction.duplicates import normalize_vendor, normalize_invoice_number, find_business_duplicate


def _build_result(vendor_name="Acme Traders Pvt. Ltd.", invoice_number="INV-001"):
    return ExtractionResult(
        document_type="invoice",
        fields={
            "vendor_name": FieldValue(value=vendor_name, confidence=0.98),
            "invoice_number": FieldValue(value=invoice_number, confidence=0.98),
            "invoice_date": FieldValue(value="2026-09-15", confidence=0.98),
            "gstin": FieldValue(value="27AABCA1234F1Z5", confidence=0.98),
            "currency": FieldValue(value="INR", confidence=0.98),
            "subtotal": FieldValue(value="10000.00", confidence=0.98),
            "tax": FieldValue(value="1800.00", confidence=0.98),
            "total": FieldValue(value="11800.00", confidence=0.98),
        },
        line_items=[],
    )


def test_normalize_vendor():
    assert normalize_vendor("Acme Traders Pvt. Ltd.") == "acme traders"
    assert normalize_vendor("ACME TRADERS PVT LTD") == "acme traders"
    assert normalize_vendor("Apex Infotech Solutions Private Limited") == "apex infotech solutions"
    assert normalize_vendor("Krishna Stationery & Office Supplies") == "krishna stationery and office supplies"
    assert normalize_vendor(None) is None
    assert normalize_vendor("   ") is None


def test_normalize_invoice_number():
    assert normalize_invoice_number("INV-001") == "INV-1"
    assert normalize_invoice_number("inv 001") == "INV-1"
    assert normalize_invoice_number("INV-1") == "INV-1"
    assert normalize_invoice_number("INV/2026/0042") == "INV-2026-42"
    assert normalize_invoice_number("INV001") == "INV-1"
    assert normalize_invoice_number(None) is None
    assert normalize_invoice_number("") is None


def test_find_business_duplicate_match():
    target = _build_result(vendor_name="Acme Traders Pvt. Ltd.", invoice_number="INV-001")
    existing = [
        {"id": "doc-uuid-1", "vendor_name": "ACME TRADERS PVT LTD", "invoice_number": "inv 001"},
    ]
    match = find_business_duplicate(target, existing)
    assert match is not None
    assert isinstance(match, DuplicateMatch)
    assert match.document_id == "doc-uuid-1"
    assert match.reason == "same_invoice"


def test_find_business_duplicate_variations():
    target = _build_result(vendor_name="Apex Infotech Solutions Pvt Ltd", invoice_number="INV-2026-001")
    existing = [
        {"id": "doc-uuid-1", "vendor_name": "Apex Infotech Solutions Private Limited", "invoice_number": "inv-2026-1"},
    ]
    match = find_business_duplicate(target, existing)
    assert match is not None
    assert match.document_id == "doc-uuid-1"


def test_different_invoice_number_no_match():
    target = _build_result(vendor_name="Acme Traders", invoice_number="INV-001")
    existing = [
        {"id": "doc-uuid-1", "vendor_name": "Acme Traders", "invoice_number": "INV-002"},
    ]
    assert find_business_duplicate(target, existing) is None


def test_different_vendor_no_match():
    target = _build_result(vendor_name="Acme Traders", invoice_number="INV-001")
    existing = [
        {"id": "doc-uuid-1", "vendor_name": "Beta Corp", "invoice_number": "INV-001"},
    ]
    assert find_business_duplicate(target, existing) is None


def test_missing_values_no_match():
    target_no_vendor = _build_result(vendor_name=None, invoice_number="INV-001")
    existing = [
        {"id": "doc-1", "vendor_name": "Acme Traders", "invoice_number": "INV-001"},
    ]
    assert find_business_duplicate(target_no_vendor, existing) is None

    target_no_inv = _build_result(vendor_name="Acme Traders", invoice_number=None)
    assert find_business_duplicate(target_no_inv, existing) is None

    target_valid = _build_result(vendor_name="Acme Traders", invoice_number="INV-001")
    existing_missing = [
        {"id": "doc-1", "vendor_name": None, "invoice_number": "INV-001"},
        {"id": "doc-2", "vendor_name": "Acme Traders", "invoice_number": None},
    ]
    assert find_business_duplicate(target_valid, existing_missing) is None


def test_empty_existing_returns_none():
    target = _build_result()
    assert find_business_duplicate(target, []) is None


def test_first_match_is_returned_deterministically():
    target = _build_result(vendor_name="Acme Traders", invoice_number="INV-001")
    existing = [
        {"id": "first-doc-id", "vendor_name": "Acme Traders", "invoice_number": "INV-001"},
        {"id": "second-doc-id", "vendor_name": "Acme Traders", "invoice_number": "INV-001"},
    ]
    match = find_business_duplicate(target, existing)
    assert match is not None
    assert match.document_id == "first-doc-id"
