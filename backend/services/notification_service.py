"""Client–lawyer email notification business logic (RF-50, RF-51)."""

from __future__ import annotations

import re

from config.settings import Settings, get_settings
from data.delivery_dto import NotificationDTO
from data.repositories.notification_repository import NotificationRepository
from domain.entities import Role
from notification.email_sender import EmailSender
from services.analysis_service import AnalysisService


class NotificationError(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class NotificationService:
    def __init__(
        self,
        analysis_service: AnalysisService | None = None,
        notification_repository: NotificationRepository | None = None,
        email_sender: EmailSender | None = None,
        settings: Settings | None = None,
    ):
        self._settings = settings or get_settings()
        self._analysis = analysis_service or AnalysisService(settings=self._settings)
        self._notifications = notification_repository or NotificationRepository(self._settings)
        self._email = email_sender or EmailSender(self._settings)

    def notify_lawyer(
        self,
        current_user: dict,
        analysis_id: str,
        lawyer_email: str,
        decision: str,
    ) -> NotificationDTO:
        if current_user["role"] != Role.CLIENT:
            raise NotificationError("Only clients can notify a lawyer")

        lawyer_email = lawyer_email.strip()
        decision = decision.strip()
        if not _EMAIL_RE.match(lawyer_email):
            raise NotificationError("Invalid lawyer email address")
        if len(decision) < 10:
            raise NotificationError("Decision must be at least 10 characters")

        analysis = self._analysis.get_analysis(current_user, analysis_id)
        contract = self._analysis._contracts.get_by_id(analysis.contract_id)

        notification = self._notifications.create(
            analysis_id=analysis_id,
            user_id=current_user["user_id"],
            lawyer_email=lawyer_email,
            decision=decision,
            status="pending",
        )

        try:
            self._email.send_lawyer_notification(
                lawyer_email=lawyer_email,
                client_email=current_user["email"],
                decision=decision,
                analysis_id=analysis_id,
                contract_title=contract.title if contract else None,
                summary_excerpt=analysis.summary_executive,
            )
            updated = self._notifications.mark_sent(notification.id)
            return updated or notification
        except Exception as exc:
            self._notifications.mark_failed(notification.id)
            raise NotificationError(f"Failed to send notification: {exc}") from exc

    def notify_client(
        self,
        current_user: dict,
        analysis_id: str,
        client_email: str,
        message: str,
    ) -> NotificationDTO:
        if current_user["role"] != Role.LAWYER:
            raise NotificationError("Only lawyers can notify a client")

        client_email = client_email.strip()
        message = message.strip()
        if not _EMAIL_RE.match(client_email):
            raise NotificationError("Invalid client email address")
        if len(message) < 10:
            raise NotificationError("Message must be at least 10 characters")

        analysis = self._analysis.get_analysis(current_user, analysis_id)
        contract = self._analysis._contracts.get_by_id(analysis.contract_id)

        notification = self._notifications.create(
            analysis_id=analysis_id,
            user_id=current_user["user_id"],
            lawyer_email=client_email,
            decision=message,
            status="pending",
        )

        try:
            self._email.send_client_notification(
                client_email=client_email,
                lawyer_email=current_user["email"],
                message=message,
                analysis_id=analysis_id,
                contract_title=contract.title if contract else None,
                summary_excerpt=analysis.summary_executive,
            )
            updated = self._notifications.mark_sent(notification.id)
            return updated or notification
        except Exception as exc:
            self._notifications.mark_failed(notification.id)
            raise NotificationError(f"Failed to send notification: {exc}") from exc

    def list_notifications(self, current_user: dict, analysis_id: str) -> list[NotificationDTO]:
        self._analysis.get_analysis(current_user, analysis_id)
        return self._notifications.list_by_analysis(analysis_id)
