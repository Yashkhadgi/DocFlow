from __future__ import annotations

import base64
import io
import json
import logging
import os
import re
import time
from datetime import datetime
from decimal import Decimal, InvalidOperation
from functools import lru_cache
from typing import Any

from app.config import settings

from .budget import BudgetExceeded, ProjectExtractionBudget
from .prompts import EXTRACTION_SYSTEM_PROMPT
from .types import ExtractionError, ExtractionResult, FieldValue, LineItem

logger = logging.getLogger("docflow.extraction")

EXPECTED_FIELDS = [
    "vendor_name",
    "invoice_number",
    "invoice_date",
    "gstin",
    "currency",
    "subtotal",
    "tax",
    "total",
]

MAX_FILE_SIZE_BYTES = 32 * 1024 * 1024  # 32 MB Anthropic limit
MAX_IMAGE_DIMENSION = 8000


@lru_cache(maxsize=1)
def _build_budget() -> ProjectExtractionBudget:
    return ProjectExtractionBudget.from_settings(settings)


def _redact_api_keys(text: str) -> str:
    """Scrub any accidental API keys from logs or error messages."""
    return re.sub(r"sk-ant-[a-zA-Z0-9_\-]+", "[REDACTED_API_KEY]", text)


def _validate_input_file(file_bytes: bytes, mime_type: str) -> str:
    """
    Validate document bytes before calling the LLM API.
    Raises non-retryable ExtractionError on invalid, corrupted, or oversized inputs.
    """
    if not file_bytes or len(file_bytes) == 0:
        raise ExtractionError("Uploaded file is empty (0 bytes).", retryable=False)

    if len(file_bytes) > MAX_FILE_SIZE_BYTES:
        raise ExtractionError(
            f"File size ({len(file_bytes) / (1024 * 1024):.1f} MB) exceeds maximum allowed limit of 32 MB.",
            retryable=False,
        )

    norm_mime = mime_type.lower().strip()
    allowed_mimes = ("application/pdf", "image/jpeg", "image/jpg", "image/png", "image/webp")

    if norm_mime not in allowed_mimes:
        raise ExtractionError(
            f"Unsupported document MIME type: '{mime_type}'. Supported formats: PDF, JPEG, PNG, WEBP.",
            retryable=False,
        )

    if norm_mime == "application/pdf":
        if not file_bytes.startswith(b"%PDF"):
            raise ExtractionError("Invalid PDF header. File is not a valid PDF document.", retryable=False)
        try:
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(file_bytes), strict=False)
            if getattr(reader, "is_encrypted", False):
                raise ExtractionError(
                    "PDF is password-protected or encrypted. Please upload an unlocked PDF.",
                    retryable=False,
                )
            if len(reader.pages) > settings.llm_max_pdf_pages:
                raise ExtractionError(
                    f"PDF page count ({len(reader.pages)}) exceeds maximum limit of {settings.llm_max_pdf_pages} pages.",
                    retryable=False,
                )
        except ExtractionError:
            raise
        except Exception as e:
            if len(file_bytes) < 30:
                raise ExtractionError(f"PDF document appears corrupted: {e}", retryable=False)
            logger.debug("PDF reader warning: %s", e)

    elif norm_mime in ("image/jpeg", "image/jpg", "image/png", "image/webp"):
        try:
            from PIL import Image
            img = Image.open(io.BytesIO(file_bytes))
            img.verify()
            # Check dimensions
            if img.width > MAX_IMAGE_DIMENSION or img.height > MAX_IMAGE_DIMENSION:
                raise ExtractionError(
                    f"Image dimensions ({img.width}x{img.height}) exceed maximum limit of {MAX_IMAGE_DIMENSION}x{MAX_IMAGE_DIMENSION}.",
                    retryable=False,
                )
        except ExtractionError:
            raise
        except Exception as e:
            raise ExtractionError(f"Image file appears corrupted or unreadable: {e}", retryable=False) from e

    return norm_mime


def _normalize_money(val: Any) -> str | None:
    if val is None:
        return None
    s = str(val).strip()
    if not s or s.lower() == "null":
        return None
    s = re.sub(r"[₹$€£\s]", "", s)
    s = re.sub(r"^(INR|USD|EUR|GBP|Rs\.?)\s*", "", s, flags=re.IGNORECASE).strip()
    s = s.replace(",", "")
    try:
        d = Decimal(s)
        return f"{d:.2f}"
    except (InvalidOperation, ValueError):
        return s if s else None


