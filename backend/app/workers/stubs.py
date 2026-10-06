from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
import re

from app.config import settings


@dataclass
class StubField:
    value: str | None
    confidence: float
    bbox: dict | None = None


@dataclass
class StubLineItem:
    description: str | None
    quantity: str | None
    rate: str | None
    amount: str | None
    confidence: float


@dataclass
class StubExtractionResult:
    document_type: str
    fields: dict[str, StubField]
    line_items: list[StubLineItem]
    raw_model_output: str | None = None


def stub_extract(
    file_bytes: bytes,
    mime_type: str,
    filename: str | None = None,
    attempt: int | None = None,
) -> StubExtractionResult:
    failure_marker = settings.force_fail_filename_contains
    if failure_marker and filename and failure_marker in filename:
        failure_limit = settings.force_fail_until_attempt
        if failure_limit <= 0 or attempt is None or attempt <= failure_limit:
            raise RuntimeError(f"Stub extraction forced to fail for {filename}")

    digest = int(sha256(file_bytes).hexdigest(), 16)
    low_confidence = digest % 3 == 0
    total_mismatch = digest % 5 == 0
    gstin_confidence = 0.62 if low_confidence else 0.92
    vendor_name, invoice_number = _stub_business_identity(file_bytes, filename)
    return StubExtractionResult(
        document_type="invoice",
        fields={
            "vendor_name": StubField(vendor_name, 0.97),
            "invoice_number": StubField(invoice_number, 0.99),
            "invoice_date": StubField("2026-10-01", 0.95),
            "gstin": StubField("27ABCDE1234F1Z5", gstin_confidence),
            "currency": StubField("INR", 0.90),
            "subtotal": StubField("10000.00", 0.96),
            "tax": StubField("1800.00", 0.94),
            "total": StubField("12000.00" if total_mismatch else "11800.00", 0.97),
        },
        line_items=[
            StubLineItem("Steel rods", "10", "1000.00", "10000.00", 0.95),
        ],
    )


def _stub_business_identity(file_bytes: bytes, filename: str | None) -> tuple[str, str]:
    """Return stable fake business fields without making every upload a duplicate."""
    normalized_name = _normalize_filename(filename)
    if normalized_name in {"clean_invoice", "clean_invoice_copy", "same_invoice_resaved"}:
        return "Acme Traders", "INV-001"

    digest_hex = sha256(file_bytes).hexdigest()
    invoice_suffix = int(digest_hex[:8], 16) % 900_000 + 100_000
    vendor_suffix = int(digest_hex[8:12], 16) % 100
    return f"Demo Vendor {vendor_suffix:02d}", f"INV-{invoice_suffix}"


def _normalize_filename(filename: str | None) -> str:
    if not filename:
        return ""
    stem = Path(filename).stem.lower()
    return re.sub(r"[^a-z0-9]+", "_", stem).strip("_")
