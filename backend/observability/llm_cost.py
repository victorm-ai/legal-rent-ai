"""Estimate LLM call cost from LiteLLM when usage is available."""

from __future__ import annotations

from typing import Any


def estimate_completion_cost_usd(model: str, usage: dict[str, Any] | None) -> float | None:
    if not usage:
        return None
    prompt_tokens = usage.get("prompt_tokens")
    completion_tokens = usage.get("completion_tokens")
    if prompt_tokens is None and completion_tokens is None:
        return None
    try:
        from litellm import completion_cost

        return float(
            completion_cost(
                model=model,
                prompt_tokens=int(prompt_tokens or 0),
                completion_tokens=int(completion_tokens or 0),
            )
        )
    except Exception:
        return None
