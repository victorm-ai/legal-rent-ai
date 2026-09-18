"""Azure Communication Services email delivery (with dev simulation)."""

from __future__ import annotations

import logging

from config.settings import Settings, get_settings
from notification.acs_errors import format_acs_send_error

logger = logging.getLogger(__name__)


class AzureCommunicationEmailError(RuntimeError):
    """ACS Email send failed with an actionable message."""

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


def acs_email_configured(settings: Settings | None = None) -> bool:
    settings = settings or get_settings()
    connection_string = (settings.azure_communication_connection_string or "").strip()
    sender = (settings.azure_communication_sender_address or "").strip()
    return bool(connection_string and sender)


def should_send_live_email(settings: Settings | None = None) -> bool:
    """True when ACS is configured and dev simulation is disabled."""
    settings = settings or get_settings()
    return acs_email_configured(settings) and not settings.notification_dev_mode


class AzureCommunicationEmailSender:
    """Sends HTML email via Azure Communication Services Email."""

    def __init__(self, settings: Settings | None = None):
        self._settings = settings or get_settings()

    def send_html(
        self,
        *,
        to_email: str,
        subject: str,
        html_body: str,
        plain_text: str | None = None,
    ) -> None:
        connection_string = (self._settings.azure_communication_connection_string or "").strip()
        sender = (self._settings.azure_communication_sender_address or "").strip()

        if not connection_string or not sender:
            if self._settings.notification_dev_mode:
                logger.info(
                    "DEV Azure Communication Services email to=%s subject=%s html_length=%s plain=%s",
                    to_email,
                    subject,
                    len(html_body),
                    (plain_text or "")[:500],
                )
                return
            raise RuntimeError(
                "Azure Communication Services is not configured and notification dev mode is disabled."
            )

        if self._settings.notification_dev_mode:
            logger.info(
                "DEV Azure Communication Services email to=%s subject=%s html_length=%s plain=%s",
                to_email,
                subject,
                len(html_body),
                (plain_text or "")[:500],
            )
            return

        _warn_if_sender_looks_unverified(sender)

        try:
            from azure.communication.email import EmailClient
        except ImportError as exc:
            raise RuntimeError(
                "Install azure-communication-email to send via Azure Communication Services."
            ) from exc

        client = EmailClient.from_connection_string(connection_string)
        message = {
            "senderAddress": sender,
            "recipients": {"to": [{"address": to_email}]},
            "content": {
                "subject": subject,
                "html": html_body,
                "plainText": plain_text or _strip_html(html_body),
            },
        }
        try:
            poller = client.begin_send(message)
            result = poller.result()
        except Exception as exc:
            raise AzureCommunicationEmailError(format_acs_send_error(exc)) from exc
        logger.info("ACS email sent message_id=%s", getattr(result, "id", result))


def _warn_if_sender_looks_unverified(sender: str) -> None:
    lowered = sender.lower()
    if lowered.endswith(".local") or "legalrentai.local" in lowered:
        raise AzureCommunicationEmailError(
            "AZURE_COMMUNICATION_SENDER_ADDRESS sigue siendo un placeholder (.local). "
            "Copia el MailFrom real desde Azure (kanban-email-service → dominio → MailFrom addresses)."
        )


def _strip_html(html: str) -> str:
    import re

    text = re.sub(r"<[^>]+>", " ", html)
    return re.sub(r"\s+", " ", text).strip()
