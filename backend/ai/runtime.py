"""In-process AI runtime (default). Swap for HTTP client when splitting to a separate container."""

from __future__ import annotations

from collections.abc import Iterator
from functools import lru_cache
from typing import Any

from agents.signing_coordination.context import SigningCoordinationContext
from agents.signing_coordination.runner import run_signing_coordination_agent
from config.settings import Settings, get_settings
from guardrails.gateway import GuardrailsGateway, get_guardrails_gateway
from llm.base import AnalysisPipelineResult
from llm.chat_provider import ContractChatLLM
from llm.registry import get_llm_provider
from observability.chat_llm_tracker import ChatObservabilityContext


class AIRuntime:
    """Facade for analysis, chat, guardrails, and LangGraph agents."""

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        chat_llm: ContractChatLLM | None = None,
        guardrails: GuardrailsGateway | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._chat = chat_llm or ContractChatLLM(self._settings)
        self._guardrails = guardrails or get_guardrails_gateway(self._settings)

    def analyze_contract(
        self,
        contract_text: str,
        perspective: str,
        title: str | None = None,
    ) -> AnalysisPipelineResult:
        provider = get_llm_provider(self._settings)
        return provider.analyze_contract(
            contract_text=contract_text,
            perspective=perspective,
            title=title,
        )

    def validate_chat_message(self, content: str, history: list[dict[str, str]]) -> None:
        self._guardrails.validate_chat_message(content, history)

    def chat_answer(
        self,
        question: str,
        contract_text: str,
        context: dict[str, Any],
        history: list[dict[str, str]],
        *,
        observability: ChatObservabilityContext | None = None,
    ) -> dict[str, Any]:
        return self._chat.answer(
            question,
            contract_text,
            context,
            history,
            observability=observability,
        )

    def chat_stream(
        self,
        question: str,
        contract_text: str,
        context: dict[str, Any],
        history: list[dict[str, str]],
        *,
        observability: ChatObservabilityContext | None = None,
    ) -> Iterator[dict[str, Any]]:
        yield from self._chat.stream_answer(
            question,
            contract_text,
            context,
            history,
            observability=observability,
        )

    def run_signing_coordination(self, ctx: SigningCoordinationContext) -> None:
        run_signing_coordination_agent(ctx, self._settings)


@lru_cache
def get_ai_runtime() -> AIRuntime:
    return AIRuntime(get_settings())
