"""Contract and document business logic."""

import logging
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)

from config.settings import Settings, get_settings
from data.contract_dto import ContractDTO, ContractDocumentDTO, ContractPartyDTO, ContractSummaryDTO
from data.repositories.contract_document_repository import ContractDocumentRepository
from data.repositories.contract_party_repository import ContractPartyRepository
from data.repositories.contract_repository import ContractRepository
from data.repositories.download_log_repository import DownloadLogRepository
from document.classifier import DOCUMENT_TYPE_LAWYER_REVISION, classify_document
from document.text_extractor import extract_document_text
from document.validation import DocumentValidationError, ValidatedDocument, validate_upload
from domain.contract_status import (
    InvalidStatusTransitionError,
    assert_transition,
    is_contract_locked,
    is_visible_to_lawyer,
    validate_status_value,
)
from domain.entities import Role


class ContractAccessError(Exception):
    """Raised when a user cannot access a contract."""

    def __init__(self, message: str = "Access denied", status_code: int = 403):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class ContractNotFoundError(Exception):
    """Raised when a contract does not exist."""

    def __init__(self, message: str = "Contract not found"):
        super().__init__(message)
        self.message = message


class DocumentNotFoundError(Exception):
    """Raised when a document does not exist."""

    def __init__(self, message: str = "Document not found"):
        super().__init__(message)
        self.message = message


ALLOWED_PERSPECTIVES = {"tenant"}


