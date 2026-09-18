"""Build structured party records from extracted contract fields (RF-12)."""

from __future__ import annotations

from typing import Any

from llm.field_specs import PARTY_FIELD_MAP

PRIMARY_PARTY_FIELDS: dict[str, str] = {
    "arrendador": "landlord",
    "arrendatario": "tenant",
    "fiador": "guarantor",
    "obligado_solidario": "joint_obligor",
}

REPRESENTATIVE_FIELD_TARGETS: dict[str, str] = {
    "representante_arrendador": "landlord",
    "representante_arrendatario": "tenant",
}

PARTY_FIELD_NAMES: frozenset[str] = frozenset(PARTY_FIELD_MAP.keys())


def build_party_records(extracted_fields: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Normalize extracted fields into contract party rows."""
    by_field = {
        str(item.get("field_name", "")): item
        for item in extracted_fields
        if item.get("field_name")
    }
    records: dict[str, dict[str, Any]] = {}

    for field_name, party_type in PRIMARY_PARTY_FIELDS.items():
        item = by_field.get(field_name)
        if not item:
            continue
        name = str(item.get("field_value", "")).strip()
        if not name:
            continue
        records[party_type] = {
            "party_type": party_type,
            "name": name,
            "legal_representative": None,
            "confidence": float(item.get("confidence", 0.7)),
            "source_page": item.get("source_page"),
        }

    for field_name, target_type in REPRESENTATIVE_FIELD_TARGETS.items():
        item = by_field.get(field_name)
        if not item:
            continue
        representative = str(item.get("field_value", "")).strip()
        if not representative:
            continue
        if target_type in records:
            records[target_type]["legal_representative"] = representative
            rep_confidence = float(item.get("confidence", records[target_type]["confidence"]))
            records[target_type]["confidence"] = min(records[target_type]["confidence"], rep_confidence)

    return list(records.values())


def detect_missing_parties(extracted_fields: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Emit findings when core parties cannot be identified (RF-12)."""
    by_field = {
        str(item.get("field_name", "")): str(item.get("field_value", "")).strip()
        for item in extracted_fields
    }
    findings: list[dict[str, Any]] = []
    if not by_field.get("arrendador"):
        findings.append(
            {
                "finding_type": "missing_clause",
                "severity": "high",
                "confidence": 0.84,
                "title": "Landlord not identified",
                "description": "The contract does not clearly identify the landlord (arrendador).",
                "recommendation": "Confirm the landlord name appears in the contract header or declarations.",
                "evidence_text": None,
                "clause_index": None,
            }
        )
    if not by_field.get("arrendatario"):
        findings.append(
            {
                "finding_type": "missing_clause",
                "severity": "high",
                "confidence": 0.84,
                "title": "Tenant not identified",
                "description": "The contract does not clearly identify the tenant (arrendatario).",
                "recommendation": "Confirm the tenant name appears in the contract header or declarations.",
                "evidence_text": None,
                "clause_index": None,
            }
        )
    return findings
