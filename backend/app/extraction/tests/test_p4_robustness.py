import io
import pytest
from unittest.mock import MagicMock, patch
from anthropic import (
    APIConnectionError,
    APIError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    RateLimitError,
)

from app.extraction.extractor import extract, _validate_input_file, _redact_api_keys
from app.extraction.types import ExtractionError


def test_empty_file_raises_non_retryable():
    with pytest.raises(ExtractionError) as exc_info:
        extract(b"", "application/pdf")
    assert exc_info.value.retryable is False
    assert "empty" in exc_info.value.message.lower()


def test_unsupported_mime_type_raises_non_retryable():
    with pytest.raises(ExtractionError) as exc_info:
        extract(b"%PDF-test", "application/zip")
    assert exc_info.value.retryable is False
    assert "unsupported" in exc_info.value.message.lower()


def test_oversized_file_raises_non_retryable():
    huge_bytes = b"0" * (33 * 1024 * 1024)
    with pytest.raises(ExtractionError) as exc_info:
        extract(huge_bytes, "application/pdf")
    assert exc_info.value.retryable is False
    assert "exceeds maximum" in exc_info.value.message.lower()


def test_corrupted_pdf_raises_non_retryable():
    bad_pdf_bytes = b"This is not a pdf file at all"
    with pytest.raises(ExtractionError) as exc_info:
        extract(bad_pdf_bytes, "application/pdf")
    assert exc_info.value.retryable is False
    assert "valid pdf" in exc_info.value.message.lower() or "corrupted" in exc_info.value.message.lower()


def test_corrupted_image_raises_non_retryable():
    bad_img_bytes = b"\xFF\xD8\xFFcorrupted_image_bytes_here"
    with pytest.raises(ExtractionError) as exc_info:
        extract(bad_img_bytes, "image/jpeg")
    assert exc_info.value.retryable is False
    assert "corrupted" in exc_info.value.message.lower()


from pathlib import Path

SAMPLE_PDF_BYTES = (Path(__file__).resolve().parent.parent.parent.parent.parent / "samples" / "invoices" / "clean_invoice.pdf").read_bytes()


@patch.dict("os.environ", {"ANTHROPIC_API_KEY": "sk-ant-fakekey-12345"})
@patch("anthropic.Anthropic")
def test_rate_limit_error_is_retryable(mock_anthropic_class):
    mock_client = MagicMock()
    mock_anthropic_class.return_value = mock_client
    mock_client.messages.create.side_effect = RateLimitError(
        message="Rate limit",
        response=MagicMock(status_code=429),
        body=None,
    )

    with pytest.raises(ExtractionError) as exc_info:
        extract(SAMPLE_PDF_BYTES, "application/pdf")
    assert exc_info.value.retryable is True


@patch.dict("os.environ", {"ANTHROPIC_API_KEY": "sk-ant-fakekey-12345"})
@patch("anthropic.Anthropic")
def test_timeout_error_is_retryable(mock_anthropic_class):
    mock_client = MagicMock()
    mock_anthropic_class.return_value = mock_client
    mock_client.messages.create.side_effect = APITimeoutError(request=MagicMock())

    with pytest.raises(ExtractionError) as exc_info:
        extract(SAMPLE_PDF_BYTES, "application/pdf")
    assert exc_info.value.retryable is True


@patch.dict("os.environ", {"ANTHROPIC_API_KEY": "sk-ant-fakekey-12345"})
@patch("anthropic.Anthropic")
def test_auth_error_is_not_retryable(mock_anthropic_class):
    mock_client = MagicMock()
    mock_anthropic_class.return_value = mock_client
    mock_client.messages.create.side_effect = AuthenticationError(
        message="Invalid API Key sk-ant-secret-key-67890",
        response=MagicMock(status_code=401),
        body=None,
    )

    with pytest.raises(ExtractionError) as exc_info:
        extract(SAMPLE_PDF_BYTES, "application/pdf")
    assert exc_info.value.retryable is False
    # Verify API key is redacted
    assert "sk-ant-secret-key-67890" not in exc_info.value.message
    assert "[REDACTED_API_KEY]" in exc_info.value.message


def test_api_key_redaction_helper():
    sample_text = "Error occurred with key sk-ant-api03-abcdef123456-XYZ at endpoint"
    redacted = _redact_api_keys(sample_text)
    assert "sk-ant-" not in redacted
    assert "[REDACTED_API_KEY]" in redacted
