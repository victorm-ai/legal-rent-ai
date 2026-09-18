"""Unified field extraction helpers for lease contracts (RF-14)."""

from __future__ import annotations

import re
from typing import Any

from llm.field_specs import CLAUSE_CATEGORY_FIELD_MAP, FIELD_SPECS, RF14_FIELD_NAMES

_MONEY_FIELDS = {"renta_mensual", "deposito", "garantia", "penalizacion"}
_JURISDICTION_PATTERNS = (
    r"(?:Estado de|Ciudad de)\s+([A-Za-zÁÉÍÓÚáéíóúñ\s]+?)(?:\.|,|\n|$)",
    r"tribunales del Estado de\s+([A-Za-zÁÉÍÓÚáéíóúñ\s]+?)(?:\.|,|\n|$)",
    r"foro\s+(?:de|en)\s+(?:los tribunales del )?(?:Estado de\s+)?([A-Za-zÁÉÍÓÚáéíóúñ\s]+?)(?:\.|,|\n|$)",
)


def normalize_jurisdiction_value(raw: str) -> str:
    """Reduce jurisdiction text to a concise place name for storage (RF-10/RF-14)."""
    cleaned = " ".join(raw.split())
    if not cleaned:
        return cleaned
    for pattern in _JURISDICTION_PATTERNS:
        match = re.search(pattern, cleaned, re.IGNORECASE)
        if match:
            return " ".join(match.group(1).split())[:100]
    return cleaned[:100]


def extract_field_value(match: re.Match[str]) -> str:
    """Return the captured value from a regex match."""
    if match.lastindex and match.lastindex >= 1:
        raw = match.group(1)
    else:
        raw = match.group(0)
    return " ".join(raw.split())


def extract_fields_from_text(text: str) -> list[dict[str, Any]]:
    """Extract all RF-14 fields present in contract text."""
    fields: list[dict[str, Any]] = []
    for field_name in RF14_FIELD_NAMES:
        patterns = FIELD_SPECS.get(field_name, [])
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if not match:
                continue
            value = extract_field_value(match)
            if field_name in _MONEY_FIELDS and not re.search(r"\d", value):
                if field_name != "garantia":
                    continue
            if len(value) < 2:
                continue
            if field_name == "jurisdiccion":
                value = normalize_jurisdiction_value(value)
                if not value:
                    continue
            snippet = text[max(0, match.start() - 20) : match.end() + 40][:300]
            fields.append(
                {
                    "field_name": field_name,
                    "field_value": value,
                    "confidence": 0.72,
                    "source_text_snippet": snippet,
                }
            )
            break
    return fields


def _summarize_clause_text(text: str, field_name: str) -> str:
    cleaned = " ".join(text.split())
    if field_name in _MONEY_FIELDS:
        amount_match = re.search(r"\$?\s*[\d,.]+(?:\.\d{2})?", cleaned)
        if amount_match:
            return amount_match.group(0).strip()
    if field_name == "duracion_meses":
        months_match = re.search(r"(\d+)\s+meses", cleaned, re.IGNORECASE)
        if months_match:
            return months_match.group(1)
    sentence_match = re.search(r"^(.{20,180}?)(?:\.|$)", cleaned)
    if sentence_match:
        return sentence_match.group(1).strip()
    return cleaned[:180].strip()


def supplement_fields_from_clauses(
    fields: list[dict[str, Any]],
    clauses: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Fill missing RF-14 fields using classified clause text when regex misses them."""
    existing = {item["field_name"] for item in fields}
    supplemented = list(fields)

    for clause in clauses:
        category = clause.get("category")
        field_name = CLAUSE_CATEGORY_FIELD_MAP.get(category or "")
        if not field_name or field_name in existing:
            continue
        clause_text = str(clause.get("text", "")).strip()
        if len(clause_text) < 20:
            continue
        value = _summarize_clause_text(clause_text, field_name)
        if field_name == "jurisdiccion":
            value = normalize_jurisdiction_value(clause_text)
        if not value:
            continue
        supplemented.append(
            {
                "field_name": field_name,
                "field_value": value,
                "confidence": 0.68,
                "source_text_snippet": clause_text[:300],
                "source_section": clause.get("section"),
                "source_clause": clause.get("section"),
                "_from_clause": True,
            }
        )
        existing.add(field_name)

    return supplemented
