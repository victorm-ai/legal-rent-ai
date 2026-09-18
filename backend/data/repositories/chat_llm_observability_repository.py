"""Persist chat LLM observability events (app.chat_llm_call_events)."""

from __future__ import annotations

import json
from typing import Any

from config.settings import Settings, get_settings
from data.database import get_connection


class ChatLlmObservabilityRepository:
    def __init__(self, settings: Settings | None = None):
        self._settings = settings or get_settings()

    def insert_event(self, payload: dict[str, Any]) -> None:
        with get_connection(self._settings) as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                INSERT INTO app.chat_llm_call_events (
                    request_id,
                    chat_session_id,
                    event,
                    provider,
                    model,
                    tokens_in,
                    tokens_out,
                    cost_usd,
                    latency_ms,
                    cache_hit,
                    fallback_used,
                    fallback_provider,
                    finish_reason,
                    error_type,
                    error_message,
                    retry_count,
                    stream,
                    payload_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                payload.get("request_id"),
                payload.get("chat_session_id"),
                payload.get("event"),
                payload.get("provider"),
                payload.get("model"),
                payload.get("tokens_in"),
                payload.get("tokens_out"),
                payload.get("cost_usd"),
                payload.get("latency_ms"),
                1 if payload.get("cache_hit") else 0,
                1 if payload.get("fallback_used") else 0,
                payload.get("fallback_provider"),
                payload.get("finish_reason"),
                payload.get("error_type"),
                payload.get("error_message"),
                payload.get("retry_count") or 0,
                1 if payload.get("stream") else 0,
                json.dumps(payload, ensure_ascii=False),
            )
            connection.commit()
