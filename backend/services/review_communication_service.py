"""Client–lawyer review communication stored in SQL Server (RF-50, RF-51)."""

from __future__ import annotations

import logging

from config.settings import Settings, get_settings
from data.delivery_dto import ReviewMessageDTO
from data.repositories.analysis_repository import AnalysisRepository
from data.repositories.contract_repository import ContractRepository
from data.repositories.review_message_repository import ReviewMessageRepository
from data.repositories.review_message_read_repository import ReviewMessageReadRepository
from data.repositories.user_repository import UserRepository
from services.contract_service import ALLOWED_PERSPECTIVES
from domain.contract_status import is_visible_to_lawyer
from domain.entities import Role
from services.analysis_service import AnalysisNotFoundError, AnalysisService
from services.contract_service import ContractAccessError, ContractNotFoundError

logger = logging.getLogger(__name__)

CLIENT_APPROVED_EDITED_CONTRACT_MESSAGE = (
    "[Approval recorded] The client confirmed acceptance of the edited contract version. "
    "The file is now in «Approved» status."
)

LAWYER_SENT_EDITED_CONTRACT_MESSAGE = (
    "[Edited version sent] The lawyer uploaded a new edited contract version. "
    "Review the original vs. edited comparison and, if you agree, mark it as approved."
)


