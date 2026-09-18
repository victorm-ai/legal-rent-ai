"""Tests for non-RAG requirement implementations."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from llm.analysis_enrichment import (
    detect_jurisdiction_issues,
    detect_missing_clauses,
    is_jurisdiction_finding,
    parse_date_value,
    resolve_jurisdiction_value,
)
from llm.party_extraction import build_party_records, detect_missing_parties
from llm.contract_rules import apply_contract_rules
from llm.field_specs import FIELD_SPECS, PARTY_FIELD_MAP, RF14_FIELD_NAMES
from llm.field_extraction import extract_fields_from_text, supplement_fields_from_clauses
from llm.heuristic_provider import HeuristicLLMProvider
from llm.clause_taxonomy import RF20_RELEVANT_CATEGORIES, RF20_CATEGORY_LABELS_ES
from llm.lease_catalog import essential_categories
from llm.prompts import CONTRACT_ANALYSIS_PROMPT_ID


def test_expanded_field_specs():
    assert "fiador" in FIELD_SPECS
    assert "forma_pago" in FIELD_SPECS
    assert "impuestos" in FIELD_SPECS
    assert "incremento_renta" in FIELD_SPECS
    assert "mantenimiento" in FIELD_SPECS
    assert len(RF14_FIELD_NAMES) >= 20
    assert PARTY_FIELD_MAP["arrendador"] == "landlord"


def _full_lease_text() -> str:
    return """
CONTRATO DE ARRENDAMIENTO

ARRENDADOR: Inmobiliaria Jalisco S.A. de C.V.
Representante legal del arrendador: Lic. Ana Ruiz
ARRENDATARIO: Maria Lopez
Representante legal del arrendatario: Ing. Carlos Meza
FIADOR: Pedro Garcia
OBLIGADO SOLIDARIO: Empresa Aval S.A.

INMUEBLE: Calle Reforma 123, Guadalajara, Jalisco.
USO DEL INMUEBLE: oficinas administrativas

Renta mensual: $10,000.00 MXN
Deposito en garantia: $20,000.00 MXN
Garantia adicional: $5,000.00 MXN
Forma de pago: transferencia bancaria
Impuestos a cargo del arrendatario
Incremento anual del 4% conforme al INPC
Pena convencional de 2 meses de renta

Fecha de inicio: 01/01/2026
Fecha de termino: 31/12/2026