def _normalize_date(val: Any) -> str | None:
    if val is None:
        return None
    s = str(val).strip()
    if not s or s.lower() == "null":
        return None
    formats = [
        "%Y-%m-%d",
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%Y/%m/%d",
        "%d.%m.%Y",
        "%d %b %Y",
        "%d %B %Y",
        "%b %d, %Y",
        "%B %d, %Y",
    ]
    for fmt in formats:
        try:
            dt = datetime.strptime(s, fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue
    return s


def clean_json_text(text: str) -> str:
    cleaned = text.strip()
    match = re.search(r"```(?:json)?\s*(.*?)\s*```", cleaned, re.DOTALL)
    if match:
        return match.group(1).strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if len(lines) >= 2 and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()
    return cleaned


def normalize_extraction_data(raw_data: dict[str, Any]) -> ExtractionResult:
    if not isinstance(raw_data, dict):
        raise ValueError("Root JSON extracted from document must be an object")

    raw_fields = raw_data.get("fields", {})
    if not isinstance(raw_fields, dict):
        raw_fields = {}

    normalized_fields: dict[str, FieldValue] = {}

    for field_name in EXPECTED_FIELDS:
        field_info = raw_fields.get(field_name)
        if isinstance(field_info, dict):
            val = field_info.get("value")
            conf = field_info.get("confidence", 0.0)
            bbox = field_info.get("bbox")
        elif field_info is not None:
            val = str(field_info)
            conf = 0.90
            bbox = None
        else:
            val = None
            conf = 0.0
            bbox = None

        if val is not None:
            if field_name in ("subtotal", "tax", "total"):
                val = _normalize_money(val)
            elif field_name == "invoice_date":
                val = _normalize_date(val)
            elif field_name == "currency" and isinstance(val, str):
                val = val.strip().upper()
            elif isinstance(val, str):
                val = val.strip() or None

        if val is None:
            conf = 0.0

        try:
            conf_val = float(conf)
            conf_val = max(0.0, min(1.0, conf_val))
        except (TypeError, ValueError):
            conf_val = 0.0

        normalized_fields[field_name] = FieldValue(
            value=val,
            confidence=conf_val,
            bbox=bbox,
        )

    raw_items = raw_data.get("line_items", [])
    normalized_items: list[LineItem] = []
    if isinstance(raw_items, list):
        for item in raw_items:
            if not isinstance(item, dict):
                continue
            desc = item.get("description")
            qty = item.get("quantity")
            rate = item.get("rate")
            amount = item.get("amount")
            conf = item.get("confidence", 0.0)

            normalized_items.append(
                LineItem(
                    description=str(desc).strip() if desc is not None else None,
                    quantity=str(qty).strip() if qty is not None else None,
                    rate=_normalize_money(rate),
                    amount=_normalize_money(amount),
                    confidence=max(0.0, min(1.0, float(conf) if conf is not None else 0.0)),
                )
            )

    return ExtractionResult(
        document_type="invoice",
        fields=normalized_fields,
        line_items=normalized_items,
        raw_model_output=json.dumps(raw_data) if isinstance(raw_data, dict) else None,
    )


def _extract_anthropic(file_bytes: bytes, mime_type: str) -> ExtractionResult:
    """
    Extract structured data from an invoice document using Anthropic Claude Vision.
    Performs pre-flight validation on inputs.
    Retries up to 2 times internally on bad JSON.
    Never logs document contents or API keys.
    Raises ExtractionError with retryable=True/False.
    """
    # 1. Pre-flight validation
    normalized_mime = _validate_input_file(file_bytes, mime_type)
    file_size = len(file_bytes)

    # 2. Check API key
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ExtractionError("ANTHROPIC_API_KEY environment variable is not set.", retryable=False, fallback_allowed=True)

    model_name = os.environ.get("LLM_MODEL", settings.llm_model)

    try:
        from anthropic import (
            Anthropic,
            APIConnectionError,
            APIError,
            APITimeoutError,
            AuthenticationError,
            BadRequestError,
            NotFoundError,
            RateLimitError,
        )
    except ImportError as e:
        raise ExtractionError("Anthropic SDK is not installed.", retryable=False, fallback_allowed=True) from e

    # 3. Lazy client initialization
    try:
        client = Anthropic(api_key=api_key)
    except Exception as err:
        raise ExtractionError("Anthropic client initialization failed.", retryable=True, fallback_allowed=True) from err
    budget = _build_budget()
    b64_data = base64.b64encode(file_bytes).decode("utf-8")

    if normalized_mime == "application/pdf":
        content_block = {
            "type": "document",
            "source": {
                "type": "base64",
                "media_type": "application/pdf",
                "data": b64_data,
            },
        }
    else:
        media_type = "image/jpeg" if normalized_mime in ("image/jpeg", "image/jpg") else normalized_mime
        content_block = {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": media_type,
                "data": b64_data,
            },
        }

    messages: list[dict[str, Any]] = [
        {
            "role": "user",
            "content": [
                content_block,
                {"type": "text", "text": "Extract all fields and line items according to the schema. Return valid JSON only."},
            ],
        }
    ]

    last_error_msg = ""

    for attempt in range(1, 4):
        start_time = time.perf_counter()
        try:
            token_estimate = client.messages.count_tokens(
                model=model_name,
                system=EXTRACTION_SYSTEM_PROMPT,
                messages=messages,
            )
            input_tokens = int(token_estimate.input_tokens)
            if input_tokens > settings.llm_max_input_tokens:
                raise ExtractionError(
                    f"Document input token limit exceeded ({input_tokens}>{settings.llm_max_input_tokens}).",
                    retryable=False,
                )
            reservation = budget.reserve(input_tokens)
            logger.info("Calling Anthropic API (attempt %d/3, size=%d bytes, mime=%s)", attempt, file_size, normalized_mime)
            response = client.messages.create(
                model=model_name,
                max_tokens=settings.llm_max_output_tokens,
                system=EXTRACTION_SYSTEM_PROMPT,
                messages=messages,
                timeout=60.0,
            )

            duration = time.perf_counter() - start_time
            usage = getattr(response, "usage", None)
            billed_input_tokens = input_tokens
            billed_output_tokens = settings.llm_max_output_tokens
            if usage:
                billed_input_tokens = sum(
                    int(getattr(usage, name, 0) or 0)
                    for name in (
                        "input_tokens",
                        "cache_creation_input_tokens",
                        "cache_read_input_tokens",
                    )
                ) or input_tokens
                billed_output_tokens = int(
                    getattr(usage, "output_tokens", settings.llm_max_output_tokens)
                    or settings.llm_max_output_tokens
                )
            budget.settle(
                reservation,
                input_tokens=billed_input_tokens,
                output_tokens=billed_output_tokens,
            )

            logger.info(
                "Document extraction completed: duration=%.2fs, input_tokens=%s, output_tokens=%s, attempt=%d",
                duration,
                billed_input_tokens,
                billed_output_tokens,
                attempt,
            )

            response_text = ""
            for block in response.content:
                if getattr(block, "type", None) == "text":
                    response_text += block.text

            cleaned_text = clean_json_text(response_text)
            parsed_json = json.loads(cleaned_text)

            return normalize_extraction_data(parsed_json)

        except (json.JSONDecodeError, ValueError) as parse_err:
            last_error_msg = f"JSON/Schema parse error: {parse_err}"
            logger.warning("Attempt %d parse error: %s", attempt, parse_err)
            if attempt < 3:
                messages.append({
                    "role": "assistant",
                    "content": response_text if "response_text" in locals() else "",
                })
                messages.append({
                    "role": "user",
                    "content": f"The response was not valid JSON: {parse_err}. Please fix and output ONLY valid JSON.",
                })

        except BudgetExceeded as budget_err:
            raise ExtractionError(str(budget_err), retryable=False) from budget_err

        except ExtractionError:
            raise

        except AuthenticationError as auth_err:
            msg = _redact_api_keys(f"Anthropic authentication failed: {auth_err}")
            raise ExtractionError(msg, retryable=False, fallback_allowed=True) from auth_err

        except (BadRequestError, NotFoundError) as client_err:
            msg = _redact_api_keys(f"Anthropic API client error: {client_err}")
            raise ExtractionError(msg, retryable=False, fallback_allowed=True) from client_err

        except RateLimitError as rl_err:
            msg = _redact_api_keys(f"Anthropic API rate limit exceeded: {rl_err}")
            raise ExtractionError(msg, retryable=True, fallback_allowed=True) from rl_err

        except APITimeoutError as timeout_err:
            msg = _redact_api_keys(f"Anthropic API request timed out: {timeout_err}")
            raise ExtractionError(msg, retryable=True, fallback_allowed=True) from timeout_err

        except APIConnectionError as conn_err:
            msg = _redact_api_keys(f"Anthropic API connection error: {conn_err}")
            raise ExtractionError(msg, retryable=True, fallback_allowed=True) from conn_err

        except APIError as api_err:
            status_code = getattr(api_err, "status_code", 500)
            is_retryable = (status_code >= 500 or status_code == 429)
            msg = _redact_api_keys(f"Anthropic API error (status {status_code}): {api_err}")
            raise ExtractionError(msg, retryable=is_retryable, fallback_allowed=True) from api_err

        except Exception as err:
            msg = _redact_api_keys(f"Unexpected extraction error: {err}")
            raise ExtractionError("Anthropic extraction provider failed.", retryable=True, fallback_allowed=True) from err

    raise ExtractionError(
        f"Extraction failed after 3 attempts: {last_error_msg}",
        retryable=True,
        fallback_allowed=True,
    )


