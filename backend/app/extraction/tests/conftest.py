import pytest

from app.extraction import extractor


class TestBudget:
    def reserve(self, input_tokens=None):
        if input_tokens is not None and input_tokens > extractor.settings.llm_max_input_tokens:
            raise extractor.BudgetExceeded("input token limit")
        return 0

    def settle(self, reservation, *, input_tokens, output_tokens):
        return 0


@pytest.fixture(autouse=True)
def use_test_budget(monkeypatch):
    monkeypatch.setattr(extractor, "_build_budget", lambda: TestBudget())
