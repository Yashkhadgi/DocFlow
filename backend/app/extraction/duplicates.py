from __future__ import annotations

import re
from typing import Any, Optional

from .types import DuplicateMatch, ExtractionResult

# Legal suffixes to strip during vendor normalization
LEGAL_SUFFIXES_PATTERN = re.compile(
    r"\b(pvt|private|ltd|limited|llp|inc|incorporated|corp|corporation|co|company|gmbh|llc|pllc)\b",
    re.IGNORECASE,
)


def normalize_vendor(name: Optional[str]) -> Optional[str]:
    """
    Normalize vendor name:
    - Lowercase
    - Strip punctuation and legal suffixes (pvt, ltd, llp, inc, etc.)
    - Collapse extra whitespace
    """
    if name is None:
        return None
    s = str(name).strip().lower()
    if not s or s == "null":
        return None

    # Replace & with 'and'
    s = s.replace("&", " and ")

    # Remove legal suffixes
    s = LEGAL_SUFFIXES_PATTERN.sub(" ", s)

    # Remove all punctuation and symbols, keeping only alphanumeric and spaces
    s = re.sub(r"[^\w\s]", " ", s)

    # Collapse whitespace
    s = re.sub(r"\s+", " ", s).strip()
    return s if s else None


def normalize_invoice_number(inv: Optional[str]) -> Optional[str]:
    """
    Normalize invoice number:
    - Uppercase
    - Split into alphabetic and numeric components
    - Strip leading zeros from numeric components
    - Join uniformly (e.g. 'INV-001', 'inv 001', 'INV-1' all become 'INV-1')
    """
    if inv is None:
        return None
    s = str(inv).strip().upper()
    if not s or s == "NULL":
        return None

    # Tokenize into letter chunks and digit chunks
    tokens = re.findall(r"[A-Z]+|\d+", s)
    if not tokens:
        return None

    normalized_tokens: list[str] = []
    for token in tokens:
        if token.isdigit():
            # Strip leading zeros, but keep '0' if all zeros
            normalized_tokens.append(str(int(token)))
        else:
            normalized_tokens.append(token)

    return "-".join(normalized_tokens)


def find_business_duplicate(
    result: ExtractionResult,
    existing: list[dict[str, Any]],
) -> Optional[DuplicateMatch]:
    """
    Pure function to identify business-level duplicates.
    Matches when normalized vendor_name AND normalized invoice_number are identical.
    Returns DuplicateMatch(document_id=id, reason="same_invoice") for the first match,
    or None if no match is found or if required fields are missing.
    """
    if not existing:
        return None

    vendor_field = result.fields.get("vendor_name")
    inv_field = result.fields.get("invoice_number")

    target_vendor_val = vendor_field.value if vendor_field else None
    target_inv_val = inv_field.value if inv_field else None

    target_vendor = normalize_vendor(target_vendor_val)
    target_inv = normalize_invoice_number(target_inv_val)

    # If either target vendor or invoice number is missing, cannot match
    if not target_vendor or not target_inv:
        return None

    for doc in existing:
        doc_id = doc.get("id") or doc.get("document_id")
        if not doc_id:
            continue

        doc_vendor = normalize_vendor(doc.get("vendor_name"))
        doc_inv = normalize_invoice_number(doc.get("invoice_number"))

        if not doc_vendor or not doc_inv:
            continue

        if target_vendor == doc_vendor and target_inv == doc_inv:
            return DuplicateMatch(document_id=str(doc_id), reason="same_invoice")

    return None
