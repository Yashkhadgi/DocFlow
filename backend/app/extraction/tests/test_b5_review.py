import pytest
from unittest.mock import patch

from app.extraction.types import ExtractionResult, FieldValue, LineItem, ValidationIssue
from app.extraction.review import low_confidence_fields, needs_review


def _create_result(default_conf=0.95, overrides=None):
    if overrides is None:
        overrides = {}
    fields = {
        "vendor_name": FieldValue(value="Acme Corp", confidence=overrides.get("vendor_name", default_conf)),
        "invoice_number": FieldValue(value="INV-001", confidence=overrides.get("invoice_number", default_conf)),
        "invoice_date": FieldValue(value="2026-09-01", confidence=overrides.get("invoice_date", default_conf)),
        "gstin": FieldValue(value="27AABCA1234F1Z5", confidence=overrides.get("gstin", default_conf)),
        "currency": FieldValue(value="INR", confidence=overrides.get("currency", default_conf)),
        "subtotal": FieldValue(value="10000.00", confidence=overrides.get("subtotal", default_conf)),
        "tax": FieldValue(value="1800.00", confidence=overrides.get("tax", default_conf)),
        "total": FieldValue(value="11800.00", confidence=overrides.get("total", default_conf)),
    }
    return ExtractionResult(document_type="invoice", fields=fields, line_items=[])


def test_boundary_at_threshold():
    # Exactly at default threshold 0.85 is NOT below threshold
    res = _create_result(default_conf=0.85)
    low = low_confidence_fields(res, threshold=0.85)
    assert len(low) == 0
    assert not needs_review(res, issues=[], threshold=0.85)


def test_boundary_just_under_threshold():
    # 0.849 is strictly below threshold 0.85
    res = _create_result(default_conf=0.95, overrides={"total": 0.849})
    low = low_confidence_fields(res, threshold=0.85)
    assert low == ["total"]
    assert needs_review(res, issues=[], threshold=0.85)


def test_env_var_threshold_override():
    res = _create_result(default_conf=0.88)
    # Default is 0.85, so 0.88 passes
    assert len(low_confidence_fields(res)) == 0

    # With CONFIDENCE_THRESHOLD=0.90, 0.88 is now low confidence
    with patch.dict("os.environ", {"CONFIDENCE_THRESHOLD": "0.90"}):
        low = low_confidence_fields(res)
        assert len(low) == 7  # all 7 counted fields are 0.88 < 0.90
        assert needs_review(res, issues=[])


def test_argument_threshold_override():
    res = _create_result(default_conf=0.88)
    # Argument threshold 0.90 overrides both default and env
    with patch.dict("os.environ", {"CONFIDENCE_THRESHOLD": "0.70"}):
        low = low_confidence_fields(res, threshold=0.90)
        assert len(low) == 7
        assert needs_review(res, issues=[], threshold=0.90)


def test_error_severity_forces_review():
    # All confidences 1.0 (perfect), but an error issue exists
    res = _create_result(default_conf=1.0)
    assert len(low_confidence_fields(res)) == 0

    error_issue = ValidationIssue(
        rule="total_mismatch",
        severity="error",
        field_name="total",
        message="Total mismatch",
    )
    assert needs_review(res, issues=[error_issue]) is True


def test_warning_severity_alone_does_not_force_review():
    # All confidences 1.0, only a warning issue (e.g. line item mismatch)
    res = _create_result(default_conf=1.0)
    warning_issue = ValidationIssue(
        rule="line_items_mismatch",
        severity="warning",
        field_name="subtotal",
        message="Line items mismatch",
    )
    assert needs_review(res, issues=[warning_issue]) is False


def test_currency_low_confidence_ignored():
    # Currency confidence is 0.40, but all 7 counted fields are 0.95
    res = _create_result(default_conf=0.95, overrides={"currency": 0.40})
    low = low_confidence_fields(res, threshold=0.85)
    assert len(low) == 0
    assert not needs_review(res, issues=[], threshold=0.85)


def test_missing_field_falls_below_threshold():
    res = _create_result(default_conf=0.95)
    # Remove total field
    del res.fields["total"]
    low = low_confidence_fields(res, threshold=0.85)
    assert "total" in low
    assert needs_review(res, issues=[])
