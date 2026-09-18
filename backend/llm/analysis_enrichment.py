"""Post-processing enrichment for analysis pipeline (RF-11, RF-15, RF-21–26)."""

from __future__ import annotations

import re
from datetime import datetime
from difflib import SequenceMatcher
from typing import Any

from llm.lease_catalog import essential_categories
from llm.page_tracking import resolve_page_from_snippet
from llm.field_extraction import normalize_jurisdiction_value


def score_field_confidence(field: dict[str, Any]) -> float:
    """Calibrate confidence by extraction source (RF-16)."""
    base = float(field.get("confidence", 0.72))
    if field.get("source_page"):
        base = min(base + 0.06, 0.95)
    if field.get("source_section") or field.get("source_clause"):
        base = min(base + 0.04, 0.95)
    snippet = field.get("source_text_snippet") or ""
    if len(snippet) >= 40:
        base = min(base + 0.03, 0.95)
    if field.get("_from_clause"):
        base = max(base - 0.04, 0.65)
    return round(base, 4)


def enrich_extracted_fields(fields: list[dict[str, Any]], contract_text: str) -> list[dict[str, Any]]:
    """Add source metadata and confidence adjustments (RF-15, RF-16)."""
    enriched: list[dict[str, Any]] = []
    for item in fields:
        copy = dict(item)
        snippet = copy.get("source_text_snippet") or ""
        if snippet and not copy.get("source_section"):
            section_match = re.search(
                r"(CL[ÁA]USULA\s+[IVXLCDM\d]+[^\n]{0,40})",
                snippet,
                re.IGNORECASE,
            )
            if section_match:
                copy["source_section"] = section_match.group(1).strip()
        if not copy.get("source_page") and contract_text:
            page = resolve_page_from_snippet(contract_text, snippet)
            if page is not None:
                copy["source_page"] = page
        if "confidence" not in copy:
            copy["confidence"] = 0.72
        copy["confidence"] = score_field_confidence(copy)
        if copy.get("field_name") == "jurisdiccion":
            copy["field_value"] = normalize_jurisdiction_value(str(copy.get("field_value", "")))
        enriched.append(copy)
    return enriched


def is_jurisdiction_finding(finding: dict[str, Any]) -> bool:
    """Return True when a finding relates to jurisdiction detection (RF-11)."""
    title = (finding.get("title") or "").lower()
    description = (finding.get("description") or "").lower()
    keywords = ("jurisdiction", "jurisdicción", "foro", "competencia")
    return any(keyword in title or keyword in description for keyword in keywords)


def resolve_jurisdiction_value(
    fields: list[dict[str, Any]],
    findings: list[dict[str, Any]],
) -> str | None:
    """Decide whether a jurisdiction value should be persisted on the contract (RF-10/RF-11)."""
    jurisdiction_findings = [item for item in findings if is_jurisdiction_finding(item)]
    blocking = [
        item
        for item in jurisdiction_findings
        if item.get("severity") == "high"
        or "inconsistent" in (item.get("title") or "").lower()
        or "conflicting" in (item.get("title") or "").lower()
        or "not clearly" in (item.get("title") or "").lower()
    ]
    if blocking:
        return None

    values = {item["field_name"]: item["field_value"] for item in fields}
    extracted = normalize_jurisdiction_value((values.get("jurisdiccion") or "").strip())
    return extracted or None


