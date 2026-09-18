"""Mutable runtime context shared by signing-coordination tools."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SigningCoordinationContext:
    contract_id: str
    client_user_id: str
    client_email: str
    contract_title: str | None
    closure_notes: str
    schedule_url: str
    lawyer_name: str | None = None

    comparison_payload: dict[str, Any] | None = None
    availability_slots: list[str] = field(default_factory=list)
    narrative_summary: str | None = None
    email_sent: bool = False
