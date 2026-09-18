"""Contract upload tests (RF-03, RF-04, RF-05)."""

import io
import os
import sys
import uuid
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from auth.models import UserCredentials
from auth.service import AuthService
from document.validation import DocumentValidationError, validate_upload
from services.contract_service import (
    ContractAccessError,
    ContractNotFoundError,
    ContractService,
    DocumentNotFoundError,
)
from services.review_communication_service import (
    CLIENT_APPROVED_EDITED_CONTRACT_MESSAGE,
    LAWYER_SENT_EDITED_CONTRACT_MESSAGE,
    ReviewCommunicationService,
)


def _minimal_pdf() -> bytes:
    return b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"


def _minimal_docx() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types></Types>")
    return buffer.getvalue()


def test_validation_pdf():
    validated = validate_upload("contract.pdf", _minimal_pdf(), "application/pdf")
    assert validated.mime_type == "application/pdf"
    assert validated.file_size_bytes > 0


def test_validation_rejects_large_file():
    content = _minimal_pdf() + (b"0" * (25 * 1024 * 1024))
    try:
        validate_upload("large.pdf", content)
        raise AssertionError("Expected size validation to fail")
    except DocumentValidationError as exc:
        assert exc.status_code == 413


def test_validation_rejects_invalid_extension():
    try:
        validate_upload("contract.txt", b"hello")
        raise AssertionError("Expected extension validation to fail")
    except DocumentValidationError as exc:
        assert exc.status_code == 400


def test_contract_upload_flow():
    auth_service = AuthService()
    login = auth_service.login(
        UserCredentials(email="code.zemoreno@gmail.com", password="cliente123")
    )
    assert login.success

    current_user = {
        "user_id": login.user.id,
        "email": login.user.email,
        "role": login.user.role,
    }

    service = ContractService()
    contract = service.create_contract_with_document(
        current_user=current_user,
        perspective="tenant",
        validated_document=service.validate_upload(
            "lease.pdf",
            _minimal_pdf(),
            "application/pdf",
        ),
        title=f"Test Contract {uuid.uuid4().hex[:8]}",
    )
    assert contract.id
    assert len(contract.documents) == 1
    assert contract.documents[0].document_type == "main_contract"

    annex = service.add_document(
        current_user=current_user,
        contract_id=contract.id,
        validated_document=service.validate_upload(
            "Anexo_Condiciones.docx",
            _minimal_docx(),
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ),
    )
    assert annex.contract_id == contract.id
    assert annex.document_type == "annex"

    documents = service.list_documents(current_user, contract.id)
    assert len(documents) == 2

    file_name, mime_type, content = service.get_document_content(
        current_user,
        contract.id,
        annex.id,
    )
    assert file_name == "Anexo_Condiciones.docx"
    assert mime_type.endswith("wordprocessingml.document")
    assert content.startswith(b"PK")


def test_lawyer_cannot_upload_contract():
    auth_service = AuthService()
    lawyer_login = auth_service.login(
        UserCredentials(email="abogado@contractes.com", password="abogado123")
    )
    assert lawyer_login.success

    lawyer_user = {
        "user_id": lawyer_login.user.id,
        "email": lawyer_login.user.email,
        "role": lawyer_login.user.role,
    }

    service = ContractService()
    try:
        service.create_contract_with_document(
            current_user=lawyer_user,
            perspective="tenant",
            validated_document=service.validate_upload(
                "lease.pdf",
                _minimal_pdf(),
                "application/pdf",
            ),
            title=f"Lawyer Upload Test {uuid.uuid4().hex[:8]}",
        )
        raise AssertionError("Expected lawyer upload to be denied")
    except ContractAccessError as exc:
        assert "cannot upload" in exc.message.lower()


def test_lawyer_can_upload_revision_visible_to_client():
    auth_service = AuthService()
    client_login = auth_service.login(
        UserCredentials(email="code.zemoreno@gmail.com", password="cliente123")
    )
    lawyer_login = auth_service.login(
        UserCredentials(email="abogado@contractes.com", password="abogado123")
    )
    assert client_login.success
    assert lawyer_login.success

    client_user = {
        "user_id": client_login.user.id,
        "email": client_login.user.email,
        "role": client_login.user.role,
    }
    lawyer_user = {
        "user_id": lawyer_login.user.id,
        "email": lawyer_login.user.email,
        "role": lawyer_login.user.role,
    }

    service = ContractService()
    contract = service.create_contract_with_document(
        current_user=client_user,
        perspective="tenant",
        validated_document=service.validate_upload(
            "lease.docx",
            _minimal_docx(),
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ),
        title=f"Lawyer Revision Test {uuid.uuid4().hex[:8]}",
    )

    service.update_contract(client_user, contract.id, status="in_review")

    first_revision = service.upload_lawyer_revision(
        lawyer_user,
        contract.id,
        service.validate_upload(
            "revision-v1.docx",
            _minimal_docx(),
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ),
    )
    assert first_revision.document_type == "lawyer_revision"

    second_revision = service.upload_lawyer_revision(
        lawyer_user,
        contract.id,
        service.validate_upload(
            "revision-v2.docx",
            _minimal_docx(),
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ),
    )
    assert second_revision.id != first_revision.id

    refreshed = service.get_contract(client_user, contract.id)
    revision_docs = [
        document for document in refreshed.documents if document.document_type == "lawyer_revision"
    ]
    assert len(revision_docs) == 1
    assert revision_docs[0].id == second_revision.id

    try:
        service.upload_lawyer_revision(
            client_user,
            contract.id,
            service.validate_upload(
                "client-revision.docx",
                _minimal_docx(),
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ),
        )
        raise AssertionError("Expected client revision upload to be denied")
    except ContractAccessError:
        pass


