from __future__ import annotations

from decimal import Decimal
from math import ceil
from typing import Any


class BudgetExceeded(Exception):
    pass


class ProjectExtractionBudget:
    """Atomic cumulative project spend guard, tracked in micro-USD in Redis."""

    # Claude Haiku 4.5 standard rates: $1/MTok input and $5/MTok output.
    INPUT_MICRO_USD_PER_TOKEN = 1
    OUTPUT_MICRO_USD_PER_TOKEN = 5
    _RESERVE_SCRIPT = """
    local used = tonumber(redis.call('GET', KEYS[1]) or '0')
    local reserve = tonumber(ARGV[1])
    local limit = tonumber(ARGV[2])
    if used + reserve > limit then return 0 end
    local total = redis.call('INCRBY', KEYS[1], reserve)
    return total
    """

    def __init__(
        self,
        redis_client: Any,
        *,
        budget_usd: Decimal | str,
        max_input_tokens: int,
        max_output_tokens: int,
    ) -> None:
        self.redis = redis_client
        self.limit_micro_usd = int(Decimal(str(budget_usd)) * 1_000_000)
        self.max_input_tokens = max_input_tokens
        self.max_output_tokens = max_output_tokens
        self.key = "docflow:llm-budget:cumulative:v1"

    @classmethod
    def from_settings(cls, settings: Any) -> "ProjectExtractionBudget":
        from redis import Redis

        redis_client = Redis.from_url(
            settings.redis_url,
            socket_connect_timeout=2,
            socket_timeout=3,
            decode_responses=True,
        )
        return cls(
            redis_client,
            budget_usd=settings.llm_budget_usd,
            max_input_tokens=settings.llm_max_input_tokens,
            max_output_tokens=settings.llm_max_output_tokens,
        )

    def reserve(self, input_tokens: int | None = None) -> int:
        if input_tokens is not None and input_tokens > self.max_input_tokens:
            raise BudgetExceeded(
                f"Document input token limit exceeded ({input_tokens}>{self.max_input_tokens})."
            )
        guarded_input_tokens = ceil(self.max_input_tokens * 1.1)
        worst_case = (
            guarded_input_tokens * self.INPUT_MICRO_USD_PER_TOKEN
            + self.max_output_tokens * self.OUTPUT_MICRO_USD_PER_TOKEN
        )
        try:
            accepted = self.redis.eval(
                self._RESERVE_SCRIPT,
                1,
                self.key,
                worst_case,
                self.limit_micro_usd,
            )
        except Exception as exc:
            raise BudgetExceeded("Could not verify the project extraction budget; request was not sent.") from exc
        if not accepted:
            raise BudgetExceeded("Monthly extraction budget reached; no paid request was sent.")
        return worst_case

    def settle(self, reservation: int, *, input_tokens: int, output_tokens: int) -> int:
        actual = (
            input_tokens * self.INPUT_MICRO_USD_PER_TOKEN
            + output_tokens * self.OUTPUT_MICRO_USD_PER_TOKEN
        )
        # A token-count estimate may be slightly low. Charge any overage rather
        # than concealing it; the preflight and fixed output cap keep it bounded.
        delta = reservation - actual
        if delta:
            self.redis.incrby(self.key, -delta)
        return actual
