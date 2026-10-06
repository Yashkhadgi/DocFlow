from __future__ import annotations

import re
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from typing import Optional

from .types import ExtractionResult, ValidationIssue

GSTIN_REGEX = re.compile(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$")
REQUIRED_FIELDS = ["vendor_name", "invoice_number", "invoice_date", "total"]


def _to_decimal(val: Optional[str]) -> Optional[Decimal]:
    if val is None:
        return None
    s = str(val).strip()
    if not s:
        return None
    try:
        return Decimal(s)
    except (InvalidOperation, ValueError):
        return None


def validate(result: ExtractionResult) -> list[ValidationIssue]:
    """
    Pure validation function executing frozen business rules. No I/O.
    Returns a list of ValidationIssue instances.
    """
    issues: list[ValidationIssue] = []
    fields = result.fields

    # Rule 1: missing_required (vendor_name, invoice_number, invoice_date, total)
    for req_field in REQUIRED_FIELDS:
        field_obj = fields.get(req_field)
        val = field_obj.value if field_obj else None
        if val is None or not str(val).strip():
            issues.append(
                ValidationIssue(
                    rule="missing_required",
                    severity="error",
                    field_name=req_field,
                    message=f"Required field '{req_field}' is missing",
                )
            )

    # Rule 2: invalid_gstin
    gstin_field = fields.get("gstin")
    gstin_val = gstin_field.value if gstin_field else None
    if gstin_val is not None and str(gstin_val).strip():
        clean_gstin = str(gstin_val).strip().upper()
        if not GSTIN_REGEX.match(clean_gstin):
            issues.append(
                ValidationIssue(
                    rule="invalid_gstin",
                    severity="error",
                    field_name="gstin",
                    message=f"GSTIN '{gstin_val}' does not match standard 15-digit format",
                )
            )

    # Rule 3: invalid_date (must be valid ISO YYYY-MM-DD and not more than 1 day in the future)
    date_field = fields.get("invoice_date")
    date_val = date_field.value if date_field else None
    if date_val is not None and str(date_val).strip():
        date_str = str(date_val).strip()
        try:
            parsed_dt = datetime.strptime(date_str, "%Y-%m-%d").date()
            # Allow up to 1 day in the future (timezone difference tolerance)
            max_future_date = date.today() + timedelta(days=1)
            if parsed_dt > max_future_date:
                issues.append(
                    ValidationIssue(
                        rule="invalid_date",
                        severity="error",
                        field_name="invoice_date",
                        message=f"Invoice date '{date_str}' is in the future by more than 1 day",
                    )
                )
        except ValueError:
            issues.append(
                ValidationIssue(
                    rule="invalid_date",
                    severity="error",
                    field_name="invoice_date",
                    message=f"Invoice date '{date_str}' is not a valid ISO date (YYYY-MM-DD)",
                )
            )

    # Rule 4: total_mismatch (abs((subtotal + tax) - total) > 0.01)
    subtotal_dec = _to_decimal(fields.get("subtotal").value if fields.get("subtotal") else None)
    tax_dec = _to_decimal(fields.get("tax").value if fields.get("tax") else None)
    total_dec = _to_decimal(fields.get("total").value if fields.get("total") else None)

    if subtotal_dec is not None and tax_dec is not None and total_dec is not None:
        expected_total = subtotal_dec + tax_dec
        diff = abs(expected_total - total_dec)
        if diff > Decimal("0.01"):
            issues.append(
                ValidationIssue(
                    rule="total_mismatch",
                    severity="error",
                    field_name="total",
                    message=f"subtotal ({subtotal_dec:.2f}) + tax ({tax_dec:.2f}) = {expected_total:.2f} but total is {total_dec:.2f}",
                )
            )

    # Rule 5: line_items_mismatch (abs(sum(line amounts) - subtotal) > 0.01)
    if subtotal_dec is not None and result.line_items:
        item_amounts = [_to_decimal(it.amount) for it in result.line_items if _to_decimal(it.amount) is not None]
        if item_amounts and len(item_amounts) == len(result.line_items):
            sum_line_amounts = sum(item_amounts, Decimal("0.00"))
            if abs(sum_line_amounts - subtotal_dec) > Decimal("0.01"):
                issues.append(
                    ValidationIssue(
                        rule="line_items_mismatch",
                        severity="warning",
                        field_name="subtotal",
                        message=f"sum of line items ({sum_line_amounts:.2f}) does not match subtotal ({subtotal_dec:.2f})",
                    )
                )

    return issues
