"""Contract status, download log and text persistence tests (Phase 1)."""

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
from domain.contract_status import InvalidStatusTransitionError, assert_transition
from domain.entities import Role
from services.contract_service import ContractService


def _minimal_pdf() -> bytes:
    return b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"


def _docx_with_text(text: str) -> bytes:
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


def test_status_transition_rules():
    assert_transition(Role.CLIENT, "draft", "in_review")
    try:
        assert_transition(Role.CLIENT, "draft", "terminated")
        raise AssertionError("Expected invalid transition")
    except InvalidStatusTransitionError:
        pass
    try:
        assert_transition(Role.CLIENT, "draft", "signed")
        raise AssertionError("Expected invalid transition")
    except InvalidStatusTransitionError:
        pass
    try:
        assert_transition(Role.CLIENT, "in_review", "terminated")
        raise AssertionError("Client must not terminate while in legal review")
    except InvalidStatusTransitionError:
        pass
    assert_transition(Role.LAWYER, "in_review", "terminated")
    try:
        assert_transition(Role.LAWYER, "in_review", "draft")
        raise AssertionError("Lawyer must not return contracts to draft")
    except InvalidStatusTransitionError:
        pass


def test_contract_status_workflow():
    current_user = _client_user()
    service = ContractService()

    contract = service.create_contract_with_document(
        current_user=current_user,
        perspective="tenant",
        validated_document=service.validate_upload(
            "lease.pdf",
            _minimal_pdf(),
            "application/pdf",
        ),
        title=f"Status Test {uuid.uuid4().hex[:8]}",
    )
    assert contract.status == "draft"

    updated = service.update_contract(
        current_user=current_user,
        contract_id=contract.id,
        status="in_review",
    )
    assert updated.status == "in_review"

    lawyer = _lawyer_user()
    approved = service.update_contract(
        current_user=lawyer,
        contract_id=contract.id,
        status="approved",
    )
    assert approved.status == "approved"


def test_document_text_persisted_on_upload():
    current_user = _client_user()
    service = ContractService()
    text = "Clausula de renta mensual y deposito en garantia"

    contract = service.create_contract_with_document(
        current_user=current_user,
        perspective="landlord",
        validated_document=service.validate_upload(
            "contract.docx",
            _docx_with_text(text),
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ),
        title=f"Text Test {uuid.uuid4().hex[:8]}",
    )
    document_id = contract.documents[0].id
    assert contract.documents[0].extraction_method == "native"

    extracted_text, method, _page_count = service.get_document_text(
        current_user,
        contract.id,
        document_id,
    )
    assert "renta mensual" in extracted_text.lower()
    assert method == "native"


def test_download_creates_log_entry():
    current_user = _client_user()
    service = ContractService()

    contract = service.create_contract_with_document(
        current_user=current_user,
        perspective="tenant",
        validated_document=service.validate_upload("lease.pdf", _minimal_pdf()),
        title=f"Download Log {uuid.uuid4().hex[:8]}",
    )
    document_id = contract.documents[0].id

    service.get_document_content(current_user, contract.id, document_id)

    settings = get_settings()
    with get_connection(settings) as connection:
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT COUNT(*)
            FROM app.download_logs
            WHERE user_id = ? AND resource_type = N'document' AND resource_id = ?
            """,
            current_user["user_id"],
            document_id,
        )
        count = cursor.fetchone()[0]

    assert count >= 1


def main() -> int:
    print("=" * 60)
    print("Legal Rent AI - Phase 1 Tests")
    print("=" * 60)
    print()
    try:
        test_status_transition_rules()
        print("Status transition rules: PASSED")

        test_contract_status_workflow()
        print("Contract status workflow: PASSED")

        test_document_text_persisted_on_upload()
        print("Text persistence on upload: PASSED")

        test_download_creates_log_entry()
        print("Download log entry: PASSED")

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
