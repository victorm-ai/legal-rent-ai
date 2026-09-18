"""SQL Server repository for app.review_messages (RF-50, RF-51)."""

from typing import List
from uuid import UUID

from config.settings import Settings, get_settings
from data.delivery_dto import ReviewMessageDTO
from data.database import get_connection


class ReviewMessageRepository:
    def __init__(self, settings: Settings | None = None):
        self._settings = settings or get_settings()

    def create(self, analysis_id: str, user_id: str, content: str) -> ReviewMessageDTO:
        with get_connection(self._settings) as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                INSERT INTO app.review_messages (analysis_id, user_id, content)
                OUTPUT INSERTED.id, INSERTED.analysis_id, INSERTED.user_id,
                       INSERTED.content, INSERTED.created_at
                VALUES (?, ?, ?)
                """,
                analysis_id,
                user_id,
                content,
            )
            row = cursor.fetchone()
            connection.commit()
        message = self._row_to_dto(row)
        return self.get_by_id(message.id) or message

    def get_by_id(self, message_id: str) -> ReviewMessageDTO | None:
        with get_connection(self._settings) as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                SELECT
                    rm.id,
                    rm.analysis_id,
                    rm.user_id,
                    u.name,
                    u.email,
                    u.role_id,
                    rm.content,
                    rm.created_at
                FROM app.review_messages rm
                INNER JOIN app.users u ON u.id = rm.user_id
                WHERE rm.id = ?
                """,
                message_id,
            )
            row = cursor.fetchone()
        return self._joined_row_to_dto(row) if row else None

    def list_by_analysis(self, analysis_id: str) -> List[ReviewMessageDTO]:
        with get_connection(self._settings) as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                SELECT
                    rm.id,
                    rm.analysis_id,
                    rm.user_id,
                    u.name,
                    u.email,
                    u.role_id,
                    rm.content,
                    rm.created_at
                FROM app.review_messages rm
                INNER JOIN app.users u ON u.id = rm.user_id
                WHERE rm.analysis_id = ?
                ORDER BY rm.created_at ASC
                """,
                analysis_id,
            )
            rows = cursor.fetchall()
        return [self._joined_row_to_dto(row) for row in rows]

    def list_by_contract(self, contract_id: str) -> List[ReviewMessageDTO]:
        with get_connection(self._settings) as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                SELECT
                    rm.id,
                    rm.analysis_id,
                    rm.user_id,
                    u.name,
                    u.email,
                    u.role_id,
                    rm.content,
                    rm.created_at
                FROM app.review_messages rm
                INNER JOIN app.analyses a ON a.id = rm.analysis_id
                INNER JOIN app.users u ON u.id = rm.user_id
                WHERE a.contract_id = ?
                ORDER BY rm.created_at ASC
                """,
                contract_id,
            )
            rows = cursor.fetchall()
        return [self._joined_row_to_dto(row) for row in rows]

    @staticmethod
    def _row_to_dto(row) -> ReviewMessageDTO:
        return ReviewMessageDTO(
            id=ReviewMessageRepository._normalize_id(row[0]),
            analysis_id=ReviewMessageRepository._normalize_id(row[1]),
            user_id=ReviewMessageRepository._normalize_id(row[2]),
            author_name="",
            author_email="",
            author_role="client",
            content=row[3],
            created_at=row[4],
        )

    @staticmethod
    def _joined_row_to_dto(row) -> ReviewMessageDTO:
        role_id = row[5]
        role_map = {1: "lawyer", 2: "client"}
        return ReviewMessageDTO(
            id=ReviewMessageRepository._normalize_id(row[0]),
            analysis_id=ReviewMessageRepository._normalize_id(row[1]),
            user_id=ReviewMessageRepository._normalize_id(row[2]),
            author_name=row[3] or row[4],
            author_email=row[4],
            author_role=role_map.get(role_id, "client"),
            content=row[6],
            created_at=row[7],
        )

    @staticmethod
    def _normalize_id(value) -> str:
        return str(value) if isinstance(value, UUID) else value