def _extract_gemini(file_bytes: bytes, mime_type: str) -> ExtractionResult:
    """Use Gemini as a document-capable provider fallback."""
    normalized_mime = _validate_input_file(file_bytes, mime_type)
    api_key = os.environ.get("GEMINI_API_KEY") or settings.gemini_api_key
    if not api_key:
        raise ExtractionError("Gemini API key is not configured.", retryable=False)

    import requests

    model = os.environ.get("GEMINI_MODEL", settings.gemini_model)
    encoded = base64.b64encode(file_bytes).decode("ascii")
    prompt_parts = [
        {"inlineData": {"mimeType": normalized_mime, "data": encoded}},
        {"text": "Extract all fields and line items according to the schema. Return valid JSON only."},
    ]
    body = {
        "systemInstruction": {"parts": [{"text": EXTRACTION_SYSTEM_PROMPT}]},
        "contents": [{"role": "user", "parts": prompt_parts}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "maxOutputTokens": settings.llm_max_output_tokens,
        },
    }
    base_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}"
    headers = {"x-goog-api-key": api_key, "content-type": "application/json"}
    budget = _build_budget()
    try:
        count_response = requests.post(
            f"{base_url}:countTokens", headers=headers, json={key: value for key, value in body.items() if key != "generationConfig"}, timeout=30,
        )
        count_response.raise_for_status()
        input_tokens = int(count_response.json().get("totalTokens", 0))
        if input_tokens <= 0:
            raise ExtractionError("Gemini returned an invalid token estimate.", retryable=True)
        if input_tokens > settings.llm_max_input_tokens:
            raise ExtractionError(
                f"Document input token limit exceeded ({input_tokens}>{settings.llm_max_input_tokens}).",
                retryable=False,
            )
        reservation = budget.reserve(input_tokens)
        response = requests.post(f"{base_url}:generateContent", headers=headers, json=body, timeout=60)
        response.raise_for_status()
        data = response.json()
        text = "".join(
            part.get("text", "")
            for part in data["candidates"][0]["content"]["parts"]
        )
        usage = data.get("usageMetadata", {})
        budget.settle(
            reservation,
            input_tokens=int(usage.get("promptTokenCount") or input_tokens),
            output_tokens=int(usage.get("candidatesTokenCount") or settings.llm_max_output_tokens),
        )
        return normalize_extraction_data(json.loads(clean_json_text(text)))
    except BudgetExceeded as exc:
        raise ExtractionError(str(exc), retryable=False) from exc
    except ExtractionError:
        raise
    except requests.HTTPError as exc:
        status = getattr(exc.response, "status_code", 500)
        raise ExtractionError(
            f"Gemini extraction provider failed (status {status}).",
            retryable=status >= 500 or status == 429,
        ) from exc
    except (requests.RequestException, KeyError, IndexError, TypeError, ValueError) as exc:
        raise ExtractionError("Gemini extraction provider failed.", retryable=True) from exc


def extract(file_bytes: bytes, mime_type: str) -> ExtractionResult:
    """Try Anthropic first and fall back to Gemini only on provider failures."""
    try:
        return _extract_anthropic(file_bytes, mime_type)
    except ExtractionError as primary_error:
        gemini_key = os.environ.get("GEMINI_API_KEY") or settings.gemini_api_key
        if not (primary_error.fallback_allowed and settings.gemini_fallback_enabled and gemini_key):
            raise
        logger.warning("Anthropic unavailable; attempting Gemini fallback (%s)", type(primary_error).__name__)
        try:
            return _extract_gemini(file_bytes, mime_type)
        except ExtractionError as backup_error:
            raise ExtractionError(
                "both extraction providers failed; retry may succeed.",
                retryable=backup_error.retryable,
            ) from backup_error