CLÁUSULA PRIMERA. OBJETO. Uso habitacional del inmueble.
CLÁUSULA SEGUNDA. RENTA. $10,000 mensual.
CLÁUSULA TERCERA. DEPOSITO. $20,000.
CLÁUSULA CUARTA. VIGENCIA. Plazo de 12 meses.
CLÁUSULA QUINTA. MANTENIMIENTO. Obligacion a cargo del arrendatario.
CLÁUSULA SEXTA. SERVICIOS. Servicios de agua, luz e internet a cargo del arrendatario.
CLÁUSULA SEPTIMA. RENOVACION. Renovacion automatica por periodos iguales.
CLÁUSULA OCTAVA. TERMINACION. Terminacion anticipada con aviso de 30 dias.
CLÁUSULA NOVENA. JURISDICCIÓN. Estado de Jalisco.
"""


def test_rf14_extracts_catalog_fields():
    fields = extract_fields_from_text(_full_lease_text())
    names = {item["field_name"] for item in fields}
    expected = {
        "arrendador",
        "arrendatario",
        "fiador",
        "obligado_solidario",
        "representante_arrendador",
        "representante_arrendatario",
        "inmueble_direccion",
        "renta_mensual",
        "deposito",
        "forma_pago",
        "impuestos",
        "incremento_renta",
        "penalizacion",
        "fecha_inicio",
        "fecha_fin",
        "jurisdiccion",
    }
    assert expected.issubset(names)


def test_rf14_supplements_from_clauses():
    provider = HeuristicLLMProvider()
    result = provider.analyze_contract(_full_lease_text(), "tenant", "RF-14 test")
    names = {item["field_name"] for item in result.extracted_fields}
    assert "mantenimiento" in names
    assert "servicios" in names
    assert "renovacion" in names
    assert "terminacion" in names
    assert "duracion_meses" in names or "fecha_inicio" in names


def test_rf20_relevant_categories_complete():
    expected = {
        "object",
        "rent",
        "deposit",
        "term",
        "maintenance",
        "services",
        "sublease",
        "guarantees",
        "insurance",
        "renewal",
        "termination",
        "penalties",
        "liability",
        "jurisdiction",
    }
    assert expected == set(RF20_RELEVANT_CATEGORIES)
    assert len(RF20_CATEGORY_LABELS_ES) == len(RF20_RELEVANT_CATEGORIES)


def test_rf20_detects_categories_from_native_text():
    provider = HeuristicLLMProvider()
    result = provider.analyze_contract(_full_lease_text(), "tenant", "RF-20 test")
    detected = {clause["category"] for clause in result.clauses}
    assert {"rent", "maintenance", "services", "jurisdiction"}.issubset(detected)


def test_ocr_stub_returns_empty():
    from document.ocr import extract_text_from_scanned_pdf, is_ocr_available

    assert is_ocr_available() is False
    text, pages = extract_text_from_scanned_pdf(b"%PDF-1.4", max_pages=5)
    assert text == ""
    assert pages is None


def test_lease_catalog_residential():
    cats = essential_categories("residential")
    assert "rent" in cats
    assert "jurisdiction" in cats


def test_heuristic_extracts_additional_fields():
    text = """
    ARRENDADOR: Inmobiliaria Test S.A.
    ARRENDATARIO: Maria Lopez
    FIADOR: Pedro Garcia
    Renta mensual: $10,000.00 MXN
    Deposito en garantia: $20,000.00 MXN
    CLÁUSULA PRIMERA. OBJETO.
    CLÁUSULA SEGUNDA. RENTA. $10,000 mensual.
    CLÁUSULA TERCERA. DEPOSITO. $20,000.
    CLÁUSULA CUARTA. VIGencia de 12 meses.
    CLÁUSULA QUINTA. JURISDICCIÓN. Estado de Jalisco.
    """
    provider = HeuristicLLMProvider()
    result = provider.analyze_contract(text, "tenant", "Test")
    names = {item["field_name"] for item in result.extracted_fields}
    assert "fiador" in names
    assert len(result.findings) >= 1


def test_contract_rules_deposit():
    fields = [
        {"field_name": "renta_mensual", "field_value": "$10,000"},
        {"field_name": "deposito", "field_value": "$25,000"},
    ]
    findings = apply_contract_rules(fields, [], "tenant", [], HeuristicLLMProvider._parse_amount)
    assert any("deposit" in f["title"].lower() for f in findings)


def test_prompt_version():
    assert CONTRACT_ANALYSIS_PROMPT_ID == "contract-analysis-v3-cag"


def test_parse_date_value():
    assert parse_date_value("01/01/2026") is not None


def test_missing_clauses_detection():
    clauses = [{"category": "rent", "text": "rent clause"}]
    findings = detect_missing_clauses(clauses, "residential")
    assert any(f["finding_type"] == "missing_clause" for f in findings)


def test_jurisdiction_missing():
    findings = detect_jurisdiction_issues([], [])
    assert any(f["title"] == "Jurisdiction not clearly defined" for f in findings)
    assert resolve_jurisdiction_value([], findings) is None


def test_jurisdiction_inconsistent_field_vs_clause():
    fields = [{"field_name": "jurisdiccion", "field_value": "Jalisco"}]
    clauses = [
        {
            "category": "jurisdiction",
            "text": "Las partes se someten a la jurisdiccion de los tribunales del Estado de Nuevo Leon.",
        }
    ]
    findings = detect_jurisdiction_issues(fields, clauses)
    assert any("inconsistent" in f["title"].lower() for f in findings)
    assert resolve_jurisdiction_value(fields, findings) is None


def test_jurisdiction_conflicting_clauses():
    clauses = [
        {
            "category": "jurisdiction",
            "text": "Foro en los tribunales del Estado de Jalisco.",
        },
        {
            "category": "termination",
            "text": "Cualquier controversia se resolvera ante los tribunales del Estado de Nuevo Leon.",
        },
    ]
    findings = detect_jurisdiction_issues([], clauses)
    assert any("conflicting" in f["title"].lower() for f in findings)


def test_jurisdiction_only_in_clause():
    clauses = [
        {
            "category": "jurisdiction",
            "text": "Las partes se someten al foro de los tribunales del Estado de Jalisco.",
        }
    ]
    findings = detect_jurisdiction_issues([], clauses)
    assert any("only found in clause" in f["title"].lower() for f in findings)


def test_jurisdiction_field_without_clause():
    fields = [{"field_name": "jurisdiccion", "field_value": "Jalisco"}]
    findings = detect_jurisdiction_issues(fields, [])
    assert any("without dedicated clause" in f["title"].lower() for f in findings)
    assert resolve_jurisdiction_value(fields, findings) == "Jalisco"


def test_is_jurisdiction_finding_helper():
    assert is_jurisdiction_finding({"title": "Jurisdiction field inconsistent with clause"})
    assert not is_jurisdiction_finding({"title": "Deposit exceeds recommended limit"})


def test_build_party_records():
    fields = [
        {"field_name": "arrendador", "field_value": "Inmobiliaria Test S.A.", "confidence": 0.9},
        {"field_name": "arrendatario", "field_value": "Maria Lopez", "confidence": 0.88},
        {"field_name": "representante_arrendador", "field_value": "Lic. Ana Ruiz", "confidence": 0.8},
    ]
    parties = build_party_records(fields)
    types = {item["party_type"] for item in parties}
    assert types == {"landlord", "tenant"}
    landlord = next(item for item in parties if item["party_type"] == "landlord")
    assert landlord["legal_representative"] == "Lic. Ana Ruiz"


def test_detect_missing_parties():
    findings = detect_missing_parties([{"field_name": "arrendador", "field_value": "Only landlord"}])
    assert len(findings) == 1
    assert findings[0]["title"] == "Tenant not identified"


def test_download_token_scoped():
    from auth.download_token import DownloadTokenService

    service = DownloadTokenService(secret_key="test-secret", ttl_seconds=60)
    token, _expires = service.create(
        user_id="user-1",
        contract_id="contract-1",
        document_id="doc-1",
    )
    assert service.verify(token, contract_id="contract-1", document_id="doc-1") == "user-1"
    assert service.verify(token, contract_id="contract-1", document_id="doc-2") is None
    assert service.verify(token, contract_id="contract-2", document_id="doc-1") is None
