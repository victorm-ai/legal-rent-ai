"""Central guardrails gateway: backend → guardrails → LLM."""

from __future__ import annotations

from config.settings import Settings, get_settings
from guardrails.chat_scope import is_on_topic_chat_message
from guardrails.errors import GuardrailViolation
from guardrails.injection import detect_prompt_injection
from guardrails.lease_domain import is_lease_contract_text


class GuardrailsGateway:
    """Validates inputs before they reach LLM providers."""

    def __init__(self, settings: Settings | None = None):
        self._settings = settings or get_settings()

    @property
    def enabled(self) -> bool:
        return self._settings.guardrails_enabled

    def validate_analysis_input(
        self,
        contract_text: str,
        title: str | None = None,
    ) -> None:
        if not self.enabled:
            return
        combined = f"{title or ''}\n{contract_text}".strip()
        if not is_lease_contract_text(
            combined,
            min_lease_score=self._settings.guardrails_lease_min_score,
        ):
            raise GuardrailViolation(
                code="not_lease_contract",
                user_message=(
                    "This document does not appear to be a real property lease agreement. "
                    "LegalRentAI only analyzes lease contracts."
                ),
                detail="lease_domain_check_failed",
            )
        injection = detect_prompt_injection(combined[:20000])
        if injection:
            raise GuardrailViolation(
                code="prompt_injection",
                user_message=(
                    "The document text contains disallowed instructions. "
                    "Review the file or contact support."
                ),
                detail=injection,
            )

    def validate_chat_message(
        self,
        message: str,
        history: list[dict[str, str]] | None = None,
    ) -> None:
        if not self.enabled:
            return
        injection = detect_prompt_injection(message)
        if injection:
            raise GuardrailViolation(
                code="prompt_injection",
                user_message=(
                    "I cannot process instructions that attempt to change assistant behavior. "
                    "Ask questions about the lease contract or its analysis."
                ),
                detail=injection,
            )
        if not is_on_topic_chat_message(message, history):
            raise GuardrailViolation(
                code="off_topic",
                user_message=(
                    "I can only answer questions related to this lease contract "
                    "and its analysis (clauses, risks, parties, terms, recommendations)."
                ),
                detail="chat_scope_check_failed",
            )


def get_guardrails_gateway(settings: Settings | None = None) -> GuardrailsGateway:
    return GuardrailsGateway(settings)