def detect_jurisdiction_issues(
    fields: list[dict[str, Any]],
    clauses: list[dict[str, Any]],
    *,
    contract_text: str | None = None,
) -> list[dict[str, Any]]:
    """Detect missing or inconsistent jurisdiction (RF-11)."""
    findings: list[dict[str, Any]] = []
    values = {item["field_name"]: item["field_value"] for item in fields}
    extracted_raw = values.get("jurisdiccion")
    extracted = (extracted_raw or "").strip().lower()

    jurisdiction_clauses = [c for c in clauses if c["category"] == "jurisdiction"]
    clause_text = " ".join(c["text"].lower() for c in jurisdiction_clauses)

    if not extracted and not jurisdiction_clauses:
        findings.append(
            {
                "finding_type": "missing_clause",
                "severity": "high",
                "confidence": 0.86,
                "title": "Jurisdiction not clearly defined",
                "description": (
                    "The contract does not declare a jurisdiction in structured fields "
                    "or in a dedicated jurisdiction clause."
                ),
                "legal_basis": "Lease disputes require a defined competent court or jurisdiction.",
                "source_law": "Código Civil — competencia",
                "recommendation": "Add an explicit jurisdiction and venue clause.",
                "evidence_text": None,
                "clause_index": None,
            }
        )
        return findings

    if not extracted and jurisdiction_clauses:
        findings.append(
            {
                "finding_type": "inconsistency",
                "severity": "medium",
                "confidence": 0.8,
                "title": "Jurisdiction only found in clause text",
                "description": (
                    "A jurisdiction clause exists, but no jurisdiction value was extracted "
                    "into the contract header fields."
                ),
                "recommendation": "Ensure jurisdiction is declared consistently in headers and clauses.",
                "evidence_text": jurisdiction_clauses[0]["text"][:500],
                "clause_index": clauses.index(jurisdiction_clauses[0]),
            }
        )

    if extracted and not jurisdiction_clauses:
        findings.append(
            {
                "finding_type": "missing_clause",
                "severity": "medium",
                "confidence": 0.78,
                "title": "Jurisdiction declared without dedicated clause",
                "description": (
                    f"Jurisdiction '{extracted_raw}' appears in contract data, "
                    "but no dedicated jurisdiction clause was identified."
                ),
                "recommendation": "Add a jurisdiction and venue clause aligned with the declared forum.",
                "evidence_text": None,
                "clause_index": None,
            }
        )

    if extracted and clause_text:
        normalized_extracted = _normalize_place(extracted)
        places_in_clause = _extract_places(clause_text)
        if places_in_clause and normalized_extracted:
            if not any(
                _places_match(normalized_extracted, place) for place in places_in_clause
            ):
                findings.append(
                    {
                        "finding_type": "inconsistency",
                        "severity": "high",
                        "confidence": 0.82,
                        "title": "Jurisdiction field inconsistent with clause",
                        "description": (
                            f"Extracted jurisdiction '{extracted_raw}' "
                            "does not match the jurisdiction clause text."
                        ),
                        "recommendation": "Align jurisdiction declarations across the contract.",
                        "evidence_text": jurisdiction_clauses[0]["text"][:500],
                        "clause_index": clauses.index(jurisdiction_clauses[0]),
                    }
                )

    conflict = _find_conflicting_places(_collect_jurisdiction_places(clauses, contract_text))
    if conflict:
        place_a, place_b = conflict
        findings.append(
            {
                "finding_type": "inconsistency",
                "severity": "high",
                "confidence": 0.84,
                "title": "Conflicting jurisdictions across contract",
                "description": (
                    f"The contract references multiple jurisdictions or forums "
                    f"('{place_a}' vs '{place_b}')."
                ),
                "recommendation": "Reconcile jurisdiction references to a single competent forum.",
                "evidence_text": jurisdiction_clauses[0]["text"][:500] if jurisdiction_clauses else None,
                "clause_index": clauses.index(jurisdiction_clauses[0]) if jurisdiction_clauses else None,
            }
        )

    return findings


