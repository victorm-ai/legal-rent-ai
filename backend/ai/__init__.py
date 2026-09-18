"""AI capabilities boundary (LLM, guardrails, agents) — in-process today, remote-ready."""

from ai.runtime import AIRuntime, get_ai_runtime

__all__ = ["AIRuntime", "get_ai_runtime"]
