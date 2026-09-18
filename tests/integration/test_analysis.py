"""Analysis pipeline tests (RF-52, RF-13, RF-10, RF-18, RF-37, RF-27–RF-40)."""

import io
import os
import sys
import uuid
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from auth.models import UserCredentials
from auth.service import AuthService
from config.settings import get_settings
from data.database import get_connection
from data.repositories.contract_repository import ContractRepository
from llm.heuristic_provider import HeuristicLLMProvider
from services.analysis_service import AnalysisPipelineError, AnalysisService
from services.contract_service import ContractService


def _lease_text() -> str:
    return """
CONTRATO DE ARRENDAMIENTO

ARRENDADOR: Inmobiliaria Jalisco S.A. de C.V.
ARRENDATARIO: Juan Perez Lopez

INMUEBLE: Calle Reforma 123, Guadalajara, Jalisco.

CLÁUSULA PRIMERA. OBJETO. El arrendador otorga el uso del inmueble para oficinas.

CLÁUSULA SEGUNDA. RENTA. La renta mensual sera de $45,000.00 MXN pagadera por mes vencido.

CLÁUSULA TERCERA. DEPOSITO. El arrendatario entregara un deposito en garantia de $95,000.00 MXN.

CLÁUSULA CUARTA. VIGencia. El contrato tendra vigencia de 12 meses.

CLÁUSULA QUINTA. JURISDICCIÓN. Para la interpretacion del presente contrato las partes se someten
a la jurisdiccion de los tribunales del Estado de Jalisco.

Fecha de inicio: 01/01/2026
Fecha de termino: 31/12/2026
"""


def _lease_docx() -> bytes:
    text = _lease_text()
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(
            "word/document.xml",
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            "<w:body>"
            f"<w:p><w:r><w:t>{text}</w:t></w:r></w:p>"
            "</w:body></w:document>",
        )
    return buffer.getvalue()


def _client_user():
    login = AuthService().login(
        UserCredentials(email="code.zemoreno@gmail.com", password="cliente123")
    )
    assert login.success
    return {
        "user_id": login.user.id,
        "email": login.user.email,
        "role": login.user.role,
    }


def test_heuristic_analyzer_extracts_fields_and_clauses():
    provider = HeuristicLLMProvider()
    result = provider.analyze_contract(
        contract_text=_lease_text(),
        perspective="tenant",
        title="Lease test",
    )
    field_names = {item["field_name"] for item in result.extracted_fields}
    assert "arrendador" in field_names or "renta_mensual" in field_names
    assert len(result.clauses) >= 1
    assert result.summary_executive
    assert result.general_risk in {"low", "medium", "high"}
    assert len(result.findings) >= 1
    assert all(item["severity"] in {"low", "medium", "high"} for item in result.findings)


def test_heuristic_analyzer_prioritizes_high_severity_findings():
    provider = HeuristicLLMProvider()
    result = provider.analyze_contract(
        contract_text=_lease_text(),
        perspective="tenant",
        title="Lease test",
    )
    deposit_findings = [
        item for item in result.findings if item.get("finding_type") == "unfavorable_clause"
    ]
    assert deposit_findings
    assert deposit_findings[0]["severity"] == "high"
    assert result.findings[0]["severity"] == "high"


def test_analysis_pipeline_persists_results():
    current_user = _client_user()
    contract_service = ContractService()
    analysis_service = AnalysisService()

    contract = contract_service.create_contract_with_document(
        current_user=current_user,
        perspective="tenant",
        validated_document=contract_service.validate_upload(
            "Contrato_Arrendamiento.docx",
            _lease_docx(),
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ),
        title=f"Analysis Test {uuid.uuid4().hex[:8]}",
    )

    analysis = analysis_service.start_analysis(current_user, contract.id, "tenant")
    assert analysis.status == "ai_generated"
    assert analysis.perspective == "tenant"
    assert analysis.summary_executive
    assert analysis.general_risk in {"low", "medium", "high"}
    assert len(analysis.extracted_fields) >= 1
    assert len(analysis.clauses) >= 1
    assert len(analysis.findings) >= 1
    assert analysis.findings[0].severity in {"low", "medium", "high"}
    assert analysis.findings[0].recommendation

    settings = get_settings()
    if settings.llm_provider in ("openai", "anthropic"):
        assert analysis.llm_metadata is not None
        assert analysis.llm_metadata.get("provider") == settings.llm_provider

    refreshed = ContractRepository(get_settings()).get_by_id(contract.id)
    assert refreshed.jurisdiction is not None

    listed = analysis_service.list_analyses(current_user, contract.id)
    assert any(item.id == analysis.id for item in listed)

    settings = get_settings()
    with get_connection(settings) as connection:
        cursor = connection.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM app.extracted_fields WHERE analysis_id = ?",
            analysis.id,
        )
        assert cursor.fetchone()[0] >= 1
        cursor.execute(
            "SELECT COUNT(*) FROM app.clauses WHERE analysis_id = ?",
            analysis.id,
        )
        assert cursor.fetchone()[0] >= 1
        cursor.execute(
            "SELECT COUNT(*) FROM app.findings WHERE analysis_id = ?",
            analysis.id,
        )
        assert cursor.fetchone()[0] >= 1
        cursor.execute(
            """
            SELECT party_type, name
            FROM app.contract_parties
            WHERE contract_id = ?
            ORDER BY party_type
            """,
            contract.id,
        )
        party_rows = cursor.fetchall()
        assert len(party_rows) >= 2
        party_types = {row[0] for row in party_rows}
        assert "landlord" in party_types
        assert "tenant" in party_types
        cursor.execute(
            """
            SELECT severity FROM app.findings
            WHERE analysis_id = ?
            ORDER BY sort_order
            """,
            analysis.id,
        )
        severities = [row[0] for row in cursor.fetchall()]
        assert severities[0] == "high" or settings.llm_provider in ("openai", "anthropic")


