"""Guardrail violation types."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GuardrailViolation(Exception):
    """Raised when input fails guardrails before reaching the LLM."""

    code: str
    user_message: str
    detail: str = ""

    def __str__(self) -> str:
        return self.user_message
