"""User-facing ACS Email error messages."""

from __future__ import annotations


def format_acs_send_error(exc: BaseException) -> str:
    text = str(exc)
    if "DomainNotLinked" in text:
        return (
            "Azure Email: el dominio no está vinculado al recurso "
            "'kanban-communication-service'. En Portal Azure: Communication Services > "
            "Email > Domains > Connect domain (desde 'kanban-email-service'). "
            "El MailFrom en .env ya debe ser el de azurecomm.net; falta solo el enlace. "
            "Guía: docs/deployment/fix-domain-not-linked.md"
        )
    if "InvalidSender" in text or "SenderAddress" in text:
        return (
            "Azure Email: remitente inválido. Usa el MailFrom verificado en ACS "
            "(donotreply@….azurecomm.net), no un dominio ficticio."
        )
    return text
