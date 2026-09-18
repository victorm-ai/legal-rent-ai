"""Email delivery for lawyer notifications (RF-51)."""

from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage

from config.settings import Settings, get_settings
from notification.azure_communication_email import (
    AzureCommunicationEmailSender,
    should_send_live_email,
)

logger = logging.getLogger(__name__)


class EmailSender:
    def __init__(self, settings: Settings | None = None):
        self._settings = settings or get_settings()

    def send_lawyer_notification(
        self,
        lawyer_email: str,
        client_email: str,
        decision: str,
        analysis_id: str,
        contract_title: str | None,
        summary_excerpt: str | None,
    ) -> None:
        subject = f"Legal Rent AI — Client decision on contract analysis"
        title = contract_title or "Lease contract"
        body_lines = [
            "A client has submitted a decision regarding a contract analysis.",
            "",
            f"Contract: {title}",
            f"Analysis ID: {analysis_id}",
            f"Client: {client_email}",
            "",
            "Decision:",
            decision,
            "",
        ]
        if summary_excerpt:
            body_lines.extend(["Executive summary excerpt:", summary_excerpt[:1500], ""])
        body_lines.append("This message was generated automatically by Legal Rent AI.")
        body = "\n".join(body_lines)

        if should_send_live_email(self._settings):
            html_body = "<pre style=\"font-family:sans-serif;white-space:pre-wrap\">" + _escape_html(body) + "</pre>"
            AzureCommunicationEmailSender(self._settings).send_html(
                to_email=lawyer_email,
                subject=subject,
                html_body=html_body,
                plain_text=body,
            )
        elif self._settings.smtp_host:
            self._send_smtp(lawyer_email, subject, body)
        elif self._settings.notification_dev_mode:
            logger.info(
                "DEV notification email to=%s subject=%s body=%s",
                lawyer_email,
                subject,
                body,
            )
        else:
            raise RuntimeError("SMTP is not configured and dev mode is disabled.")

    def send_client_notification(
        self,
        client_email: str,
        lawyer_email: str,
        message: str,
        analysis_id: str,
        contract_title: str | None,
        summary_excerpt: str | None,
    ) -> None:
        subject = "Legal Rent AI — Nueva versión editada del contrato"
        title = contract_title or "Lease contract"
        body_lines = [
            "Su abogado ha subido una nueva versión editada del contrato para su revisión.",
            "",
            f"Contract: {title}",
            f"Analysis ID: {analysis_id}",
            f"Lawyer: {lawyer_email}",
            "",
            "Message:",
            message,
            "",
        ]
        if summary_excerpt:
            body_lines.extend(["Executive summary excerpt:", summary_excerpt[:1500], ""])
        body_lines.append("This message was generated automatically by Legal Rent AI.")
        body = "\n".join(body_lines)

        if should_send_live_email(self._settings):
            html_body = "<pre style=\"font-family:sans-serif;white-space:pre-wrap\">" + _escape_html(body) + "</pre>"
            AzureCommunicationEmailSender(self._settings).send_html(
                to_email=client_email,
                subject=subject,
                html_body=html_body,
                plain_text=body,
            )
        elif self._settings.smtp_host:
            self._send_smtp(client_email, subject, body)
        elif self._settings.notification_dev_mode:
            logger.info(
                "DEV notification email to=%s subject=%s body=%s",
                client_email,
                subject,
                body,
            )
        else:
            raise RuntimeError("SMTP is not configured and dev mode is disabled.")

    def _send_smtp(self, to_email: str, subject: str, body: str) -> None:
        message = EmailMessage()
        message["From"] = self._settings.smtp_from
        message["To"] = to_email
        message["Subject"] = subject
        message.set_content(body)

        with smtplib.SMTP(self._settings.smtp_host, self._settings.smtp_port) as server:
            if self._settings.smtp_use_tls:
                server.starttls()
            if self._settings.smtp_user:
                server.login(self._settings.smtp_user, self._settings.smtp_password)
            server.send_message(message)


def _escape_html(text: str) -> str:
    import html

    return html.escape(text)
