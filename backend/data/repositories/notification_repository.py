"""SQL Server repository for app.notifications (RF-50, RF-51)."""

from datetime import datetime
from typing import List
from uuid import UUID

from config.settings import Settings, get_settings
from data.delivery_dto import NotificationDTO
from data.database import get_connection


class NotificationRepository:
    def __init__(self, settings: Settings | None = None):
        self._settings = settings or get_settings()

    def create(
        self,
        analysis_id: str,
        user_id: str,
        lawyer_email: str,
        decision: str,
        status: str = "pending",
    ) -> NotificationDTO:
        with get_connection(self._settings) as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                INSERT INTO app.notifications (analysis_id, user_id, lawyer_email, decision, status)
                OUTPUT INSERTED.id, INSERTED.analysis_id, INSERTED.user_id,
                       INSERTED.lawyer_email, INSERTED.decision, INSERTED.status,
                       INSERTED.sent_at, INSERTED.created_at
                VALUES (?, ?, ?, ?, ?)
                """,
                analysis_id,
                user_id,
                lawyer_email,
                decision,
                status,
            )
            row = cursor.fetchone()
            connection.commit()
        return self._row_to_dto(row)

    def mark_sent(self, notification_id: str) -> NotificationDTO | None:
        with get_connection(self._settings) as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                UPDATE app.notifications
                SET status = N'sent', sent_at = SYSUTCDATETIME()
                OUTPUT INSERTED.id, INSERTED.analysis_id, INSERTED.user_id,
                       INSERTED.lawyer_email, INSERTED.decision, INSERTED.status,
                       INSERTED.sent_at, INSERTED.created_at
                WHERE id = ?
                """,
                notification_id,
            )
            row = cursor.fetchone()
            connection.commit()
        return self._row_to_dto(row) if row else None

    def mark_failed(self, notification_id: str) -> None:
        with get_connection(self._settings) as connection:
            cursor = connection.cursor()
            cursor.execute(
                "UPDATE app.notifications SET status = N'failed' WHERE id = ?",
                notification_id,
            )
            connection.commit()

    def list_by_analysis(self, analysis_id: str) -> List[NotificationDTO]:
        with get_connection(self._settings) as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                SELECT id, analysis_id, user_id, lawyer_email, decision, status, sent_at, created_at
                FROM app.notifications
                WHERE analysis_id = ?
                ORDER BY created_at DESC
                """,
                analysis_id,
            )
            rows = cursor.fetchall()
        return [self._row_to_dto(row) for row in rows]

    @staticmethod
    def _row_to_dto(row) -> NotificationDTO:
        return NotificationDTO(
            id=str(row[0]) if isinstance(row[0], UUID) else row[0],
            analysis_id=str(row[1]) if isinstance(row[1], UUID) else row[1],
            user_id=str(row[2]) if isinstance(row[2], UUID) else row[2],
            lawyer_email=row[3],
            decision=row[4],
            status=row[5],
            sent_at=row[6],
            created_at=row[7],
        )
