"""Prompt-injection heuristics (input-side)."""

from __future__ import annotations

import re

from guardrails.text_utils import normalize_text

_INJECTION_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"\bignore\b.{0,40}\b(all\s+)?(previous|prior|above|system)\b.{0,20}\b(instructions?|prompts?|rules?)\b",
        r"\bdisregard\b.{0,30}\b(instructions?|prompts?|rules?|context)\b",
        r"\bolvida\b.{0,30}\b(las\s+)?(instrucciones|reglas|prompts?)\b",
        r"\b(nuevo|new)\s+(system\s+)?prompt\b",
        r"\byou\s+are\s+now\b",
        r"\bpretend\s+(you are|to be)\b",
        r"\broleplay\s+as\b",
        r"\bact\s+as\s+a\s+(?!tenant|landlord|arrendatario|arrendador\b)",
        r"\b(system|hidden|developer)\s+(prompt|instructions?|message)\b",
        r"\breveal\b.{0,25}\b(system|hidden|secret)\b",
        r"\bjailbreak\b",
        r"\bdan\s+mode\b",
        r"\bdeveloper\s+mode\b",
        r"\boverride\b.{0,20}\b(safety|guardrails?|policies|rules?)\b",
        r"\bforget\b.{0,20}\beverything\b",
        r"\bdo\s+not\b.{0,30}\bfollow\b.{0,20}\b(instructions?|rules?)\b",
        r"\bno\s+sigas\b.{0,30}\b(las\s+)?(instrucciones|reglas)\b",
        r"```\s*system",
        r"<\s*/?\s*system\s*>",
        r"\brole\s*:\s*system\b",
        r"\brepeat\b.{0,30}\b(your\s+)?(system|initial)\b.{0,20}\b(prompt|instructions?)\b",
    )
)


def detect_prompt_injection(text: str) -> str | None:
    """Return a short reason if injection-like content is detected."""
    normalized = normalize_text(text)
    if not normalized:
        return None
    for pattern in _INJECTION_PATTERNS:
        if pattern.search(normalized):
            return "prompt_injection_pattern"
    return None