class ContractService:
    """Manages contract creation and document uploads."""

    def __init__(
        self,
        contract_repository: ContractRepository | None = None,
        document_repository: ContractDocumentRepository | None = None,
        party_repository: ContractPartyRepository | None = None,
        download_log_repository: DownloadLogRepository | None = None,
        settings: Settings | None = None,
    ):
        self._settings = settings or get_settings()
        self._contracts = contract_repository or ContractRepository(self._settings)
        self._documents = document_repository or ContractDocumentRepository(self._settings)
        self._parties = party_repository or ContractPartyRepository(self._settings)
        self._download_logs = download_log_repository or DownloadLogRepository(self._settings)

    def create_contract_with_document(
        self,
        current_user: dict,
        perspective: str,
        validated_document: ValidatedDocument,
        title: str | None = None,
    ) -> ContractDTO:
        """Create a contract and attach the first document (RF-03, RF-08)."""
        if current_user["role"] == Role.LAWYER:
            raise ContractAccessError("Lawyers cannot upload contracts")
        self._validate_perspective(perspective)
        document_type = self._classify_document_type(validated_document, is_first_document=True)
        extraction = self._extract_text(validated_document)

        contract = self._contracts.create(
            user_id=current_user["user_id"],
            perspective=perspective,
            title=title,
        )
        document = self._documents.create(
            contract_id=contract.id,
            file_name=validated_document.file_name,
            file_content=validated_document.content,
            file_size_bytes=validated_document.file_size_bytes,
            document_type=document_type,
            mime_type=validated_document.mime_type,
            extracted_text=extraction.text or None,
            extraction_method=extraction.extraction_method,
            page_count=extraction.page_count,
        )
        contract.documents = [document]
        return contract

    def add_document(
        self,
        current_user: dict,
        contract_id: str,
        validated_document: ValidatedDocument,
        *,
        is_signed_version: bool = False,
    ) -> ContractDocumentDTO:
        """Attach an additional document to a contract (RF-05, RF-08, RF-57)."""
        self._ensure_can_modify(current_user, contract_id)

        contract = self._contracts.get_by_id(contract_id)
        if contract is None:
            raise ContractNotFoundError()
        self._ensure_not_locked(contract)

        existing_documents = self._documents.list_by_contract(contract_id)
        document_type = self._classify_document_type(
            validated_document,
            is_first_document=len(existing_documents) == 0,
        )
        extraction = self._extract_text(validated_document)

        return self._documents.create(
            contract_id=contract_id,
            file_name=validated_document.file_name,
            file_content=validated_document.content,
            file_size_bytes=validated_document.file_size_bytes,
            document_type=document_type,
            mime_type=validated_document.mime_type,
            extracted_text=extraction.text or None,
            extraction_method=extraction.extraction_method,
            page_count=extraction.page_count,
            is_signed_version=is_signed_version,
        )

    def update_contract(
        self,
        current_user: dict,
        contract_id: str,
        status: str | None = None,
        title: str | None = None,
        closure_notes: str | None = None,
    ) -> ContractDTO:
        """Update contract metadata or lifecycle status (RF-56)."""
        contract = self._get_accessible_contract(current_user, contract_id)
        self._ensure_not_locked(contract)

        if status is not None:
            validate_status_value(status)
            self._ensure_can_change_status(current_user, contract)
            assert_transition(current_user["role"], contract.status, status)
            self._validate_status_transition_context(
                current_user,
                contract,
                status,
                closure_notes,
            )

        if title is not None and title != contract.title:
            self._ensure_can_modify(current_user, contract_id)

        previous_status = contract.status
        previous_closure_notes = contract.closure_notes

        updated = self._contracts.update_contract(
            contract_id=contract_id,
            status=status,
            title=title,
            closure_notes=closure_notes,
        )
        if updated is None:
            raise ContractNotFoundError()

        if (
            status == "terminated"
            and previous_status == "approved"
            and current_user["role"] == Role.LAWYER
        ):
            from agents.signing_coordination.runner import SigningCoordinationError
            from services.signing_coordination_service import SigningCoordinationService

            notes_for_agent = (closure_notes if closure_notes is not None else updated.closure_notes) or ""
            try:
                SigningCoordinationService(settings=self._settings).run_for_terminated_contract(
                    contract_id,
                    notes_for_agent,
                )
            except SigningCoordinationError as exc:
                self._contracts.update_contract(
                    contract_id=contract_id,
                    status=previous_status,
                    closure_notes=previous_closure_notes,
                )
                raise InvalidStatusTransitionError(str(exc.message)) from exc

        if status == "in_review" and contract.status != "in_review":
            from services.analysis_service import AnalysisService

            AnalysisService().promote_analyses_for_contract_review(contract_id)

        if (
            status == "approved"
            and contract.status == "in_review"
            and current_user["role"] == Role.CLIENT
        ):
            from services.review_communication_service import ReviewCommunicationService

            try:
                ReviewCommunicationService(settings=self._settings).record_client_approved_edited_contract(
                    current_user,
                    contract_id,
                    updated.title,
                )
            except Exception:
                logger.exception(
                    "Failed to record client approval message for contract %s",
                    contract_id,
                )

        updated.documents = self._documents.list_by_contract(contract_id)
        updated.parties = self._load_parties(contract_id)
        return updated

    def list_contracts(self, current_user: dict) -> List[ContractSummaryDTO]:
        """List contracts visible to the current user."""
        role = current_user["role"]
        if role == Role.LAWYER:
            summaries = self._contracts.list_for_lawyer()
        else:
            summaries = self._contracts.list_for_user(current_user["user_id"])
        return self._attach_parties_to_summaries(summaries)

    def delete_contract(self, current_user: dict, contract_id: str) -> None:
        """Soft-delete a contract and its documents (RF-53)."""
        self._ensure_can_delete(current_user, contract_id)

        contract = self._contracts.get_by_id(contract_id)
        if contract is None:
            raise ContractNotFoundError()
        self._ensure_not_locked(contract)

        self._documents.soft_delete_by_contract(contract_id)
        deleted = self._contracts.soft_delete(contract_id)
        if not deleted:
            raise ContractNotFoundError()

    def get_contract(self, current_user: dict, contract_id: str) -> ContractDTO:
        """Return contract detail with document metadata."""
        contract = self._get_accessible_contract(current_user, contract_id)
        contract.documents = self._documents.list_by_contract(contract_id)
        contract.parties = self._load_parties(contract_id)
        return contract

    def list_documents(
        self,
        current_user: dict,
        contract_id: str,
    ) -> List[ContractDocumentDTO]:
        """List documents for an accessible contract."""
        self._get_accessible_contract(current_user, contract_id)
        return self._documents.list_by_contract(contract_id)

    def get_document_content(
        self,
        current_user: dict,
        contract_id: str,
        document_id: str,
    ) -> Tuple[str, str, bytes]:
        """Return binary content for download and log the event (RF-55)."""
        self._get_accessible_contract(current_user, contract_id)
        content = self._documents.get_content(contract_id, document_id)
        if content is None:
            raise DocumentNotFoundError()

        self._download_logs.log_download(
            user_id=current_user["user_id"],
            resource_type="document",
            resource_id=document_id,
        )
        return content

    def get_document_text(
        self,
        current_user: dict,
        contract_id: str,
        document_id: str,
    ) -> Tuple[str, str | None, int | None]:
        """Return persisted extracted text for a document (RF-06)."""
        self._get_accessible_contract(current_user, contract_id)
        extracted = self._documents.get_extracted_text(contract_id, document_id)
        if extracted is None:
            raise DocumentNotFoundError()
        return extracted

    def upload_lawyer_revision(
        self,
        current_user: dict,
        contract_id: str,
        validated_document: ValidatedDocument,
    ) -> ContractDocumentDTO:
        """Upload a lawyer-edited contract file, replacing any prior revision."""
        contract = self._get_accessible_contract(current_user, contract_id)
        self._ensure_not_locked(contract)
        self._ensure_can_upload_lawyer_revision(current_user, contract)

        self._documents.soft_delete_by_document_type(
            contract_id,
            DOCUMENT_TYPE_LAWYER_REVISION,
        )
        extraction = self._extract_text(validated_document)
        document = self._documents.create(
            contract_id=contract_id,
            file_name=validated_document.file_name,
            file_content=validated_document.content,
            file_size_bytes=validated_document.file_size_bytes,
            document_type=DOCUMENT_TYPE_LAWYER_REVISION,
            mime_type=validated_document.mime_type,
            extracted_text=extraction.text or None,
            extraction_method=extraction.extraction_method,
            page_count=extraction.page_count,
        )
        self._contracts.touch_updated_at(contract_id)

        from services.review_communication_service import ReviewCommunicationService

        try:
            ReviewCommunicationService(settings=self._settings).record_lawyer_sent_edited_contract(
                current_user,
                contract_id,
                contract.title,
            )
        except Exception:
            logger.exception(
                "Failed to record lawyer revision message for contract %s",
                contract_id,
            )

        return document

    def validate_upload(
        self,
        file_name: str,
        content: bytes,
        content_type: str | None = None,
    ) -> ValidatedDocument:
        """Validate uploaded bytes (RF-03, RF-04)."""
        return validate_upload(
            file_name=file_name,
            content=content,
            content_type=content_type,
            max_size_bytes=self._settings.max_upload_size_bytes,
        )

    def _extract_text(self, validated_document: ValidatedDocument):
        return extract_document_text(
            content=validated_document.content,
            mime_type=validated_document.mime_type,
            ocr_enabled=self._settings.ocr_enabled,
            max_pdf_pages=self._settings.max_extraction_pdf_pages,
            ocr_max_pages=self._settings.ocr_max_pages,
        )

    def _get_accessible_contract(self, current_user: dict, contract_id: str) -> ContractDTO:
        contract = self._contracts.get_by_id(contract_id)
        if contract is None:
            raise ContractNotFoundError()

        role = current_user["role"]
        if role == Role.LAWYER:
            if not is_visible_to_lawyer(contract.status):
                raise ContractAccessError("Contract is not available for legal review")
            return contract

        if contract.user_id != current_user["user_id"]:
            raise ContractAccessError()

        return contract

    @staticmethod
    def _ensure_not_locked(contract: ContractDTO) -> None:
        if is_contract_locked(contract.status):
            raise ContractAccessError("This contract is closed and cannot be modified")

    def _validate_status_transition_context(
        self,
        current_user: dict,
        contract: ContractDTO,
        target_status: str,
        closure_notes: str | None,
    ) -> None:
        role = current_user["role"]
        if (
            role == Role.CLIENT
            and contract.status == "in_review"
            and target_status == "approved"
        ):
            documents = self._documents.list_by_contract(contract.id)
            has_revision = any(
                doc.document_type == DOCUMENT_TYPE_LAWYER_REVISION for doc in documents
            )
            if not has_revision:
                raise InvalidStatusTransitionError(
                    "A lawyer-edited version must be uploaded before approval"
                )

        if (
            role == Role.LAWYER
            and contract.status == "approved"
            and target_status == "terminated"
        ):
            notes = (closure_notes or "").strip()
            if not notes:
                raise InvalidStatusTransitionError(
                    "Final notes are required to close the contract"
                )

    def _ensure_can_upload_lawyer_revision(
        self,
        current_user: dict,
        contract: ContractDTO,
    ) -> None:
        role = current_user["role"]
        if role == Role.LAWYER and is_visible_to_lawyer(contract.status):
            return
        raise ContractAccessError("You cannot upload a lawyer revision for this contract")

    def _ensure_can_change_status(self, current_user: dict, contract: ContractDTO) -> None:
        role = current_user["role"]
        if role == Role.LAWYER:
            return
        if role == Role.CLIENT and contract.user_id == current_user["user_id"]:
            return
        raise ContractAccessError("You cannot change this contract status")

    def _ensure_can_delete(self, current_user: dict, contract_id: str) -> None:
        role = current_user["role"]
        if role == Role.LAWYER:
            raise ContractAccessError("Lawyers cannot delete contracts")

        if not self._contracts.user_owns_contract(contract_id, current_user["user_id"]):
            contract = self._contracts.get_by_id(contract_id)
            if contract is None:
                raise ContractNotFoundError()
            raise ContractAccessError()

    def _ensure_can_modify(self, current_user: dict, contract_id: str) -> None:
        contract = self._contracts.get_by_id(contract_id)
        if contract is None:
            raise ContractNotFoundError()
        self._ensure_not_locked(contract)
        if not self._contracts.user_owns_contract(contract_id, current_user["user_id"]):
            raise ContractAccessError()

    def _load_parties(self, contract_id: str) -> List[ContractPartyDTO]:
        return [
            ContractPartyDTO(
                party_type=item["party_type"],
                name=item["name"],
                legal_representative=item.get("legal_representative"),
                confidence=item.get("confidence"),
                source_page=item.get("source_page"),
            )
            for item in self._parties.list_by_contract(contract_id)
        ]

    def _attach_parties_to_summaries(
        self,
        summaries: List[ContractSummaryDTO],
    ) -> List[ContractSummaryDTO]:
        if not summaries:
            return summaries
        grouped = self._parties.list_by_contract_ids([summary.id for summary in summaries])
        for summary in summaries:
            summary.parties = [
                ContractPartyDTO(
                    party_type=item["party_type"],
                    name=item["name"],
                    legal_representative=item.get("legal_representative"),
                    confidence=item.get("confidence"),
                    source_page=item.get("source_page"),
                )
                for item in grouped.get(summary.id, [])
            ]
        return summaries

    @staticmethod
    def _classify_document_type(
        validated_document: ValidatedDocument,
        is_first_document: bool,
    ) -> str:
        classification = classify_document(
            file_name=validated_document.file_name,
            content=validated_document.content,
            mime_type=validated_document.mime_type,
            is_first_document=is_first_document,
        )
        return classification.document_type

    @staticmethod
    def _validate_perspective(perspective: str) -> None:
        if perspective not in ALLOWED_PERSPECTIVES:
            raise DocumentValidationError(
                "Perspective must be tenant",
                status_code=400,
            )
