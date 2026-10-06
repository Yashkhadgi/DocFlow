import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from app.extraction.types import ExtractionResult, FieldValue, LineItem, ExtractionError
from app.extraction.extractor import extract, normalize_extraction_data, _normalize_date, _normalize_money


def test_field_value_and_line_item_models():
    fv = FieldValue(value="Acme Corp", confidence=0.98)
    assert fv.value == "Acme Corp"
    assert fv.confidence == 0.98
    assert fv.bbox is None

    li = LineItem(description="Item 1", quantity="2", rate="100.00", amount="200.00", confidence=0.95)
    assert li.description == "Item 1"
    assert li.amount == "200.00"


def test_normalization_helpers():
    assert _normalize_money("₹ 1,500.50") == "1500.50"
    assert _normalize_money("INR 12,000.00") == "12000.00"
    assert _normalize_money("$45.00") == "45.00"
    assert _normalize_money("null") is None
    assert _normalize_money(None) is None

    assert _normalize_date("15/09/2026") == "2026-09-15"
    assert _normalize_date("15-09-2026") == "2026-09-15"
    assert _normalize_date("2026-09-15") == "2026-09-15"
    assert _normalize_date(None) is None


def test_normalize_extraction_data():
    raw_payload = {
        "fields": {
            "vendor_name": {"value": "Apex Infotech", "confidence": 0.99},
            "invoice_number": {"value": "INV-001", "confidence": 0.95},
            "invoice_date": {"value": "15-09-2026", "confidence": 0.90},
            "gstin": {"value": "27AABCA1234F1Z5", "confidence": 0.85},
            "currency": {"value": "inr", "confidence": 0.95},
            "subtotal": {"value": "10,000.00", "confidence": 0.90},
            "tax": {"value": "1,800.00", "confidence": 0.90},
            "total": {"value": "11,800.00", "confidence": 0.95},
        },
        "line_items": [
            {
                "description": "Hosting",
                "quantity": "1",
                "rate": "10,000.00",
                "amount": "10,000.00",
                "confidence": 0.95,
            }
        ],
    }

    result = normalize_extraction_data(raw_payload)
    assert isinstance(result, ExtractionResult)
    assert result.fields["vendor_name"].value == "Apex Infotech"
    assert result.fields["invoice_date"].value == "2026-09-15"
    assert result.fields["currency"].value == "INR"
    assert result.fields["subtotal"].value == "10000.00"
    assert result.fields["total"].value == "11800.00"
    assert len(result.line_items) == 1
    assert result.line_items[0].amount == "10000.00"


def test_extraction_result_json_schema_conformity():
    result = ExtractionResult(
        document_type="invoice",
        fields={
            "vendor_name": FieldValue(value="Acme Corp", confidence=0.98),
            "invoice_number": FieldValue(value="INV-001", confidence=0.99),
            "invoice_date": FieldValue(value="2026-10-01", confidence=0.95),
            "gstin": FieldValue(value="27ABCDE1234F1Z5", confidence=0.90),
            "currency": FieldValue(value="INR", confidence=0.95),
            "subtotal": FieldValue(value="1000.00", confidence=0.95),
            "tax": FieldValue(value="180.00", confidence=0.95),
            "total": FieldValue(value="1180.00", confidence=0.95),
        },
        line_items=[
            LineItem(description="Item A", quantity="1", rate="1000.00", amount="1000.00", confidence=0.95)
        ],
    )
    serialized = result.model_dump()
    assert serialized["document_type"] == "invoice"
    assert "fields" in serialized
    assert "line_items" in serialized
    for f in ["vendor_name", "invoice_number", "invoice_date", "gstin", "currency", "subtotal", "tax", "total"]:
        assert f in serialized["fields"]
        assert "value" in serialized["fields"][f]
        assert "confidence" in serialized["fields"][f]


@patch.dict("os.environ", {"ANTHROPIC_API_KEY": "mock-api-key"})
@patch("anthropic.Anthropic")
def test_extract_mock_success(mock_anthropic_class):
    mock_client = MagicMock()
    mock_anthropic_class.return_value = mock_client

    mock_response = MagicMock()
    mock_text_block = MagicMock()
    mock_text_block.type = "text"
    mock_text_block.text = json.dumps({
        "document_type": "invoice",
        "fields": {
            "vendor_name": {"value": "Apex Infotech Solutions Pvt Ltd", "confidence": 0.98},
            "invoice_number": {"value": "INV-2026-001", "confidence": 0.99},
            "invoice_date": {"value": "2026-09-15", "confidence": 0.95},
            "gstin": {"value": "27AABCA1234F1Z5", "confidence": 0.90},
            "currency": {"value": "INR", "confidence": 0.95},
            "subtotal": {"value": "10000.00", "confidence": 0.96},
            "tax": {"value": "1800.00", "confidence": 0.94},
            "total": {"value": "11800.00", "confidence": 0.97},
        },
        "line_items": [
            {
                "description": "Cloud Hosting Subscription",
                "quantity": "1",
                "rate": "5000.00",
                "amount": "5000.00",
                "confidence": 0.95,
            }
        ],
    })
    mock_response.content = [mock_text_block]
    mock_client.messages.create.return_value = mock_response

    sample_pdf_bytes = (Path(__file__).resolve().parent.parent.parent.parent.parent / "samples" / "invoices" / "clean_invoice.pdf").read_bytes()
    result = extract(sample_pdf_bytes, "application/pdf")

    assert result.fields["vendor_name"].value == "Apex Infotech Solutions Pvt Ltd"
    assert result.fields["total"].value == "11800.00"
    assert len(result.line_items) == 1
