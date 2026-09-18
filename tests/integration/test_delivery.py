"""Phase 5 delivery tests (RF-46–RF-51, RF-41)."""

import io
import os
import sys
import uuid
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from auth.models import UserCredentials
from auth.service import AuthService
from services.analysis_service import AnalysisService
from services.chat_service import ChatService
from services.contract_service import ContractService
from services.review_communication_service import ReviewCommunicationError, ReviewCommunicationService
from services.report_service import ReportService


def _lease_text() -> str:
    return """
CONTRATO DE ARRENDAMIENTO
ARRENDADOR: Inmobiliaria Jalisco S.A. de C.V.
ARRENDATARIO: Juan Perez Lopez
INMUEBLE: Calle Reforma 123, Guadalajara, Jalisco.
CLÁUSULA SEGUNDA. RENTA. La renta mensual sera de $45,000.00 MXN.
CLÁUSULA TERCERA. DEPOSITO. deposito en garantia de $95,000.00 MXN.
CLÁUSULA QUINTA. JURISDICCIÓN. tribunales del Estado de Jalisco.
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


def _lawyer_user():
    login = AuthService().login(
        UserCredentials(email="abogado@contractes.com", password="abogado123")
    )
    assert login.success
    return {
        "user_id": login.user.id,
        "email": login.user.email,
        "role": login.user.role,
    }


def test_report_json_and_pdf_generation():
    user = _client_user()
    contract = ContractService().create_contract_with_document(
        current_user=user,
        perspective="tenant",
        validated_document=ContractService().validate_upload(
            f"Delivery_{uuid.uuid4().hex[:6]}.docx",
            _lease_docx(),
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ),
        title=f"Delivery Test {uuid.uuid4().hex[:6]}",
    )
    analysis = AnalysisService().start_analysis(user, contract.id, "tenant")
    report_service = ReportService()

    json_report = report_service.generate_report(user, analysis.id, "json")
    assert json_report.format == "json"
    assert os.path.isfile(json_report.storage_path)

    pdf_report = report_service.generate_report(user, analysis.id, "pdf")
    assert pdf_report.format == "pdf"
    assert os.path.isfile(pdf_report.storage_path)

    path, media, _ = report_service.get_report_file(user, json_report.id)
    assert path.exists()
    assert media == "application/json"


def test_chat_session_and_message():
    user = _client_user()
    contract = ContractService().create_contract_with_document(
        current_user=user,
        perspective="tenant",
        validated_document=ContractService().validate_upload(
            f"Chat_{uuid.uuid4().hex[:6]}.docx",
            _lease_docx(),
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ),
        title=f"Chat Test {uuid.uuid4().hex[:6]}",
    )
    analysis = AnalysisService().start_analysis(user, contract.id, "tenant")
    chat_service = ChatService()

    session = chat_service.create_session(user, contract.id, analysis.id)
    suggestions = chat_service.get_suggestions(user, session.id)
    assert len(suggestions) >= 1

    reply = chat_service.send_message(user, session.id, "What are the main risks?")
    assert reply.role == "assistant"
    assert reply.content

    messages = chat_service.list_messages(user, session.id)
    assert len(messages) >= 2


def test_review_communication_persists_messages():
    client = _client_user()
    lawyer = _lawyer_user()
    contract_service = ContractService()
    review_service = ReviewCommunicationService()

    contract = contract_service.create_contract_with_document(
        current_user=client,
        perspective="tenant",
        validated_document=contract_service.validate_upload(
            f"ReviewMsg_{uuid.uuid4().hex[:6]}.docx",
            _lease_docx(),
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ),
        title=f"Review Msg Test {uuid.uuid4().hex[:6]}",
    )
    analysis = AnalysisService().start_analysis(client, contract.id, "tenant")

    try:
        review_service.send_message(
            client,
            analysis.id,
            "I accept the contract subject to deposit negotiation.",
        )
        raise AssertionError("Expected draft contract messaging to be rejected")
    except ReviewCommunicationError as exc:
        assert "legal review" in exc.message.lower()

    contract_service.update_contract(client, contract.id, status="in_review")

    client_message = review_service.send_message(
        client,
        analysis.id,
        "I accept the contract subject to deposit negotiation.",
    )
    assert client_message.author_role == "client"

    lawyer_message = review_service.send_message(
        lawyer,
        analysis.id,
        "Received. Please clarify the requested changes to clause 12.",
    )
    assert lawyer_message.author_role == "lawyer"

    messages = review_service.list_messages(lawyer, analysis.id)
    assert len(messages) == 2
    assert messages[0].content.startswith("I accept")
    assert messages[1].content.startswith("Received")

    unread_for_lawyer = review_service.unread_counts_by_contract(lawyer, [contract.id])
    assert unread_for_lawyer.get(contract.id) == 1

    unread_for_client = review_service.unread_counts_by_contract(client, [contract.id])
    assert unread_for_client.get(contract.id) == 1

    review_service.mark_contract_read(lawyer, contract.id)
    unread_for_lawyer = review_service.unread_counts_by_contract(lawyer, [contract.id])
    assert unread_for_lawyer.get(contract.id) == 0


def test_review_communication_without_prior_analysis():
    client = _client_user()
    lawyer = _lawyer_user()
    contract_service = ContractService()
    review_service = ReviewCommunicationService()

    contract = contract_service.create_contract_with_document(
        current_user=client,
        perspective="tenant",
        validated_document=contract_service.validate_upload(
            f"NoAnalysis_{uuid.uuid4().hex[:6]}.docx",
            _lease_docx(),
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ),
        title=f"No Analysis Chat {uuid.uuid4().hex[:6]}",
    )
    contract_service.update_contract(client, contract.id, status="in_review")

    client_message = review_service.send_message_for_contract(
        client,
        contract.id,
        "¿Puede revisar la cláusula de depósito?",
    )
    assert client_message.author_role == "client"

    messages = review_service.list_messages_for_contract(lawyer, contract.id)
    assert len(messages) == 1
    assert messages[0].content.startswith("¿Puede revisar")


def main() -> int:
    print("=" * 60)
    print("Legal Rent AI - Phase 5 Delivery Tests")
    print("=" * 60)
    try:
        test_report_json_and_pdf_generation()
        print("Reports JSON/PDF: PASSED")
        test_chat_session_and_message()
        print("Chat session/messages: PASSED")
        test_review_communication_persists_messages()
        print("Review communication messages: PASSED")
        test_review_communication_without_prior_analysis()
        print("Review communication without analysis: PASSED")
        print("=" * 60)
        print("ALL TESTS PASSED")
        print("=" * 60)
        return 0
    except Exception as exc:
        print(f"Test failed: {exc}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