def detect_amount_inconsistencies(
    fields: list[dict[str, Any]],
    clauses: list[dict[str, Any]],
    parse_amount,
) -> list[dict[str, Any]]:
    """Compare extracted amounts with clause text (RF-23)."""
    findings: list[dict[str, Any]] = []
    values = {item["field_name"]: item["field_value"] for item in fields}
    rent = parse_amount(values.get("renta_mensual", ""))
    deposit = parse_amount(values.get("deposito", ""))

    for index, clause in enumerate(clauses):
        if clause["category"] == "rent" and rent:
            amounts = [_parse_amount_from_text(clause["text"]) for _ in [0]]
            clause_amounts = re.findall(r"\$?\s*[\d,.]+", clause["text"])
            for raw in clause_amounts:
                clause_val = parse_amount(raw)
                if clause_val and rent and abs(clause_val - rent) / rent > 0.05:
                    findings.append(
                        {
                            "finding_type": "inconsistency",
                            "severity": "medium",
                            "confidence": 0.8,
                            "title": "Rent amount mismatch",
                            "description": (
                                f"Extracted rent ({values.get('renta_mensual')}) differs from "
                                f"rent clause amount ({raw.strip()})."
                            ),
                            "recommendation": "Verify the correct monthly rent across all clauses.",
                            "evidence_text": clause["text"][:500],
                            "clause_index": index,
                        }
                    )
                    break

        if clause["category"] == "deposit" and deposit:
            clause_amounts = re.findall(r"\$?\s*[\d,.]+", clause["text"])
            for raw in clause_amounts:
                clause_val = parse_amount(raw)
                if clause_val and deposit and abs(clause_val - deposit) / max(deposit, 1) > 0.05:
                    findings.append(
                        {
                            "finding_type": "inconsistency",
                            "severity": "medium",
                            "confidence": 0.8,
                            "title": "Deposit amount mismatch",
                            "description": (
                                f"Extracted deposit ({values.get('deposito')}) differs from "
                                f"deposit clause amount ({raw.strip()})."
                            ),
                            "recommendation": "Verify the security deposit amount.",
                            "evidence_text": clause["text"][:500],
                            "clause_index": index,
                        }
                    )
                    break

    garantia = parse_amount(values.get("garantia", ""))
    if rent and garantia and garantia > rent * 3:
        findings.append(
            {
                "finding_type": "inconsistency",
                "severity": "medium",
                "confidence": 0.79,
                "title": "Guarantee amount unusually high vs rent",
                "description": (
                    f"Guarantee ({values.get('garantia')}) exceeds three times monthly rent "
                    f"({values.get('renta_mensual')})."
                ),
                "recommendation": "Verify guarantee amount and refund conditions.",
                "evidence_text": values.get("garantia"),
                "clause_index": None,
            }
        )

    penalty = parse_amount(values.get("penalizacion", ""))
    if rent and penalty and penalty > rent * 6:
        findings.append(
            {
                "finding_type": "inconsistency",
                "severity": "high",
                "confidence": 0.82,
                "title": "Penalty amount disproportionate to rent",
                "description": (
                    f"Penalty ({values.get('penalizacion')}) appears disproportionate to monthly rent."
                ),
                "recommendation": "Review penalty clause for reasonableness.",
                "evidence_text": values.get("penalizacion"),
                "clause_index": None,
            }
        )

    return findings


def detect_date_inconsistencies(
    fields: list[dict[str, Any]],
    parse_date,
) -> list[dict[str, Any]]:
    """Validate dates vs duration (RF-24)."""
    findings: list[dict[str, Any]] = []
    values = {item["field_name"]: item["field_value"] for item in fields}
    start = parse_date(values.get("fecha_inicio", ""))
    end = parse_date(values.get("fecha_fin", ""))
    duration_raw = values.get("duracion_meses", "")
    months = None
    if duration_raw:
        try:
            months = int(re.sub(r"[^\d]", "", duration_raw))
        except ValueError:
            months = None

    if start and end and months:
        delta_months = (end.year - start.year) * 12 + (end.month - start.month)
        if abs(delta_months - months) > 1:
            findings.append(
                {
                    "finding_type": "inconsistency",
                    "severity": "medium",
                    "confidence": 0.83,
                    "title": "Duration inconsistent with start/end dates",
                    "description": (
                        f"Stated duration ({months} months) does not match the interval between "
                        f"{values.get('fecha_inicio')} and {values.get('fecha_fin')} (~{delta_months} months)."
                    ),
                    "recommendation": "Align contract dates and stated duration.",
                    "evidence_text": f"{values.get('fecha_inicio')} — {values.get('fecha_fin')}",
                    "clause_index": None,
                }
            )
    if start and end and end < start:
        findings.append(
            {
                "finding_type": "inconsistency",
                "severity": "high",
                "confidence": 0.88,
                "title": "End date precedes start date",
                "description": (
                    f"End date ({values.get('fecha_fin')}) is before start date ({values.get('fecha_inicio')})."
                ),
                "recommendation": "Correct contract start and end dates.",
                "evidence_text": f"{values.get('fecha_inicio')} — {values.get('fecha_fin')}",
                "clause_index": None,
            }
        )
    return findings


