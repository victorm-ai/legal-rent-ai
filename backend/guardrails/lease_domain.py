"""Lease-domain detection for analysis inputs."""

from __future__ import annotations

import re

from guardrails.text_utils import normalize_text

_LEASE_POSITIVE_PATTERNS = (
    r"\bcontrato de arrendamiento\b",
    r"\bcontrato de locacion\b",
    r"\blease agreement\b",
    r"\brental agreement\b",
    r"\btenancy agreement\b",
    r"\barrendamiento\b",
    r"\barrendador\b",
    r"\barrendatario\b",
    r"\blocador\b",
    r"\blocatario\b",
    r"\brenta mensual\b",
    r"\bmonthly rent\b",
    r"\binmueble\b",
    r"\bdep[oó]sito en garant[ií]a\b",
    r"\bsecurity deposit\b",
    r"\bfiador\b",
    r"\bobligado solidario\b",
    r"\bprorroga\b",
    r"\brenewal\b",
    r"\bterminacion anticipada\b",
    r"\bearly termination\b",
    r"\banexo\b.{0,30}\b(contrato|arrendamiento|lease)\b",
)

_NON_LEASE_PATTERNS = (
    r"\bcontrato de trabajo\b",
    r"\bemployment agreement\b",
    r"\blabor contract\b",
    r"\bcompraventa\b",
    r"\bpurchase agreement\b",
    r"\bsale of goods\b",
    r"\bloan agreement\b",
    r"\bcredit agreement\b",
    r"\bprestacion de servicios\b",
    r"\bservices agreement\b",
    r"\bnda\b",
    r"\bnon[- ]disclosure\b",
    r"\bmatrimonial\b",
    r"\bprenuptial\b",
    r"\bsoftware license\b",
    r"\blicencia de software\b",
)


def _count_patterns(text: str, patterns: tuple[str, ...]) -> int:
    return sum(1 for pattern in patterns if re.search(pattern, text, re.IGNORECASE))


def lease_domain_score(text: str) -> tuple[float, float]:
    """Return (lease_signal, non_lease_signal) in range ~0..1."""
    normalized = normalize_text(text)
    if not normalized:
        return 0.0, 0.0
    lease_hits = _count_patterns(normalized, _LEASE_POSITIVE_PATTERNS)
    other_hits = _count_patterns(normalized, _NON_LEASE_PATTERNS)
    length_factor = min(len(normalized) / 4000, 1.0)
    lease_score = min(lease_hits * 0.22 + (0.12 if lease_hits else 0), 1.0)
    if lease_hits == 0 and length_factor > 0.15:
        lease_score *= 0.35
    other_score = min(other_hits * 0.35, 1.0)
    return round(lease_score, 4), round(other_score, 4)


def is_lease_contract_text(text: str, *, min_lease_score: float = 0.22) -> bool:
    lease_score, other_score = lease_domain_score(text)
    if other_score >= 0.5 and other_score > lease_score:
        return False
    if other_score >= 0.35 and lease_score < 0.35:
        return False
    return lease_score >= min_lease_score
