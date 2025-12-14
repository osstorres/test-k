from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any, Dict
from uuid import UUID
import time


llm_usage_context_var: ContextVar["LLMUsageContext | None"] = ContextVar(
    "llm_usage_context", default=None
)


@dataclass
class LLMUsageContext:
    request_id: str
    path: str
    method: str
    user_id: UUID | None = None
    organization_id: UUID | None = None
    provider: str | None = None
    model: str | None = None
    tokens_used: int = 0
    tokens_prompt: int = 0
    tokens_completion: int = 0
    llm_calls: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    start_time: float = field(default_factory=time.perf_counter)
    organization_monthly_token_limit: int | None = None
    organization_monthly_request_limit: int | None = None

    @property
    def has_usage(self) -> bool:
        return self.llm_calls > 0

    def record_call(
        self,
        *,
        provider: str | None = None,
        model: str | None = None,
        tokens_used: int | None = None,
        tokens_prompt: int | None = None,
        tokens_completion: int | None = None,
        metadata: Dict[str, Any] | None = None,
    ) -> None:
        self.llm_calls += 1
        if tokens_used:
            self.tokens_used += tokens_used
        if provider:
            self.provider = provider
        if model:
            self.model = model
        if tokens_prompt:
            self.tokens_prompt += tokens_prompt
        if tokens_completion:
            self.tokens_completion += tokens_completion
        if metadata:
            self.metadata.update(metadata)


def set_current_llm_usage_context(context: LLMUsageContext):
    """Store context so other modules can fetch usage metrics."""
    return llm_usage_context_var.set(context)


def get_current_llm_usage_context() -> LLMUsageContext | None:
    """Retrieve the usage context attached to the current request."""
    return llm_usage_context_var.get()