class ReviewCommunicationError(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class ReviewCommunicationService:
    def __init__(
        self,
        analysis_service: AnalysisService | None = None,
        message_repository: ReviewMessageRepository | None = None,
        read_repository: ReviewMessageReadRepository | None = None,
        contract_repository: ContractRepository | None = None,
        settings: Settings | None = None,
    ):
        self._settings = settings or get_settings()
        self._analysis = analysis_service or AnalysisService(settings=self._settings)
        self._messages = message_repository or ReviewMessageRepository(self._settings)
        self._reads = read_repository or ReviewMessageReadRepository(self._settings)
        self._contracts = contract_repository or ContractRepository(self._settings)
        self._analyses = AnalysisRepository(self._settings)
        self._users = UserRepository(self._settings)

    def record_client_approved_edited_contract(
        self,
        current_user: dict,
        contract_id: str,
        contract_title: str | None = None,
    ) -> ReviewMessageDTO | None:
        """Post an automatic chat message and email notification when the client approves."""
        if current_user["role"] != Role.CLIENT:
            return None

        analysis_id = self._resolve_communication_analysis_id(current_user, contract_id)
        message = self.send_message(
            current_user,
            analysis_id,
            CLIENT_APPROVED_EDITED_CONTRACT_MESSAGE,
        )

        lawyer_email = self._users.get_primary_lawyer_email()
        if not lawyer_email:
            logger.warning(
                "Client approved contract %s but no lawyer email is configured",
                contract_id,
            )
            return message

        from services.notification_service import NotificationError, NotificationService

        try:
            NotificationService(settings=self._settings).notify_lawyer(
                current_user,
                analysis_id,
                lawyer_email,
                CLIENT_APPROVED_EDITED_CONTRACT_MESSAGE,
            )
        except NotificationError as exc:
            logger.warning(
                "Client approval chat message saved but lawyer notification failed: %s",
                exc.message,
            )
        except Exception:
            logger.exception(
                "Client approval chat message saved but lawyer notification failed"
            )

        return message

    def record_lawyer_sent_edited_contract(
        self,
        current_user: dict,
        contract_id: str,
        contract_title: str | None = None,
    ) -> ReviewMessageDTO | None:
        """Post an automatic chat message and email notification when the lawyer uploads a revision."""
        if current_user["role"] != Role.LAWYER:
            return None

        analysis_id = self._resolve_communication_analysis_id(current_user, contract_id)
        message = self.send_message(
            current_user,
            analysis_id,
            LAWYER_SENT_EDITED_CONTRACT_MESSAGE,
        )

        contract = self._contracts.get_by_id(contract_id)
        if contract is None:
            return message

        client = self._users.get_by_id(contract.user_id)
        if client is None or not client.email:
            logger.warning(
                "Lawyer uploaded revision for contract %s but client email is unavailable",
                contract_id,
            )
            return message

        from services.notification_service import NotificationError, NotificationService

        try:
            NotificationService(settings=self._settings).notify_client(
                current_user,
                analysis_id,
                client.email,
                LAWYER_SENT_EDITED_CONTRACT_MESSAGE,
            )
        except NotificationError as exc:
            logger.warning(
                "Lawyer revision chat message saved but client notification failed: %s",
                exc.message,
            )
        except Exception:
            logger.exception(
                "Lawyer revision chat message saved but client notification failed"
            )

        return message

    def list_messages(self, current_user: dict, analysis_id: str) -> list[ReviewMessageDTO]:
        self._ensure_can_read(current_user, analysis_id)
        return self._messages.list_by_analysis(analysis_id)

    def list_messages_for_contract(
        self,
        current_user: dict,
        contract_id: str,
    ) -> list[ReviewMessageDTO]:
        if not self._can_access_contract(current_user, contract_id):
            raise ContractAccessError()
        return self._messages.list_by_contract(contract_id)

    def send_message_for_contract(
        self,
        current_user: dict,
        contract_id: str,
        content: str,
    ) -> ReviewMessageDTO:
        analysis_id = self._resolve_communication_analysis_id(current_user, contract_id)
        return self.send_message(current_user, analysis_id, content)

    def unread_counts_by_contract(
        self,
        current_user: dict,
        contract_ids: list[str],
    ) -> dict[str, int]:
        accessible_ids = [
            contract_id
            for contract_id in contract_ids
            if self._can_access_contract(current_user, contract_id)
        ]
        return self._reads.unread_counts_by_contract(
            current_user["user_id"],
            accessible_ids,
        )

    def mark_contract_read(self, current_user: dict, contract_id: str) -> None:
        if not self._can_access_contract(current_user, contract_id):
            raise ContractAccessError()
        self._reads.mark_contract_read(current_user["user_id"], contract_id)

    def send_message(
        self,
        current_user: dict,
        analysis_id: str,
        content: str,
    ) -> ReviewMessageDTO:
        content = content.strip()
        if not content:
            raise ReviewCommunicationError("Message cannot be empty")

        analysis, contract = self._ensure_can_read(current_user, analysis_id)
        role = current_user["role"]

        if role == Role.CLIENT and contract.status == "draft":
            raise ReviewCommunicationError(
                "Send the contract to legal review before messaging the lawyer"
            )

        if role == Role.LAWYER and contract.status == "draft":
            raise ReviewCommunicationError("Contract is not available for legal review")

        if role not in (Role.CLIENT, Role.LAWYER):
            raise ContractAccessError()

        return self._messages.create(
            analysis_id=analysis.id,
            user_id=current_user["user_id"],
            content=content,
        )

    def _can_access_contract(self, current_user: dict, contract_id: str) -> bool:
        contract = self._contracts.get_by_id(contract_id)
        if contract is None:
            return False

        role = current_user["role"]
        if role == Role.CLIENT:
            return contract.user_id == current_user["user_id"]
        if role == Role.LAWYER:
            return is_visible_to_lawyer(contract.status)
        return False

    def _resolve_communication_analysis_id(
        self,
        current_user: dict,
        contract_id: str,
    ) -> str:
        contract = self._contracts.get_by_id(contract_id)
        if contract is None:
            raise ContractNotFoundError()

        role = current_user["role"]
        if role == Role.CLIENT:
            if contract.user_id != current_user["user_id"]:
                raise ContractAccessError()
        elif role == Role.LAWYER:
            if not is_visible_to_lawyer(contract.status):
                raise ContractAccessError("Contract is not available for legal review")
        else:
            raise ContractAccessError()

        analyses = self._analyses.list_by_contract(contract_id)
        if analyses:
            anchor = min(analyses, key=lambda item: item.created_at)
            return anchor.id

        perspective = (contract.perspective or "neutral").strip().lower()
        if perspective not in ALLOWED_PERSPECTIVES:
            perspective = "neutral"

        placeholder = self._analyses.create(
            contract_id=contract_id,
            perspective=perspective,
            document_scope="original",
            status="failed",
        )
        return placeholder.id

    def _ensure_can_read(self, current_user: dict, analysis_id: str):
        analysis = self._analysis.get_analysis(current_user, analysis_id)
        contract = self._contracts.get_by_id(analysis.contract_id)
        if contract is None:
            raise ContractNotFoundError()

        role = current_user["role"]
        if role == Role.CLIENT:
            if contract.user_id != current_user["user_id"]:
                raise ContractAccessError()
            return analysis, contract

        if role == Role.LAWYER:
            if not is_visible_to_lawyer(contract.status):
                raise ContractAccessError("Contract is not available for legal review")
            return analysis, contract

        raise ContractAccessError()