def test_client_approval_posts_review_message_for_lawyer():
    auth_service = AuthService()
    client_login = auth_service.login(
        UserCredentials(email="code.zemoreno@gmail.com", password="cliente123")
    )
    lawyer_login = auth_service.login(
        UserCredentials(email="abogado@contractes.com", password="abogado123")
    )
    assert client_login.success
    assert lawyer_login.success

    client_user = {
        "user_id": client_login.user.id,
        "email": client_login.user.email,
        "role": client_login.user.role,
    }
    lawyer_user = {
        "user_id": lawyer_login.user.id,
        "email": lawyer_login.user.email,
        "role": lawyer_login.user.role,
    }

    service = ContractService()
    contract = service.create_contract_with_document(
        current_user=client_user,
        perspective="tenant",
        validated_document=service.validate_upload(
            "approve-flow.docx",
            _minimal_docx(),
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ),
        title=f"Client Approval Chat {uuid.uuid4().hex[:8]}",
    )
    service.update_contract(client_user, contract.id, status="in_review")
    service.upload_lawyer_revision(
        lawyer_user,
        contract.id,
        service.validate_upload(
            "revision-approved.docx",
            _minimal_docx(),
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ),
    )

    updated = service.update_contract(client_user, contract.id, status="approved")
    assert updated.status == "approved"

    review_service = ReviewCommunicationService()
    messages = review_service.list_messages_for_contract(lawyer_user, contract.id)
    assert any(
        message.content == CLIENT_APPROVED_EDITED_CONTRACT_MESSAGE for message in messages
    )

    unread = review_service.unread_counts_by_contract(lawyer_user, [contract.id])
    assert unread.get(contract.id, 0) >= 1


def test_lawyer_revision_upload_posts_review_message_for_client():
    auth_service = AuthService()
    client_login = auth_service.login(
        UserCredentials(email="code.zemoreno@gmail.com", password="cliente123")
    )
    lawyer_login = auth_service.login(
        UserCredentials(email="abogado@contractes.com", password="abogado123")
    )
    assert client_login.success
    assert lawyer_login.success

    client_user = {
        "user_id": client_login.user.id,
        "email": client_login.user.email,
        "role": client_login.user.role,
    }
    lawyer_user = {
        "user_id": lawyer_login.user.id,
        "email": lawyer_login.user.email,
        "role": lawyer_login.user.role,
    }

    service = ContractService()
    contract = service.create_contract_with_document(
        current_user=client_user,
        perspective="tenant",
        validated_document=service.validate_upload(
            "revision-notify.docx",
            _minimal_docx(),
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ),
        title=f"Lawyer Revision Notify {uuid.uuid4().hex[:8]}",
    )
    service.update_contract(client_user, contract.id, status="in_review")
    service.upload_lawyer_revision(
        lawyer_user,
        contract.id,
        service.validate_upload(
            "revision-notify-v1.docx",
            _minimal_docx(),
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ),
    )

    review_service = ReviewCommunicationService()
    messages = review_service.list_messages_for_contract(client_user, contract.id)
    assert any(
        message.content == LAWYER_SENT_EDITED_CONTRACT_MESSAGE for message in messages
    )

    unread = review_service.unread_counts_by_contract(client_user, [contract.id])
    assert unread.get(contract.id, 0) >= 1


def test_soft_delete_contract():
    auth_service = AuthService()
    login = auth_service.login(
        UserCredentials(email="code.zemoreno@gmail.com", password="cliente123")
    )
    assert login.success

    current_user = {
        "user_id": login.user.id,
        "email": login.user.email,
        "role": login.user.role,
    }

    service = ContractService()
    contract = service.create_contract_with_document(
        current_user=current_user,
        perspective="tenant",
        validated_document=service.validate_upload(
            "lease.pdf",
            _minimal_pdf(),
            "application/pdf",
        ),
        title=f"Delete Test {uuid.uuid4().hex[:8]}",
    )

    lawyer_login = auth_service.login(
        UserCredentials(email="abogado@contractes.com", password="abogado123")
    )
    assert lawyer_login.success
    lawyer_user = {
        "user_id": lawyer_login.user.id,
        "email": lawyer_login.user.email,
        "role": lawyer_login.user.role,
    }

    try:
        service.delete_contract(lawyer_user, contract.id)
        raise AssertionError("Expected lawyer delete to be denied")
    except ContractAccessError:
        pass

    service.delete_contract(current_user, contract.id)

    contracts = service.list_contracts(current_user)
    assert all(item.id != contract.id for item in contracts)

    try:
        service.get_contract(current_user, contract.id)
        raise AssertionError("Expected deleted contract to be inaccessible")
    except ContractNotFoundError:
        pass


def main():
    print("=" * 60)
    print("Legal Rent AI - Contract Upload Tests")
    print("=" * 60)
    print()

    try:
        test_validation_pdf()
        print("PDF validation: PASSED")

        test_validation_rejects_large_file()
        print("25 MB limit: PASSED")

        test_validation_rejects_invalid_extension()
        print("Extension validation: PASSED")

        test_contract_upload_flow()
        print("Contract + multi-document flow: PASSED")

        test_lawyer_cannot_upload_contract()
        print("Lawyer upload denied: PASSED")

        test_lawyer_can_upload_revision_visible_to_client()
        print("Lawyer revision upload visible to client: PASSED")

        test_lawyer_revision_upload_posts_review_message_for_client()
        print("Lawyer revision review message for client: PASSED")

        test_client_approval_posts_review_message_for_lawyer()
        print("Client approval review message: PASSED")

        test_soft_delete_contract()
        print("Soft delete contract: PASSED")

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
