"""LLM provider registry (RNF-30)."""

from __future__ import annotations

from typing import Callable

from config.settings import Settings, get_settings
from llm.base import LLMProvider

ProviderFactory = Callable[[Settings], LLMProvider]


def _heuristic_factory(_settings: Settings) -> LLMProvider:
    from llm.heuristic_provider import HeuristicLLMProvider

    return HeuristicLLMProvider()


def _openai_factory(settings: Settings) -> LLMProvider:
    from llm.litellm_runtime import is_usable_openai_key
    from llm.openai_provider import OpenAILLMProvider

    if not is_usable_openai_key(settings.openai_api_key):
        raise RuntimeError(
            "OPENAI_API_KEY is required. Set a valid key in .env "
            "or use LLM_PROVIDER=heuristic for offline analysis."
        )
    return OpenAILLMProvider(settings)


def _anthropic_factory(settings: Settings) -> LLMProvider:
    from llm.litellm_provider import LiteLLMLLMProvider
    from llm.litellm_runtime import is_usable_anthropic_key

    if not is_usable_anthropic_key(settings.anthropic_api_key):
        raise RuntimeError(
            "ANTHROPIC_API_KEY is required when LLM_PROVIDER=anthropic. "
            "Set a valid key in .env or use LLM_PROVIDER=openai."
        )
    return LiteLLMLLMProvider(settings, provider="anthropic")


def _azure_factory(settings: Settings) -> LLMProvider:
    if not settings.azure_openai_endpoint or not settings.azure_openai_api_key:
        raise RuntimeError("Azure OpenAI settings are required when LLM_PROVIDER=azure")
    from llm.azure_openai_provider import AzureOpenAILLMProvider

    return AzureOpenAILLMProvider(settings)


def _local_factory(settings: Settings) -> LLMProvider:
    from llm.local_provider import LocalLLMProvider

    return LocalLLMProvider(settings)


PROVIDER_REGISTRY: dict[str, ProviderFactory] = {
    "heuristic": _heuristic_factory,
    "openai": _openai_factory,
    "anthropic": _anthropic_factory,
    "azure": _azure_factory,
    "local": _local_factory,
}


def get_llm_provider(settings: Settings | None = None) -> LLMProvider:
    settings = settings or get_settings()
    provider = settings.llm_provider.strip().lower()
    factory = PROVIDER_REGISTRY.get(provider)
    if factory is None:
        raise RuntimeError(f"Unsupported LLM provider: {provider}")
    inner = factory(settings)
    if settings.guardrails_enabled:
        from guardrails.gateway import get_guardrails_gateway
        from llm.guarded_provider import GuardedLLMProvider

        return GuardedLLMProvider(inner, gateway=get_guardrails_gateway(settings))
    return inner
