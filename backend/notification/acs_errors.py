"""User-facing ACS Email error messages."""

from __future__ import annotations


def format_acs_send_error(exc: BaseException) -> str:
    text = str(exc)
    if "DomainNotLinked" in text:
        return (
            "Azure Email: the domain is not linked to the "
            "'kanban-communication-service' resource. In Azure Portal: Communication Services > "
            "Email > Domains > Connect domain (from 'kanban-email-service'). "
            "MailFrom in .env should already be the azurecomm.net address; only the link is missing. "
            "Guide: docs/deployment/fix-domain-not-linked.md"
        )
    if "InvalidSender" in text or "SenderAddress" in text:
        return (
            "Azure Email: invalid sender. Use the verified ACS MailFrom address "
            "(donotreply@….azurecomm.net), not a fictional domain."
        )
    return text
