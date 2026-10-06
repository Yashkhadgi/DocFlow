import json
import pytest
from unittest.mock import MagicMock, patch
from anthropic import APIError, APITimeoutError, RateLimitError

from app.extraction.extractor import extract, clean_json_text
from app.extraction.types import ExtractionError


def test_clean_json_text_strips_fences():
    raw_markdown = "```json\n{\"document_type\": \"invoice\", \"fields\": {}}\n```"
    assert clean_json_text(raw_markdown) == '{"document_type": "invoice", "fields": {}}'

    raw_generic = "```\n{\"test\": 123}\n```"
    assert clean_json_text(raw_generic) == '{"test": 123}'

    raw_clean = '{"document_type": "invoice"}'
    assert clean_json_text(raw_clean) == '{"document_type": "invoice"}'


from pathlib import Path

SAMPLE_PDF_BYTES = (Path(__file__).resolve().parent.parent.parent.parent.parent / "samples" / "invoices" / "clean_invoice.pdf").read_bytes()


@patch.dict("os.environ", {"ANTHROPIC_API_KEY": "dummy-key"})
@patch("anthropic.Anthropic")
def test_retry_on_bad_json_then_success(mock_anthropic_class):
    mock_client = MagicMock()
    mock_anthropic_class.return_value = mock_client

    # First attempt returns invalid JSON string, second returns valid JSON
    bad_resp = MagicMock()
    bad_block = MagicMock(type="text", text="Sorry, here is the result: not valid json {")
    bad_resp.content = [bad_block]

    good_resp = MagicMock()
    good_block = MagicMock(
        type="text",
        text=json.dumps({
            "document_type": "invoice",
            "fields": {
                "vendor_name": {"value": "Retry Success Ltd", "confidence": 0.95},
                "invoice_number": {"value": "INV-RETRY-01", "confidence": 0.95},
                "invoice_date": {"value": "2026-09-10", "confidence": 0.95},
                "gstin": {"value": "27AABCA1234F1Z5", "confidence": 0.95},
                "currency": {"value": "INR", "confidence": 0.95},
                "subtotal": {"value": "10000.00", "confidence": 0.95},
                "tax": {"value": "1800.00", "confidence": 0.95},
                "total": {"value": "11800.00", "confidence": 0.95},
            },
            "line_items": [],
        }),
    )
    good_resp.content = [good_block]

    mock_client.messages.create.side_effect = [bad_resp, good_resp]

    result = extract(SAMPLE_PDF_BYTES, "application/pdf")
    assert result.fields["vendor_name"].value == "Retry Success Ltd"
    assert mock_client.messages.create.call_count == 2


@patch.dict("os.environ", {"ANTHROPIC_API_KEY": "dummy-key"})
@patch("anthropic.Anthropic")
def test_retry_exhausted_raises_extraction_error(mock_anthropic_class):
    mock_client = MagicMock()
    mock_anthropic_class.return_value = mock_client

    bad_resp = MagicMock()
    bad_block = MagicMock(type="text", text="Invalid JSON on all attempts")
    bad_resp.content = [bad_block]

    mock_client.messages.create.return_value = bad_resp

    with pytest.raises(ExtractionError, match="Extraction failed after 3 attempts"):
        extract(SAMPLE_PDF_BYTES, "application/pdf")

    assert mock_client.messages.create.call_count == 3


@patch.dict("os.environ", {"ANTHROPIC_API_KEY": "dummy-key"})
@patch("anthropic.Anthropic")
def test_api_timeout_raises_extraction_error(mock_anthropic_class):
    mock_client = MagicMock()
    mock_anthropic_class.return_value = mock_client

    mock_client.messages.create.side_effect = APITimeoutError(request=MagicMock())

    with pytest.raises(ExtractionError, match="Anthropic API request timed out"):
        extract(SAMPLE_PDF_BYTES, "application/pdf")


@patch.dict("os.environ", {"ANTHROPIC_API_KEY": "dummy-key"})
@patch("anthropic.Anthropic")
def test_rate_limit_raises_extraction_error(mock_anthropic_class):
    mock_client = MagicMock()
    mock_anthropic_class.return_value = mock_client

    mock_client.messages.create.side_effect = RateLimitError(
        message="Rate limit exceeded",
        response=MagicMock(status_code=429),
        body=None,
    )

    with pytest.raises(ExtractionError, match="Anthropic API rate limit exceeded"):
        extract(SAMPLE_PDF_BYTES, "application/pdf")
