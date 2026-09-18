"""Configurable contract rules engine (RF-63)."""

from __future__ import annotations

from typing import Any


def apply_contract_rules(
    fields: list[dict[str, Any]],
    clauses: list[dict[str, Any]],
    perspective: str,
    existing_findings: list[dict[str, Any]],
    parse_amount,
) -> list[dict[str, Any]]:
    """Append rule-based findings; rules are declarative and code-configured."""
    findings = list(existing_findings)
    values = {item["field_name"]: item["field_value"] for item in fields}
    rent = parse_amount(values.get("renta_mensual", ""))
    deposit = parse_amount(values.get("deposito", ""))
    categories = {clause["category"] for clause in clauses}

    # Rule: deposit > 2 months rent (§22 example)
    if rent and deposit and deposit > rent * 2:
        if not _has_title(findings, "Security deposit exceeds two months' rent"):
            deposit_index = next(
                (index for index, clause in enumerate(clauses) if clause["category"] == "deposit"),
                None,
            )
            severity = "high" if perspective == "tenant" else "medium"
            findings.append(
                {
                    "finding_type": "unfavorable_clause" if perspective == "tenant" else "best_practice",
                    "severity": severity,
                    "confidence": 0.85,
                    "title": "Security deposit exceeds two months' rent",
                    "description": (
                        f"Deposit ({values.get('deposito')}) exceeds twice monthly rent "
                        f"({values.get('renta_mensual')})."
                    ),
                    "legal_basis": "Mexican lease practice commonly limits deposits to one or two months' rent.",
                    "source_law": "Best practice — Mexican lease market",
                    "recommendation": (
                        "Negotiate a lower deposit or document refund conditions clearly."
                        if perspective == "tenant"
                        else "Ensure deposit refund terms are explicit."
                    ),
                    "evidence_text": next(
                        (clause["text"][:500] for clause in clauses if clause["category"] == "deposit"),
                        values.get("deposito", ""),
                    ),
                    "clause_index": deposit_index,
                }
            )

    # Rule: tenant perspective — short payment grace
    if perspective == "tenant":
        for index, clause in enumerate(clauses):
            lowered = clause["text"].lower()
            if "pago" in lowered and any(k in lowered for k in ("inmediato", "mismo dia", "sin tolerancia")):
                if not _has_title(findings, "Strict rent payment terms"):
                    findings.append(
                        {
                            "finding_type": "unfavorable_clause",
                            "severity": "medium",
                            "confidence": 0.78,
                            "title": "Strict rent payment terms",
                            "description": "Payment terms appear strict with little or no grace period.",
                            "recommendation": "Negotiate a reasonable grace period for rent payments.",
                            "evidence_text": clause["text"][:500],
                            "clause_index": index,
                        }
                    )
                break

    # Rule: landlord perspective — unilateral renewal
    if perspective == "landlord":
        for index, clause in enumerate(clauses):
            if clause["category"] != "renewal":
                continue
            lowered = clause["text"].lower()
            if "arrendatario" in lowered and "renov" in lowered and "arrendador" not in lowered:
                if not _has_title(findings, "Tenant-driven renewal clause"):
                    findings.append(
                        {
                            "finding_type": "unfavorable_clause",
                            "severity": "medium",
                            "confidence": 0.75,
                            "title": "Tenant-driven renewal clause",
                            "description": "Renewal appears driven by tenant request without landlord control.",
                            "recommendation": "Clarify landlord consent requirements for renewal.",
                            "evidence_text": clause["text"][:500],
                            "clause_index": index,
                        }
                    )
                break

    # Rule: missing insurance for commercial leases with guarantees category absent
    if "guarantees" not in categories and "insurance" not in categories:
        if any(k in " ".join(c["text"].lower() for c in clauses) for k in ("comercial", "local", "oficina")):
            if not _has_title(findings, "No insurance clause identified"):
                findings.append(
                    {
                        "finding_type": "missing_clause",
                        "severity": "medium",
                        "confidence": 0.7,
                        "title": "No insurance clause identified",
                        "description": "Commercial leases often require insurance provisions.",
                        "recommendation": "Verify whether insurance obligations should be documented.",
                        "evidence_text": None,
                        "clause_index": None,
                    }
                )

    # Rule: neutral perspective — asymmetric penalty exposure
    if perspective == "neutral":
        penalty_clauses = [index for index, clause in enumerate(clauses) if clause["category"] == "penalties"]
        if len(penalty_clauses) >= 2 and not _has_title(findings, "Multiple penalty clauses"):
            findings.append(
                {
                    "finding_type": "unfavorable_clause",
                    "severity": "medium",
                    "confidence": 0.77,
                    "title": "Multiple penalty clauses",
                    "description": "The contract defines more than one penalty mechanism.",
                    "recommendation": "Consolidate penalty terms to avoid cumulative sanctions.",
                    "evidence_text": clauses[penalty_clauses[0]]["text"][:500],
                    "clause_index": penalty_clauses[0],
                }
            )
        for index, clause in enumerate(clauses):
            lowered = clause["text"].lower()
            if "unilateral" in lowered and any(k in lowered for k in ("rescind", "termin", "rescision")):
                if not _has_title(findings, "Unilateral termination risk"):
                    findings.append(
                        {
                            "finding_type": "unfavorable_clause",
                            "severity": "high",
                            "confidence": 0.81,
                            "title": "Unilateral termination risk",
                            "description": "A clause allows unilateral termination without balanced remedies.",
                            "recommendation": "Review termination symmetry and notice periods for both parties.",
                            "evidence_text": clause["text"][:500],
                            "clause_index": index,
                        }
                    )
                break

    return findings


def _has_title(findings: list[dict[str, Any]], title: str) -> bool:
    return any(item.get("title") == title for item in findings)
