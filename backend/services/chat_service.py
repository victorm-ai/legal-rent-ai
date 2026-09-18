"""Contract chat business logic (RF-41–RF-45)."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from config.settings import Settings, get_settings
from ai.runtime import AIRuntime
from guardrails.errors import GuardrailViolation
from data.delivery_dto import ChatMessageDTO, ChatSessionDTO
from data.repositories.chat_repository import ChatRepository
from data.repositories.contract_document_repository import ContractDocumentRepository
from domain.entities import Role
from observability.chat_llm_tracker import ChatObservabilityContext
from services.analysis_service import AnalysisNotFoundError, AnalysisService
from services.comparison_service import EDITED_ANALYSIS_DOCUMENT_SCOPE, ComparisonService
from services.contract_service import ContractAccessError, ContractNotFoundError


class ChatSessionNotFoundError(Exception):
    def __init__(self, message: str = "Chat session not found"):
        super().__init__(message)
        self.message = message


class ChatService:
    def __init__(
        self,
        analysis_service: AnalysisService | None = None,
        chat_repository: ChatRepository | None = None,
        document_repository: ContractDocumentRepository | None = None,
        ai_runtime: AIRuntime | None = None,
        comparison_service: ComparisonService | None = None,
        settings: Settings | None = None,
    ):
        self._settings = settings or get_settings()
        self._analysis = analysis_service or AnalysisService(settings=self._settings)
        self._chat = chat_repository or ChatRepository(self._settings)
        self._documents = document_repository or ContractDocumentRepository(self._settings)
        self._ai = ai_runtime or AIRuntime(self._settings)
        self._comparisons = comparison_service or ComparisonService(settings=self._settings)

    def create_session(
        self,
        current_user: dict,
        contract_id: str,
        analysis_id: str,
    ) -> ChatSessionDTO:
        analysis = self._analysis.get_analysis(current_user, analysis_id)
        if analysis.contract_id != contract_id:
            raise ValueError("Analysis does not belong to this contract")

        existing = self._chat.get_session_for_analysis(
            contract_id=contract_id,
            user_id=current_user["user_id"],
            analysis_id=analysis_id,
        )
        if existing is not None:
            return existing

        return self._chat.create_session(
            contract_id=contract_id,
            user_id=current_user["user_id"],
            analysis_id=analysis_id,
        )

    def list_sessions(self, current_user: dict, contract_id: str) -> list[ChatSessionDTO]:
        self._analysis._get_accessible_contract(current_user, contract_id)
        return self._chat.list_sessions_by_contract(contract_id, current_user["user_id"])

    def list_messages(self, current_user: dict, session_id: str) -> list[ChatMessageDTO]:
        session = self._get_owned_session(current_user, session_id)
        return self._chat.list_messages(session.id)

    def _prepare_chat_turn(
        self,
        current_user: dict,
        session_id: str,
        content: str,
        *,
        persist_user_message: bool,
    ) -> tuple[ChatSessionDTO, str, str, dict[str, Any], list[dict[str, str]]]:
        session = self._get_owned_session(current_user, session_id)
        content = content.strip()
        if not content:
            raise ValueError("Message content is required")

        history = [
            {"role": msg.role, "content": msg.content}
            for msg in self._chat.list_messages(session.id)
            if msg.role in {"user", "assistant"}
        ]
        try:
            self._ai.validate_chat_message(content, history)
        except GuardrailViolation as exc:
            raise ValueError(exc.user_message) from exc

        if persist_user_message:
            self._chat.add_message(session.id, "user", content)

        analysis = self._analysis.get_analysis(current_user, session.analysis_id)
        document_scope = getattr(analysis, "document_scope", None) or "original"
        contract_text = self._documents.get_extracted_text_for_analysis_scope(
            session.contract_id,
            document_scope,
        )
        context = self._build_chat_context(analysis, session.contract_id)
        comparison_text = self._format_revision_comparison_text(context.get("revision_comparison"))
        if comparison_text:
            contract_text = f"{comparison_text}\n\n{contract_text}".strip()
        history = [
            {"role": msg.role, "content": msg.content}
            for msg in self._chat.list_messages(session.id)
            if msg.role in {"user", "assistant"}
        ]
        return session, content, contract_text, context, history

    def send_message(
        self,
        current_user: dict,
        session_id: str,
        content: str,
    ) -> ChatMessageDTO:
        _session, question, contract_text, context, history = self._prepare_chat_turn(
            current_user,
            session_id,
            content,
            persist_user_message=True,
        )
        answer = self._ai.chat_answer(
            question,
            contract_text,
            context,
            history,
            observability=ChatObservabilityContext(_session.id, stream=False),
        )
        return self._chat.add_message(
            _session.id,
            "assistant",
            answer["content"],
            answer.get("references") or [],
        )

    def stream_message(
        self,
        current_user: dict,
        session_id: str,
        content: str,
    ) -> Iterator[dict[str, Any]]:
        session, question, contract_text, context, history = self._prepare_chat_turn(
            current_user,
            session_id,
            content,
            persist_user_message=True,
        )
        obs = ChatObservabilityContext(session.id, stream=True)
        for event in self._ai.chat_stream(
            question,
            contract_text,
            context,
            history,
            observability=obs,
        ):
            if event.get("type") != "done":
                yield event
                continue
            saved = self._chat.add_message(
                session.id,
                "assistant",
                event["content"],
                event.get("references") or [],
            )
            yield {
                "type": "done",
                "message": {
                    "id": saved.id,
                    "role": saved.role,
                    "content": saved.content,
                    "references": saved.references,
                    "created_at": saved.created_at.isoformat() if saved.created_at else None,
                },
            }

    def get_suggestions(self, current_user: dict, session_id: str) -> list[str]:
        session = self._get_owned_session(current_user, session_id)
        analysis = self._analysis.get_analysis(current_user, session.analysis_id)
        context = self._build_chat_context(analysis, session.contract_id)
        return self._llm.suggest_questions(context)

    def _get_owned_session(self, current_user: dict, session_id: str) -> ChatSessionDTO:
        session = self._chat.get_session(session_id)
        if session is None:
            raise ChatSessionNotFoundError()
        if session.user_id != current_user["user_id"]:
            role = current_user["role"]
            if role != Role.LAWYER:
                raise ContractAccessError()
        self._analysis._get_accessible_contract(current_user, session.contract_id)
        return session

    def _build_chat_context(self, analysis, contract_id: str) -> dict:
        context = self._build_analysis_context(analysis)
        document_scope = getattr(analysis, "document_scope", None) or "original"
        if document_scope != EDITED_ANALYSIS_DOCUMENT_SCOPE:
            return context
        revision_comparison = self._comparisons.get_revision_comparison_context(contract_id)
        if revision_comparison:
            context["revision_comparison"] = revision_comparison
        return context

    @staticmethod
    def _format_revision_comparison_text(revision_comparison: dict | None) -> str:
        if not revision_comparison:
            return ""
        rows = revision_comparison.get("rows") or []
        if not rows:
            return ""
        lines = [
            "Tabla comparativa entre contrato original y contrato editado:",
            "Dato | Original | Editado | Diferencia",
        ]
        for row in rows:
            original = (row.get("original_value") or "—").replace("\n", " ")
            new_value = (row.get("new_value") or "—").replace("\n", " ")
            difference = row.get("difference") or "—"
            item_key = row.get("item_key") or "item"
            lines.append(f"{item_key} | {original} | {new_value} | {difference}")
        summary = revision_comparison.get("summary")
        if summary:
            lines.insert(1, f"Resumen: {summary}")
        return "\n".join(lines)

    @staticmethod
    def _build_analysis_context(analysis) -> dict:
        return {
            "summary_executive": analysis.summary_executive,
            "general_risk": analysis.general_risk,
            "extracted_fields": [
                {
                    "field_name": f.field_name,
                    "field_value": f.field_value,
                    "confidence": f.confidence,
                }
                for f in analysis.extracted_fields
            ],
            "clauses": [
                {
                    "id": c.id,
                    "category": c.category,
                    "section": c.section,
                    "page": c.page,
                    "text": c.text[:800],
                }
                for c in analysis.clauses
            ],
            "findings": [
                {
                    "id": f.id,
                    "finding_type": f.finding_type,
                    "severity": f.severity,
                    "title": f.title,
                    "description": f.description,
                    "recommendation": f.recommendation,
                    "evidence_text": f.evidence_text,
                    "source_law": f.source_law,
                    "legal_basis": f.legal_basis,
                    "legal_citations": [
                        {"law_code": c.law_code, "article": c.article, "excerpt": c.excerpt}
                        for c in f.legal_citations
                    ],
                }
                for f in analysis.findings
            ],
        }
