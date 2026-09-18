"""Lawyer review workflow tests (RF-58, RF-68, RF-69)."""

import io
import os
import sys
import uuid
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from auth.models import UserCredentials
from auth.service import AuthService
from domain.analysis_status import assert_transition as assert_analysis_transition, InvalidAnalysisStatusTransitionError
from domain.entities import Role
from services.analysis_service import AnalysisReviewError, AnalysisService
from services.contract_service import ContractAccessError, ContractService


def _lease_text() -> str:
    return """
CONTRATO DE ARRENDAMIENTO
ARRENDADOR: Inmobiliaria Jalisco S.A. de C.V.
ARRENDATARIO: Juan Perez Lopez
RENTA: $45,000.00 MXN mensuales.
DEPOSITO: $95,000.00 MXN.
JURISDICCIÓN: Jalisco.
"""


def _lease_docx() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(
            "word/document.xml",
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            f"<w:body><w:p><w:r><w:t>{_lease_text()}</w:t></w:r></w:p></w:body>"
            "</w:document>",
        )
    return buffer.getvalue()


def _login(email: str, password: str) -> dict:
    login = AuthService().login(UserCredentials(email=email, password=password))
    assert login.success
    return {
        "user_id": login.user.id,
        "email": login.user.email,
        "role": login.user.role,
    }


def _create_analyzed_contract(client_user: dict) -> tuple:
    contract_service = ContractService()
    analysis_service = AnalysisService()

    contract = contract_service.create_contract_with_document(
        current_user=client_user,
        perspective="tenant",
        validated_document=contract_service.validate_upload(
            "Review_Flow.docx",
            _lease_docx(),
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ),
        title=f"Lawyer Review Test {uuid.uuid4().hex[:8]}",
    )
    analysis = analysis_service.start_analysis(client_user, contract.id, "tenant")
    assert analysis.status == "ai_generated"
    return contract, analysis


def test_lawyer_cannot_see_draft_contract():
    client = _login("code.zemoreno@gmail.com", "cliente123")
    lawyer = _login("abogado@contractes.com", "abogado123")
    contract, _analysis = _create_analyzed_contract(client)

    contract_service = ContractService()
    lawyer_contracts = contract_service.list_contracts(lawyer)
    assert all(item.id != contract.id for item in lawyer_contracts)

    try:
        contract_service.get_contract(lawyer, contract.id)
        raise AssertionError("Expected lawyer access to draft contract to be denied")
    except ContractAccessError:
        pass


def test_lawyer_cannot_start_analysis():
    client = _login("code.zemoreno@gmail.com", "cliente123")
    lawyer = _login("abogado@contractes.com", "abogado123")
    contract, _analysis = _create_analyzed_contract(client)

    contract_service = ContractService()
    contract_service.update_contract(client, contract.id, status="in_review")

    analysis_service = AnalysisService()
    try:
        analysis_service.start_analysis(lawyer, contract.id, "tenant")
        raise AssertionError("Expected lawyer analysis start to be denied")
    except ContractAccessError:
        pass


def test_contract_in_review_promotes_analyses():
    client = _login("code.zemoreno@gmail.com", "cliente123")
    contract, analysis = _create_analyzed_contract(client)

    contract_service = ContractService()
    updated = contract_service.update_contract(client, contract.id, status="in_review")
    assert updated.status == "in_review"

    refreshed = AnalysisService().get_analysis(client, analysis.id)
    assert refreshed.status == "pending_review"


def test_lawyer_reviews_findings_and_approves_analysis():
    client = _login("code.zemoreno@gmail.com", "cliente123")
    lawyer = _login("abogado@contractes.com", "abogado123")
    contract, analysis = _create_analyzed_contract(client)

    contract_service = ContractService()
    contract_service.update_contract(client, contract.id, status="in_review")

    analysis_service = AnalysisService()
    refreshed = analysis_service.get_analysis(lawyer, analysis.id)
    assert refreshed.status == "pending_review"
    assert len(refreshed.findings) >= 1

    finding_id = refreshed.findings[0].id
    review = analysis_service.review_finding(
        lawyer,
        analysis.id,
        finding_id,
        "correct",
        notes="Accurate finding",
    )
    assert review.verdict == "correct"

    updated = analysis_service.get_analysis(lawyer, analysis.id)
    assert updated.status == "reviewed"
    assert updated.finding_reviews[finding_id].verdict == "correct"

    approval = analysis_service.approve_analysis(lawyer, analysis.id, notes="Approved for signing")
    assert approval.analysis_id == analysis.id

    approved = analysis_service.get_analysis(lawyer, analysis.id)
    assert approved.status == "approved"
    assert approved.approval is not None


def test_client_cannot_review_findings():
    client = _login("code.zemoreno@gmail.com", "cliente123")
    _, analysis = _create_analyzed_contract(client)

    analysis_service = AnalysisService()
    detail = analysis_service.get_analysis(client, analysis.id)
    finding_id = detail.findings[0].id

    try:
        analysis_service.review_finding(client, analysis.id, finding_id, "correct")
        raise AssertionError("Expected client review to be denied")
    except ContractAccessError:
        pass


def test_analysis_status_transition_rules():
    assert_analysis_transition(Role.CLIENT, "ai_generated", "pending_review")
    assert_analysis_transition(Role.LAWYER, "pending_review", "reviewed")
    assert_analysis_transition(Role.LAWYER, "reviewed", "approved")

    try:
        assert_analysis_transition(Role.CLIENT, "pending_review", "reviewed")
        raise AssertionError("Expected client transition to fail")
    except InvalidAnalysisStatusTransitionError:
        pass


def test_duplicate_approval_rejected():
    client = _login("code.zemoreno@gmail.com", "cliente123")
    lawyer = _login("abogado@contractes.com", "abogado123")
    contract, analysis = _create_analyzed_contract(client)

    ContractService().update_contract(client, contract.id, status="in_review")
    analysis_service = AnalysisService()
    detail = analysis_service.get_analysis(lawyer, analysis.id)
    analysis_service.review_finding(lawyer, analysis.id, detail.findings[0].id, "correct")
    analysis_service.approve_analysis(lawyer, analysis.id)

    try:
        analysis_service.approve_analysis(lawyer, analysis.id)
        raise AssertionError("Expected duplicate approval to fail")
    except AnalysisReviewError as exc:
        assert "already been approved" in exc.message.lower()


def main() -> int:
    print("=" * 60)
    print("Legal Rent AI - Lawyer Review Workflow Tests")
    print("=" * 60)
    print()
    try:
        test_analysis_status_transition_rules()
        print("Analysis status transition rules: PASSED")

        test_lawyer_cannot_see_draft_contract()
        print("Lawyer cannot see draft contracts: PASSED")

        test_lawyer_cannot_start_analysis()
        print("Lawyer cannot start analysis: PASSED")

        test_contract_in_review_promotes_analyses()
        print("Contract in_review promotes analyses: PASSED")

        test_client_cannot_review_findings()
        print("Client cannot review findings: PASSED")

        test_lawyer_reviews_findings_and_approves_analysis()
        print("Lawyer review and approval flow: PASSED")

        test_duplicate_approval_rejected()
        print("Duplicate approval guard: PASSED")

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
