"""LangGraph tools for signing coordination (function calling)."""

from __future__ import annotations

import json
from typing import Any

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from agents.signing_coordination.context import SigningCoordinationContext
from agents.signing_coordination.html_email import build_signing_coordination_html
from config.settings import Settings, get_settings
from notification.azure_communication_email import AzureCommunicationEmailSender
from scheduling.availability import generate_signing_slots
from services.comparison_service import ComparisonService


class EmptyInput(BaseModel):
    """Tool with no parameters."""


class SendEmailInput(BaseModel):
    narrative_summary: str = Field(
        description=(
            "Narrative summary in English for the client. "
            "Do not include table rows; only context and next steps."
        )
    )


def _load_comparison_payload(contract_id: str, settings: Settings) -> dict[str, Any]:
    service = ComparisonService(settings=settings)
    comparison = service._comparisons.get_latest_self_comparison(contract_id)
    if comparison is None:
        raise ValueError(
            "No original-vs-edited comparison is saved. "
            "The client must generate it before closure."
        )
    changes = service._comparisons.list_changes(comparison.id)
    rows = service._revision_comparison_rows(contract_id)
    return {
        "comparison_id": comparison.id,
        "summary": comparison.summary,
        "risk_delta": comparison.risk_delta,
        "rows": rows,
        "changes": [
            {
                "change_type": c.change_type,
                "category": c.category,
                "description": c.description,
                "old_value": c.old_value,
                "new_value": c.new_value,
            }
            for c in changes
        ],
    }


def build_signing_coordination_tools(
    ctx: SigningCoordinationContext,
    settings: Settings | None = None,
) -> list[StructuredTool]:
    settings = settings or get_settings()

    def get_stored_revision_comparison() -> str:
        """Load the latest original-vs-edited comparison JSON from the database."""
        payload = _load_comparison_payload(ctx.contract_id, settings)
        ctx.comparison_payload = payload
        return json.dumps(payload, ensure_ascii=False)

    def list_lawyer_availability() -> str:
        """List simulated lawyer availability slots (Mon–Fri 09:00–18:00 CDMX, 45 min)."""
        slots = generate_signing_slots(
            slot_minutes=settings.signing_schedule_slot_minutes,
            weeks_ahead=settings.signing_schedule_weeks_ahead,
        )
        ctx.availability_slots = slots
        preview = slots[:40]
        return json.dumps({"slot_count": len(slots), "slots": preview}, ensure_ascii=False)

    def send_signing_coordination_email(narrative_summary: str) -> str:
        """Send the coordination email to the client via Azure Communication Services."""
        if ctx.comparison_payload is None:
            raise ValueError("Call get_stored_revision_comparison before sending email.")
        if not ctx.availability_slots:
            raise ValueError("Call list_lawyer_availability before sending email.")

        narrative = (narrative_summary or "").strip()
        if not narrative:
            raise ValueError("narrative_summary is required.")

        ctx.narrative_summary = narrative
        html_body = build_signing_coordination_html(
            contract_title=ctx.contract_title,
            narrative_summary=narrative,
            comparison=ctx.comparison_payload,
            schedule_url=ctx.schedule_url,
            closure_notes=ctx.closure_notes,
        )
        subject = f"Legal Rent AI — Signing coordination: {ctx.contract_title or 'Contract'}"
        AzureCommunicationEmailSender(settings).send_html(
            to_email=ctx.client_email,
            subject=subject,
            html_body=html_body,
            plain_text=narrative,
        )
        ctx.email_sent = True
        return json.dumps({"status": "sent", "to": ctx.client_email}, ensure_ascii=False)

    return [
        StructuredTool.from_function(
            func=get_stored_revision_comparison,
            name="get_stored_revision_comparison",
            description="Load the persisted original-vs-edited comparison from SQL Server.",
            args_schema=EmptyInput,
        ),
        StructuredTool.from_function(
            func=list_lawyer_availability,
            name="list_lawyer_availability",
            description="List simulated lawyer availability slots for signing coordination.",
            args_schema=EmptyInput,
        ),
        StructuredTool.from_function(
            func=send_signing_coordination_email,
            name="send_signing_coordination_email",
            description="Send HTML email to the client with comparison table and scheduling link.",
            args_schema=SendEmailInput,
        ),
    ]
