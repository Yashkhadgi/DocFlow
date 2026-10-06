from __future__ import annotations

from dataclasses import dataclass


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


def stub_extract(file_bytes: bytes, mime_type: str) -> StubExtractionResult:
    low_confidence = len(file_bytes) % 3 == 0
    gstin_confidence = 0.62 if low_confidence else 0.92
    return StubExtractionResult(
        document_type="invoice",
        fields={
            "vendor_name": StubField("Acme Traders", 0.97),
            "invoice_number": StubField("INV-001", 0.99),
            "invoice_date": StubField("2026-10-01", 0.95),
            "gstin": StubField("27ABCDE1234F1Z5", gstin_confidence),
            "currency": StubField("INR", 0.90),
            "subtotal": StubField("10000.00", 0.96),
            "tax": StubField("1800.00", 0.94),
            "total": StubField("11800.00", 0.97),
        },
        line_items=[
            StubLineItem("Steel rods", "10", "1000.00", "10000.00", 0.95),
        ],
    )
