"""Tracks per-user read cursors for client–lawyer review chat."""

from __future__ import annotations

from typing import Dict, List
from uuid import UUID

from config.settings import Settings, get_settings
from data.database import get_connection


class ReviewMessageReadRepository:
    def __init__(self, settings: Settings | None = None):
        self._settings = settings or get_settings()

    def mark_contract_read(self, user_id: str, contract_id: str) -> None:
        with get_connection(self._settings) as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                MERGE app.review_message_read_cursors AS target
                USING (SELECT ? AS user_id, ? AS contract_id) AS source
                ON target.user_id = source.user_id AND target.contract_id = source.contract_id
                WHEN MATCHED THEN
                    UPDATE SET last_read_at = SYSUTCDATETIME()
                WHEN NOT MATCHED THEN
                    INSERT (user_id, contract_id, last_read_at)
                    VALUES (source.user_id, source.contract_id, SYSUTCDATETIME());
                """,
                user_id,
                contract_id,
            )
            connection.commit()

    def unread_counts_by_contract(self, user_id: str, contract_ids: List[str]) -> Dict[str, int]:
        if not contract_ids:
            return {}

        placeholders = ",".join("?" for _ in contract_ids)
        params: list = [user_id, *contract_ids, user_id]

        with get_connection(self._settings) as connection:
            cursor = connection.cursor()
            cursor.execute(
                f"""
                SELECT
                    c.id,
                    COUNT(rm.id) AS unread_count
                FROM app.contracts c
                INNER JOIN app.analyses a ON a.contract_id = c.id
                INNER JOIN app.review_messages rm ON rm.analysis_id = a.id
                LEFT JOIN app.review_message_read_cursors rc
                    ON rc.contract_id = c.id AND rc.user_id = ?
                WHERE c.id IN ({placeholders})
                  AND rm.user_id <> ?
                  AND rm.created_at > COALESCE(rc.last_read_at, '1970-01-01T00:00:00')
                GROUP BY c.id
                """,
                params,
            )
            rows = cursor.fetchall()

        counts = {
            self._normalize_id(row[0]).lower(): int(row[1])
            for row in rows
        }
        return {
            contract_id: counts.get(self._normalize_id(contract_id).lower(), 0)
            for contract_id in contract_ids
        }

    @staticmethod
    def _normalize_id(value) -> str:
        if isinstance(value, UUID):
            return str(value).lower()
        return str(value).lower()
