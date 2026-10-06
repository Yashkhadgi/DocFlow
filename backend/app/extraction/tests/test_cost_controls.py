from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.extraction.budget import BudgetExceeded, ProjectExtractionBudget
from app.extraction import extractor
from app.extraction.extractor import extract
from app.extraction.types import ExtractionError
from app.config import settings


class FakeRedis:
    def __init__(self, reserve_result=1):
        self.reserve_result = reserve_result
        self.eval_calls = []
        self.incrby_calls = []

    def eval(self, script, numkeys, key, reservation, limit):
        self.eval_calls.append((numkeys, key, int(reservation), int(limit)))
        return self.reserve_result

    def incrby(self, key, amount):
        self.incrby_calls.append((key, amount))


def test_budget_reserves_full_worst_case_and_refunds_unused_cost():
    redis = FakeRedis()
    budget = ProjectExtractionBudget(
        redis,
        budget_usd="0.15",
        max_input_tokens=8000,
        max_output_tokens=1024,
    )

    reservation = budget.reserve()
    assert reservation == 13_920  # $0.01392, including a 10% input-token buffer.
    assert redis.eval_calls[0][1] == "docflow:llm-budget:cumulative:v1"
    assert redis.eval_calls[0][2:] == (13_920, 150_000)

    actual = budget.settle(reservation, input_tokens=2000, output_tokens=400)
    assert actual == 4_000
    assert redis.incrby_calls[0][1] == -(reservation - actual)


def test_budget_rejects_when_cumulative_cap_has_no_room():
    redis = FakeRedis(reserve_result=0)
    budget = ProjectExtractionBudget(
        redis,
        budget_usd="0.15",
        max_input_tokens=8000,
        max_output_tokens=1024,
    )

    with pytest.raises(BudgetExceeded):
        budget.reserve()


def test_budget_refuses_actual_token_counts_above_configured_bound():
    budget = ProjectExtractionBudget(
        FakeRedis(),
        budget_usd="0.15",
        max_input_tokens=8000,
        max_output_tokens=1024,
    )

    with pytest.raises(BudgetExceeded):
        budget.reserve(input_tokens=8001)


@patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"})
@patch("anthropic.Anthropic")
def test_extractor_blocks_over_limit_input_before_paid_message(mock_anthropic, monkeypatch):
    monkeypatch.setattr(settings, "llm_max_input_tokens", 8000)
    client = MagicMock()
    mock_anthropic.return_value = client
    client.messages.count_tokens.return_value.input_tokens = 8001

    with pytest.raises(ExtractionError, match="input token limit") as error:
        extract(b"%PDF-1.4\n" + b"content " * 100, "application/pdf")

    assert error.value.retryable is False
    client.messages.create.assert_not_called()


@patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"})
@patch("anthropic.Anthropic")
def test_extractor_does_not_send_paid_request_when_budget_is_exhausted(mock_anthropic, monkeypatch):
    client = MagicMock()
    mock_anthropic.return_value = client
    client.messages.count_tokens.return_value.input_tokens = 100
    monkeypatch.setattr(
        extractor,
        "_build_budget",
        lambda: ProjectExtractionBudget(
            FakeRedis(reserve_result=0),
            budget_usd="0.15",
            max_input_tokens=8000,
            max_output_tokens=1024,
        ),
    )

    with pytest.raises(ExtractionError, match="Monthly extraction budget reached") as error:
        extract(b"%PDF-1.4\n" + b"content " * 100, "application/pdf")

    assert error.value.retryable is False
    client.messages.create.assert_not_called()


def test_default_model_is_current_haiku_45():
    assert settings.llm_model == "claude-haiku-4-5-20251001"


def test_retries_on_gemini_only_after_primary_provider_failure(monkeypatch):
    expected = object()
    calls = []

    def primary(*_args):
        calls.append("anthropic")
        raise ExtractionError("primary unavailable", retryable=True, fallback_allowed=True)

    def backup(*_args):
        calls.append("gemini")
        return expected

    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
    monkeypatch.setattr(extractor, "_extract_anthropic", primary)
    monkeypatch.setattr(extractor, "_extract_gemini", backup)

    assert extract(b"pdf", "application/pdf") is expected
    assert calls == ["anthropic", "gemini"]


def test_primary_success_does_not_call_gemini(monkeypatch):
    expected = object()
    monkeypatch.setattr(extractor, "_extract_anthropic", lambda *_args: expected)
    monkeypatch.setattr(
        extractor,
        "_extract_gemini",
        lambda *_args: pytest.fail("Gemini must not run when Anthropic succeeds"),
    )

    assert extract(b"pdf", "application/pdf") is expected


def test_no_gemini_key_keeps_primary_error(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setattr(
        extractor,
        "_extract_anthropic",
        lambda *_args: (_ for _ in ()).throw(
            ExtractionError("primary unavailable", retryable=True, fallback_allowed=True)
        ),
    )
    monkeypatch.setattr(
        extractor,
        "_extract_gemini",
        lambda *_args: pytest.fail("Gemini cannot run without a key"),
    )

    with pytest.raises(ExtractionError, match="primary unavailable"):
        extract(b"pdf", "application/pdf")


def test_does_not_fail_over_for_local_validation_or_budget_error(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
    monkeypatch.setattr(
        extractor,
        "_extract_anthropic",
        lambda *_args: (_ for _ in ()).throw(
            ExtractionError("bad input", retryable=False, fallback_allowed=False)
        ),
    )
    monkeypatch.setattr(
        extractor,
        "_extract_gemini",
        lambda *_args: pytest.fail("local errors must not trigger provider failover"),
    )

    with pytest.raises(ExtractionError, match="bad input"):
        extract(b"pdf", "application/pdf")


def test_reports_safe_error_when_both_providers_fail(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
    monkeypatch.setattr(
        extractor,
        "_extract_anthropic",
        lambda *_args: (_ for _ in ()).throw(
            ExtractionError("primary unavailable", retryable=True, fallback_allowed=True)
        ),
    )
    monkeypatch.setattr(
        extractor,
        "_extract_gemini",
        lambda *_args: (_ for _ in ()).throw(ExtractionError("backup unavailable", retryable=True)),
    )

    with pytest.raises(ExtractionError, match="both extraction providers failed") as error:
        extract(b"pdf", "application/pdf")
    assert error.value.retryable is True


def test_gemini_sends_inline_pdf_and_normalizes_result(monkeypatch):
    class Response:
        def __init__(self, data):
            self.data = data

        def raise_for_status(self):
            return None

        def json(self):
            return self.data

    requests = []
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
    monkeypatch.setattr(extractor, "_build_budget", lambda: type("Budget", (), {
        "reserve": lambda _self, _tokens: 100,
        "settle": lambda *_args, **_kwargs: None,
    })())

    def post(url, **kwargs):
        requests.append((url, kwargs))
        if url.endswith(":countTokens"):
            return Response({"totalTokens": 20})
        return Response({
            "candidates": [{"content": {"parts": [{"text": '{"fields": {}, "line_items": []}'}]}}],
            "usageMetadata": {"promptTokenCount": 20, "candidatesTokenCount": 10},
        })

    monkeypatch.setattr("requests.post", post)
    result = extractor._extract_gemini(b"%PDF-1.4\n" + b"content " * 10, "application/pdf")

    assert result.document_type == "invoice"
    assert len(requests) == 2
    assert requests[1][1]["json"]["contents"][0]["parts"][0]["inlineData"]["mimeType"] == "application/pdf"
    assert requests[1][1]["headers"]["x-goog-api-key"] == "test-gemini-key"