def detect_contradictions(clauses: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Detect contradictory clauses (RF-22)."""
    findings: list[dict[str, Any]] = []
    sublease_texts = [c for c in clauses if c["category"] == "sublease" or "subarrend" in c["text"].lower()]
    if len(sublease_texts) >= 2:
        allows = any("permite" in c["text"].lower() or "podra" in c["text"].lower() for c in sublease_texts)
        forbids = any(
            "prohib" in c["text"].lower() or "no podra" in c["text"].lower() for c in sublease_texts
        )
        if allows and forbids:
            findings.append(
                {
                    "finding_type": "contradiction",
                    "severity": "high",
                    "confidence": 0.84,
                    "title": "Contradictory sublease provisions",
                    "description": "The contract contains both permissive and prohibitive sublease language.",
                    "recommendation": "Clarify whether subleasing is permitted and under what conditions.",
                    "evidence_text": sublease_texts[0]["text"][:500],
                    "clause_index": clauses.index(sublease_texts[0]),
                }
            )

    deposit_clauses = [c for c in clauses if c["category"] == "deposit"]
    if deposit_clauses:
        text = deposit_clauses[0]["text"].lower()
        if "reembols" in text and "no reembols" in text:
            findings.append(
                {
                    "finding_type": "contradiction",
                    "severity": "high",
                    "confidence": 0.8,
                    "title": "Contradictory deposit refund terms",
                    "description": "Deposit clause contains conflicting refund language.",
                    "recommendation": "Define clear deposit refund conditions.",
                    "evidence_text": deposit_clauses[0]["text"][:500],
                    "clause_index": clauses.index(deposit_clauses[0]),
                }
            )

    object_text = " ".join(c["text"].lower() for c in clauses if c["category"] == "object")
    rent_text = " ".join(c["text"].lower() for c in clauses if c["category"] == "rent")
    if object_text and rent_text:
        habitacional = "habitacional" in object_text or "vivienda" in object_text
        comercial = "comercial" in object_text or "oficina" in object_text or "local" in object_text
        if habitacional and "comercial" in rent_text:
            findings.append(
                {
                    "finding_type": "contradiction",
                    "severity": "medium",
                    "confidence": 0.8,
                    "title": "Object vs rent use mismatch",
                    "description": "Object clause suggests residential use but rent clause references commercial use.",
                    "recommendation": "Align permitted property use across clauses.",
                    "evidence_text": object_text[:500],
                    "clause_index": next(
                        (index for index, clause in enumerate(clauses) if clause["category"] == "object"),
                        None,
                    ),
                }
            )
        if comercial and "habitacional" in rent_text:
            findings.append(
                {
                    "finding_type": "contradiction",
                    "severity": "medium",
                    "confidence": 0.8,
                    "title": "Object vs rent use mismatch",
                    "description": "Object clause suggests commercial use but rent clause references residential use.",
                    "recommendation": "Align permitted property use across clauses.",
                    "evidence_text": object_text[:500],
                    "clause_index": next(
                        (index for index, clause in enumerate(clauses) if clause["category"] == "object"),
                        None,
                    ),
                }
            )

    maintenance_text = " ".join(c["text"].lower() for c in clauses if c["category"] == "maintenance")
    services_text = " ".join(c["text"].lower() for c in clauses if c["category"] == "services")
    if maintenance_text and services_text:
        if ("arrendador" in maintenance_text and "arrendador" in services_text) or (
            "arrendatario" in maintenance_text and "arrendatario" in services_text
        ):
            if maintenance_text.count("arrendador") != services_text.count("arrendador"):
                findings.append(
                    {
                        "finding_type": "contradiction",
                        "severity": "low",
                        "confidence": 0.74,
                        "title": "Overlapping maintenance and services obligations",
                        "description": "Maintenance and services clauses may assign overlapping obligations.",
                        "recommendation": "Clarify which party pays for maintenance vs utilities/services.",
                        "evidence_text": maintenance_text[:500],
                        "clause_index": next(
                            (
                                index
                                for index, clause in enumerate(clauses)
                                if clause["category"] == "maintenance"
                            ),
                            None,
                        ),
                    }
                )

    return findings


def detect_missing_clauses(
    clauses: list[dict[str, Any]],
    lease_type: str = "residential",
) -> list[dict[str, Any]]:
    """Missing essential clauses by lease type (RF-21)."""
    categories = {clause["category"] for clause in clauses}
    expected = essential_categories(lease_type)
    findings: list[dict[str, Any]] = []
    for category in sorted(expected - categories):
        findings.append(
            {
                "finding_type": "missing_clause",
                "severity": "high" if category == "jurisdiction" else "medium",
                "confidence": 0.76,
                "title": f"Potentially missing {category} clause",
                "description": f"No clause categorized as '{category}' was identified.",
                "recommendation": f"Verify whether a {category} clause exists or should be added.",
                "evidence_text": None,
                "clause_index": None,
            }
        )
    return findings


def consolidate_obligations(
    clauses: list[dict[str, Any]],
    perspective: str,
) -> list[dict[str, Any]]:
    """Summarize key obligations (RF-25)."""
    obligation_categories = {"maintenance", "services", "termination", "guarantees", "insurance", "rent", "deposit"}
    landlord_items: list[str] = []
    tenant_items: list[str] = []
    indices: dict[str, int] = {}

    obligation_pattern = re.compile(
        r"(?:deber[aá]|obligaci[oó]n|se compromete)[^.;\n]{0,120}",
        re.IGNORECASE,
    )

    for index, clause in enumerate(clauses):
        if clause["category"] not in obligation_categories:
            continue
        lowered = clause["text"].lower()
        label = clause["category"].title()
        phrases = [" ".join(match.group(0).split()) for match in obligation_pattern.finditer(clause["text"])]
        phrase_summary = phrases[0][:120] if phrases else label
        if any(k in lowered for k in ("arrendador", "propietario", "landlord")):
            landlord_items.append(phrase_summary)
            indices["landlord"] = index
        elif any(k in lowered for k in ("arrendatario", "tenant", "inquilino")):
            tenant_items.append(phrase_summary)
            indices["tenant"] = index
        else:
            tenant_items.append(phrase_summary)
            indices.setdefault("tenant", index)

    findings: list[dict[str, Any]] = []
    if landlord_items:
        findings.append(
            {
                "finding_type": "obligation",
                "severity": "low",
                "confidence": 0.74,
                "title": "Landlord obligations identified",
                "description": "Key landlord obligations: " + "; ".join(sorted(set(landlord_items))) + ".",
                "recommendation": "Confirm landlord obligations are balanced for the selected perspective.",
                "evidence_text": clauses[indices["landlord"]]["text"][:500] if "landlord" in indices else None,
                "clause_index": indices.get("landlord"),
            }
        )
    if tenant_items:
        party = "tenant" if perspective == "tenant" else "tenant"
        findings.append(
            {
                "finding_type": "obligation",
                "severity": "low",
                "confidence": 0.74,
                "title": f"{party.title()} obligations identified",
                "description": f"Key {party} obligations: " + "; ".join(sorted(set(tenant_items))) + ".",
                "recommendation": "Confirm tenant obligations are balanced for the selected perspective.",
                "evidence_text": clauses[indices["tenant"]]["text"][:500] if "tenant" in indices else None,
                "clause_index": indices.get("tenant"),
            }
        )
    return findings


def dedupe_findings(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for item in findings:
        key = (item.get("title") or "", item.get("finding_type") or "")
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique


def _normalize_place(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def _extract_places(text: str) -> list[str]:
    places: list[str] = []
    for match in re.finditer(
        r"(?:estado de|ciudad de|foro (?:de|en))\s+([a-záéíóúñ\s]+)",
        text,
        re.IGNORECASE,
    ):
        places.append(_normalize_place(match.group(1)))
    return places


def _collect_jurisdiction_places(
    clauses: list[dict[str, Any]],
    contract_text: str | None = None,
) -> list[str]:
    places: list[str] = []
    jurisdiction_pattern = re.compile(r"foro|competencia|tribunal|jurisdicci", re.IGNORECASE)
    for clause in clauses:
        text = clause["text"].lower()
        if clause["category"] == "jurisdiction" or jurisdiction_pattern.search(text):
            places.extend(_extract_places(text))
    if contract_text:
        places.extend(_extract_places(contract_text.lower()))
    return places


def _find_conflicting_places(places: list[str]) -> tuple[str, str] | None:
    normalized = [_normalize_place(place) for place in places if place.strip()]
    for index, left in enumerate(normalized):
        for right in normalized[index + 1 :]:
            if not _places_match(left, right):
                return left, right
    return None


def _places_match(a: str, b: str) -> bool:
    return a in b or b in a or SequenceMatcher(None, a, b).ratio() > 0.6


def _parse_amount_from_text(text: str) -> float | None:
    match = re.search(r"\$?\s*[\d,.]+", text)
    if not match:
        return None
    digits = re.sub(r"[^\d.]", "", match.group(0).replace(",", ""))
    try:
        return float(digits) if digits else None
    except ValueError:
        return None


def parse_date_value(raw: str) -> datetime | None:
    raw = raw.strip()
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y", "%d-%m-%y"):
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
    return None
