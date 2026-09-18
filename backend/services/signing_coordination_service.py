"""Orchestrates signing coordination LangGraph agent after contract termination."""

from __future__ import annotations

from urllib.parse import quote

from agents.signing_coordination.context import SigningCoordinationContext
from agents.signing_coordination.runner import SigningCoordinationError
from ai.runtime import AIRuntime
from auth.signing_schedule_token import SigningScheduleTokenService
from config.settings import Settings, get_settings
from data.repositories.contract_repository import ContractRepository
from data.repositories.user_repository import UserRepository


class SigningCoordinationService:
    def __init__(self, settings: Settings | None = None, ai_runtime: AIRuntime | None = None):
        self._settings = settings or get_settings()
        self._ai = ai_runtime or AIRuntime(self._settings)
        self._contracts = ContractRepository(self._settings)
        self._users = UserRepository(self._settings)
        self._tokens = SigningScheduleTokenService(self._settings.secret_key)

    def run_for_terminated_contract(self, contract_id: str, closure_notes: str) -> None:
        contract = self._contracts.get_by_id(contract_id)
        if contract is None:
            raise SigningCoordinationError("Contract not found")

        client = self._users.get_by_id(contract.user_id)
        if client is None:
            raise SigningCoordinationError("Contract owner not found")

        schedule_token = self._tokens.create(
            client_user_id=client.id,
            contract_id=contract_id,
        )
        base = self._settings.frontend_base_url.rstrip("/")
        schedule_url = f"{base}/schedule-signing?token={quote(schedule_token)}"

        ctx = SigningCoordinationContext(
            contract_id=contract_id,
            client_user_id=client.id,
            client_email=client.email,
            contract_title=contract.title,
            closure_notes=closure_notes.strip(),
            schedule_url=schedule_url,
        )
        self._ai.run_signing_coordination(ctx)
