"""Unified chat LLM observability events (structlog + SQL Server)."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import structlog

from config.settings import Settings, get_settings
from data.repositories.chat_llm_observability_repository import ChatLlmObservabilityRepository

_log = structlog.get_logger("observability.chat_llm")


@dataclass(frozen=True)
class ChatObservabilityContext:
    chat_session_id: str
    stream: bool = False


class ChatLlmCallTracker:
    """Emit llm_call_started | llm_call_completed | llm_call_failed for one chat turn."""

    def __init__(
        self,
        context: ChatObservabilityContext,
        settings: Settings | None = None,
        repository: ChatLlmObservabilityRepository | None = None,
    ):
        self._context = context
        self._settings = settings or get_settings()
        self._repo = repository or ChatLlmObservabilityRepository(self._settings)
        self.request_id = str(uuid.uuid4())
        self._started_at: float | None = None

    def started(self, provider: str, model: str) -> dict[str, Any]:
        self._started_at = time.perf_counter()
        payload = self._build_payload(
            event="llm_call_started",
            provider=provider,
            model=model,
        )
        self._emit(payload)
        return payload

    def completed(
        self,
        *,
        provider: str,
        model: str,
        tokens_in: int | None = None,
        tokens_out: int | None = None,
        cost_usd: float | None = None,
        finish_reason: str | None = None,
        cache_hit: bool = False,
        fallback_used: bool = False,
        fallback_provider: str | None = None,
        retry_count: int = 0,
    ) -> dict[str, Any]:
        payload = self._build_payload(
            event="llm_call_completed",
            provider=provider,
            model=model,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost_usd=cost_usd,
            finish_reason=finish_reason,
            cache_hit=cache_hit,
            fallback_used=fallback_used,
            fallback_provider=fallback_provider,
            retry_count=retry_count,
        )
        self._emit(payload)
        return payload

    def failed(
        self,
        *,
        provider: str,
        model: str,
        error: BaseException,
        retry_count: int = 0,
        tokens_in: int | None = None,
        tokens_out: int | None = None,
    ) -> dict[str, Any]:
        payload = self._build_payload(
            event="llm_call_failed",
            provider=provider,
            model=model,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            error_type=type(error).__name__,
            error_message=str(error),
            retry_count=retry_count,
        )
        self._emit(payload)
        return payload

    def _latency_ms(self) -> int | None:
        if self._started_at is None:
            return None
        return int((time.perf_counter() - self._started_at) * 1000)

    def _build_payload(
        self,
        *,
        event: str,
        provider: str,
        model: str,
        tokens_in: int | None = None,
        tokens_out: int | None = None,
        cost_usd: float | None = None,
        finish_reason: str | None = None,
        cache_hit: bool = False,
        fallback_used: bool = False,
        fallback_provider: str | None = None,
        error_type: str | None = None,
        error_message: str | None = None,
        retry_count: int = 0,
    ) -> dict[str, Any]:
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": event,
            "request_id": self.request_id,
            "chat_session_id": self._context.chat_session_id,
            "stream": self._context.stream,
            "provider": provider,
            "model": model,
            "tokens_in": tokens_in if tokens_in is not None else 0,
            "tokens_out": tokens_out if tokens_out is not None else 0,
            "cost_usd": cost_usd if cost_usd is not None else 0.0,
            "latency_ms": self._latency_ms() if event != "llm_call_started" else 0,
            "cache_hit": cache_hit,
            "fallback_used": fallback_used,
            "fallback_provider": fallback_provider,
            "finish_reason": finish_reason,
            "error_type": error_type,
            "error_message": error_message,
            "retry_count": retry_count,
        }

    def _emit(self, payload: dict[str, Any]) -> None:
        log_fields = {key: value for key, value in payload.items() if key != "event"}
        log_fields["llm_event"] = payload["event"]
        _log.info("chat_llm_observability", **log_fields)
        try:
            self._repo.insert_event(payload)
        except Exception:
            _log.exception(
                "chat_llm_event_persist_failed",
                request_id=payload.get("request_id"),
                event=payload.get("event"),
            )
