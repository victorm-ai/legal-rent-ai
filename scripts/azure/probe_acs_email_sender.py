#!/usr/bin/env python
"""Probe ACS Email send and print actionable errors (local dev helper)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from config.settings import get_settings  # noqa: E402
from notification.azure_communication_email import AzureCommunicationEmailSender  # noqa: E402


def main() -> int:
    settings = get_settings()
    to_email = sys.argv[1] if len(sys.argv) > 1 else "code.zemoreno@gmail.com"
    sender = AzureCommunicationEmailSender(settings)
    try:
        sender.send_html(
            to_email=to_email,
            subject="Legal Rent AI — prueba ACS",
            html_body="<p>Correo de prueba desde Legal Rent AI.</p>",
            plain_text="Correo de prueba desde Legal Rent AI.",
        )
    except Exception as exc:
        from notification.acs_errors import format_acs_send_error

        print(f"ERROR: {format_acs_send_error(exc)}")
        print("\nGuía: docs/deployment/fix-domain-not-linked.md")
        return 1
    print(f"OK: mensaje enviado hacia {to_email}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
