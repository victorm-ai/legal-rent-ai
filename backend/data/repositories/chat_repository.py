"""SQL Server repository for app.chat_sessions and app.chat_messages (RF-41–RF-44)."""

import json
from typing import List
from uuid import UUID

from config.settings import Settings, get_settings
from data.delivery_dto import ChatMessageDTO, ChatSessionDTO
from data.database import get_connection


class ChatRepository:
    def __init__(self, settings: Settings | None = None):
        self._settings = settings or get_settings()

    def get_session_for_analysis(
        self,
        contract_id: str,
        user_id: str,
        analysis_id: str,
    ) -> ChatSessionDTO | None:
        with get_connection(self._settings) as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                SELECT TOP 1 id, contract_id, user_id, analysis_id, created_at
                FROM app.chat_sessions
                WHERE contract_id = ? AND user_id = ? AND analysis_id = ?
                ORDER BY created_at DESC
                """,
                contract_id,
                user_id,
                analysis_id,
            )
            row = cursor.fetchone()
        if row is None:
            return None
        return ChatSessionDTO(
            id=self._normalize_id(row[0]),
            contract_id=self._normalize_id(row[1]),
            user_id=self._normalize_id(row[2]),
            analysis_id=self._normalize_id(row[3]),
            created_at=row[4],
        )

    def create_session(
        self,
        contract_id: str,
        user_id: str,
        analysis_id: str,
    ) -> ChatSessionDTO:
        with get_connection(self._settings) as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                INSERT INTO app.chat_sessions (contract_id, user_id, analysis_id)
                OUTPUT INSERTED.id, INSERTED.contract_id, INSERTED.user_id,
                       INSERTED.analysis_id, INSERTED.created_at
                VALUES (?, ?, ?)
                """,
                contract_id,
                user_id,
                analysis_id,
            )
            row = cursor.fetchone()
            connection.commit()
        return ChatSessionDTO(
            id=self._normalize_id(row[0]),
            contract_id=self._normalize_id(row[1]),
            user_id=self._normalize_id(row[2]),
            analysis_id=self._normalize_id(row[3]),
            created_at=row[4],
        )

    def get_session(self, session_id: str) -> ChatSessionDTO | None:
        with get_connection(self._settings) as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                SELECT id, contract_id, user_id, analysis_id, created_at
                FROM app.chat_sessions WHERE id = ?
                """,
                session_id,
            )
            row = cursor.fetchone()
        if row is None:
            return None
        return ChatSessionDTO(
            id=self._normalize_id(row[0]),
            contract_id=self._normalize_id(row[1]),
            user_id=self._normalize_id(row[2]),
            analysis_id=self._normalize_id(row[3]),
            created_at=row[4],
        )

    def list_sessions_by_contract(self, contract_id: str, user_id: str) -> List[ChatSessionDTO]:
        with get_connection(self._settings) as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                SELECT id, contract_id, user_id, analysis_id, created_at
                FROM app.chat_sessions
                WHERE contract_id = ? AND user_id = ?
                ORDER BY created_at DESC
                """,
                contract_id,
                user_id,
            )
            rows = cursor.fetchall()
        return [
            ChatSessionDTO(
                id=self._normalize_id(row[0]),
                contract_id=self._normalize_id(row[1]),
                user_id=self._normalize_id(row[2]),
                analysis_id=self._normalize_id(row[3]),
                created_at=row[4],
            )
            for row in rows
        ]

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        references: list | None = None,
    ) -> ChatMessageDTO:
        refs_json = json.dumps(references or [], ensure_ascii=False)
        with get_connection(self._settings) as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                INSERT INTO app.chat_messages (session_id, role, content, references_json)
                OUTPUT INSERTED.id, INSERTED.session_id, INSERTED.role,
                       INSERTED.content, INSERTED.references_json, INSERTED.created_at
                VALUES (?, ?, ?, ?)
                """,
                session_id,
                role,
                content,
                refs_json,
            )
            row = cursor.fetchone()
            connection.commit()
        return self._row_to_message(row)

    def list_messages(self, session_id: str) -> List[ChatMessageDTO]:
        with get_connection(self._settings) as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                SELECT id, session_id, role, content, references_json, created_at
                FROM app.chat_messages
                WHERE session_id = ?
                ORDER BY created_at
                """,
                session_id,
            )
            rows = cursor.fetchall()
        return [self._row_to_message(row) for row in rows]

    def _row_to_message(self, row) -> ChatMessageDTO:
        refs_raw = row[4]
        references = json.loads(refs_raw) if refs_raw else []
        return ChatMessageDTO(
            id=self._normalize_id(row[0]),
            session_id=self._normalize_id(row[1]),
            role=row[2],
            content=row[3],
            references=references,
            created_at=row[5],
        )

    @staticmethod
    def _normalize_id(value) -> str:
        return str(value) if isinstance(value, UUID) else value
