from __future__ import annotations

import os
from typing import Optional

from .types import ExtractionResult, ValidationIssue

# Counted fields for confidence threshold evaluation (required fields + key financial/tax identifiers)
COUNTED_FIELDS = [
    "vendor_name",
    "invoice_number",
    "invoice_date",
    "total",
    "gstin",
    "subtotal",
    "tax",
]

DEFAULT_THRESHOLD = 0.85


def _get_effective_threshold(threshold: Optional[float] = None) -> float:
    if threshold is not None:
        return float(threshold)
    env_val = os.environ.get("CONFIDENCE_THRESHOLD")
    if env_val:
        try:
            return float(env_val.strip())
        except ValueError:
            pass
    return DEFAULT_THRESHOLD


def low_confidence_fields(
    result: ExtractionResult,
    threshold: Optional[float] = None,
) -> list[str]:
    """
    Returns the names of counted fields that fall strictly below the confidence threshold.
    Only evaluates: vendor_name, invoice_number, invoice_date, total, gstin, subtotal, tax.
    """
    effective_threshold = _get_effective_threshold(threshold)
    low_fields: list[str] = []

    for field_name in COUNTED_FIELDS:
        field_obj = result.fields.get(field_name)
        if field_obj is None:
            # Missing field implies 0.0 confidence
            low_fields.append(field_name)
        else:
            # Strictly below threshold
            if field_obj.confidence < effective_threshold:
                low_fields.append(field_name)

    return low_fields


def needs_review(
    result: ExtractionResult,
    issues: list[ValidationIssue],
    threshold: Optional[float] = None,
) -> bool:
    """
    Determines if an extracted document requires human review.
    True if:
      1. Any ValidationIssue has severity 'error' (blocking errors), OR
      2. Any counted field has confidence strictly below the threshold.
    Note: Warnings alone do not force human review if all fields are confident.
    """
    # Check for blocking errors
    has_error_severity = any(issue.severity == "error" for issue in issues)
    if has_error_severity:
        return True

    # Check for low confidence fields
    low_fields = low_confidence_fields(result, threshold=threshold)
    return len(low_fields) > 0