def test_analysis_rejects_duplicate_perspective():
    current_user = _client_user()
    contract_service = ContractService()
    analysis_service = AnalysisService()

    contract = contract_service.create_contract_with_document(
        current_user=current_user,
        perspective="tenant",
        validated_document=contract_service.validate_upload(
            "Contrato_Duplicado.docx",
            _lease_docx(),
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ),
        title=f"Duplicate Perspective Test {uuid.uuid4().hex[:8]}",
    )

    first = analysis_service.start_analysis(current_user, contract.id, "tenant")
    assert first.perspective == "tenant"

    try:
        analysis_service.start_analysis(current_user, contract.id, "tenant")
        raise AssertionError("Expected duplicate perspective analysis to fail")
    except AnalysisPipelineError as exc:
        assert "already exists" in str(exc).lower()


def test_edited_contract_analysis_separate_from_original():
    current_user = _client_user()
    contract_service = ContractService()
    analysis_service = AnalysisService()

    contract = contract_service.create_contract_with_document(
        current_user=current_user,
        perspective="tenant",
        validated_document=contract_service.validate_upload(
            "Contrato_Original.docx",
            _lease_docx(),
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ),
        title=f"Edited Scope Test {uuid.uuid4().hex[:8]}",
    )

    original = analysis_service.start_analysis(current_user, contract.id, "tenant")
    assert original.document_scope == "original"

    contract_service.update_contract(current_user, contract.id, status="in_review")
    from auth.service import AuthService
    from auth.models import UserCredentials

    login = AuthService().login(UserCredentials(email="abogado@contractes.com", password="abogado123"))
    assert login.success
    lawyer_user = {
        "user_id": login.user.id,
        "email": login.user.email,
        "role": login.user.role,
    }

    contract_service.upload_lawyer_revision(
        lawyer_user,
        contract.id,
        contract_service.validate_upload(
            "Contrato_Editado.docx",
            _lease_docx(),
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ),
    )

    edited = analysis_service.start_analysis(
        current_user,
        contract.id,
        "tenant",
        document_scope="lawyer_revision",
    )
    assert edited.document_scope == "lawyer_revision"
    assert edited.id != original.id


def test_analysis_rejects_non_tenant_perspective():
    current_user = _client_user()
    contract_service = ContractService()
    analysis_service = AnalysisService()

    contract = contract_service.create_contract_with_document(
        current_user=current_user,
        perspective="tenant",
        validated_document=contract_service.validate_upload(
            "Contrato_Solo_Arrendatario.docx",
            _lease_docx(),
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ),
        title=f"Tenant Only Test {uuid.uuid4().hex[:8]}",
    )

    tenant_analysis = analysis_service.start_analysis(current_user, contract.id, "tenant")
    assert tenant_analysis.perspective == "tenant"

    for invalid_perspective in ("landlord", "neutral"):
        try:
            analysis_service.start_analysis(current_user, contract.id, invalid_perspective)
            raise AssertionError(f"Expected {invalid_perspective} perspective analysis to be rejected")
        except AnalysisPipelineError as exc:
            assert "invalid perspective" in str(exc).lower()


def main() -> int:
    print("=" * 60)
    print("Legal Rent AI - Analysis Pipeline Tests")
    print("=" * 60)
    print()
    try:
        test_heuristic_analyzer_extracts_fields_and_clauses()
        print("Heuristic analyzer: PASSED")

        test_heuristic_analyzer_prioritizes_high_severity_findings()
        print("Heuristic findings prioritization: PASSED")

        test_analysis_pipeline_persists_results()
        print("Analysis pipeline persistence: PASSED")

        test_analysis_rejects_duplicate_perspective()
        print("Duplicate perspective guard: PASSED")

        test_edited_contract_analysis_separate_from_original()
        print("Edited contract analysis scope: PASSED")

        test_analysis_rejects_non_tenant_perspective()
        print("Tenant-only perspective guard: PASSED")

        print()
        print("=" * 60)
        print("ALL TESTS PASSED")
        print("=" * 60)
        return 0
    except Exception as exc:
        print(f"\nTest failed: {exc}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
