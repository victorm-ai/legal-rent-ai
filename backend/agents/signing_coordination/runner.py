"""LangGraph ReAct agent for post-termination signing coordination."""

from __future__ import annotations

import logging

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.prebuilt import create_react_agent

from agents.signing_coordination.context import SigningCoordinationContext
from agents.signing_coordination.tools import build_signing_coordination_tools
from config.settings import Settings, get_settings
logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a signing coordination agent for Legal Rent AI (Mexico).
Use tools in this logical order:
1) get_stored_revision_comparison
2) list_lawyer_availability
3) send_signing_coordination_email

Rules:
- Write the narrative summary in English, professional and clear tone.
- Do NOT invent comparison table rows; the table is included in HTML from the send tool.
- Mention that the client, lawyer, and landlord must coordinate formal in-person signing.
- Use the lawyer's closing notes as context without altering contractual facts."""


class SigningCoordinationError(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


def _build_chat_model(settings: Settings):
    provider = settings.llm_provider.strip().lower()
    if provider == "heuristic":
        return None
    if provider in {"openai", "azure"}:
        from langchain_openai import ChatOpenAI

        if provider == "azure":
            return ChatOpenAI(
                api_key=settings.azure_openai_api_key,
                azure_endpoint=settings.azure_openai_endpoint,
                api_version=settings.azure_openai_api_version,
                azure_deployment=settings.azure_openai_deployment,
                temperature=0.2,
            )
        return ChatOpenAI(
            api_key=settings.openai_api_key or "missing-key",
            model=settings.openai_model,
            temperature=0.2,
        )
    if provider == "anthropic":
        try:
            from langchain_anthropic import ChatAnthropic
        except ImportError as exc:
            raise SigningCoordinationError(
                "Install langchain-anthropic for signing coordination with Anthropic."
            ) from exc
        return ChatAnthropic(
            api_key=settings.anthropic_api_key,
            model=settings.anthropic_model,
            temperature=0.2,
        )
    return None


def _run_deterministic(ctx: SigningCoordinationContext, settings: Settings) -> None:
    """Fallback when no chat model is configured (tests / heuristic provider)."""
    tools = {t.name: t for t in build_signing_coordination_tools(ctx, settings)}
    tools["get_stored_revision_comparison"].invoke({})
    tools["list_lawyer_availability"].invoke({})
    narrative = (
        f"Your file «{ctx.contract_title or 'contract'}» was closed administratively. "
        "We include the comparison between the original contract and the approved edited version. "
        "Please choose a time slot using the secure link to coordinate in-person signing "
        "with your lawyer and the landlord."
    )
    tools["send_signing_coordination_email"].invoke({"narrative_summary": narrative})


def run_signing_coordination_agent(ctx: SigningCoordinationContext, settings: Settings | None = None) -> None:
    settings = settings or get_settings()
    tools = build_signing_coordination_tools(ctx, settings)
    model = _build_chat_model(settings)

    if model is None:
        _run_deterministic(ctx, settings)
        if not ctx.email_sent:
            raise SigningCoordinationError("Signing coordination agent did not send email.")
        return

    agent = create_react_agent(model, tools)
    task = (
        f"Contract ID: {ctx.contract_id}\n"
        f"Title: {ctx.contract_title or 'N/A'}\n"
        f"Lawyer closing notes:\n{ctx.closure_notes}\n\n"
        "Complete coordination: load comparison from DB, list availability, and send the email."
    )
    try:
        agent.invoke(
            {
                "messages": [
                    SystemMessage(content=SYSTEM_PROMPT),
                    HumanMessage(content=task),
                ]
            }
        )
    except Exception as exc:
        logger.exception("Signing coordination LangGraph agent failed")
        from notification.acs_errors import format_acs_send_error

        detail = format_acs_send_error(exc)
        raise SigningCoordinationError(detail) from exc

    if not ctx.email_sent:
        raise SigningCoordinationError(
            "Signing coordination agent finished without calling send_signing_coordination_email."
        )
