"""LLM provider for eval runs (no guardrails, no DB side effects)."""

from __future__ import annotations

from config.settings import Settings
from llm.base import LLMProvider
from llm.registry import PROVIDER_REGISTRY


def get_eval_llm_provider(settings: Settings) -> LLMProvider:
    """Return the configured analysis provider without GuardedLLMProvider."""
    provider = settings.llm_provider.strip().lower()
    factory = PROVIDER_REGISTRY.get(provider)
    if factory is None:
        raise RuntimeError(f"Unsupported LLM provider for eval: {provider}")
    return factory(settings)
