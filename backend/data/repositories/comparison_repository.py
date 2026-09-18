"""SQL Server repository for contract comparisons (RF-59)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from config.settings import Settings, get_settings
from data.database import get_connection


@dataclass
class ComparisonDTO:
    id: str
    base_contract_id: str
    compare_contract_id: str
    created_by: str
    summary: str | None
    risk_delta: str | None
    created_at: Any


@dataclass
class ComparisonChangeDTO:
    id: str
    comparison_id: str
    change_type: str
    category: str | None
    description: str | None
    old_value: str | None
    new_value: str | None


class ComparisonRepository:
    def __init__(self, settings: Settings | None = None):
        self._settings = settings or get_settings()

    def create(
        self,
        base_contract_id: str,
        compare_contract_id: str,
        created_by: str,
        summary: str | None,
        risk_delta: str | None,
        changes: list[dict[str, Any]],
    ) -> ComparisonDTO:
        with get_connection(self._settings) as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                INSERT INTO app.contract_comparisons (
                    base_contract_id, compare_contract_id, created_by, summary, risk_delta
                )
                OUTPUT
                    INSERTED.id,
                    INSERTED.base_contract_id,
                    INSERTED.compare_contract_id,
                    INSERTED.created_by,
                    INSERTED.summary,
                    INSERTED.risk_delta,
                    INSERTED.created_at
                VALUES (?, ?, ?, ?, ?)
                """,
                base_contract_id,
                compare_contract_id,
                created_by,
                summary,
                risk_delta,
            )
            row = cursor.fetchone()
            comparison_id = self._normalize_id(row[0])

            for change in changes:
                cursor.execute(
                    """
                    INSERT INTO app.comparison_changes (
                        comparison_id, change_type, category, description, old_value, new_value
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    comparison_id,
                    change["change_type"],
                    change.get("category"),
                    change.get("description"),
                    change.get("old_value"),
                    change.get("new_value"),
                )
            connection.commit()

        return ComparisonDTO(
            id=comparison_id,
            base_contract_id=self._normalize_id(row[1]),
            compare_contract_id=self._normalize_id(row[2]),
            created_by=self._normalize_id(row[3]),
            summary=row[4],
            risk_delta=row[5],
            created_at=row[6],
        )

    def get_by_id(self, comparison_id: str) -> ComparisonDTO | None:
        with get_connection(self._settings) as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                SELECT id, base_contract_id, compare_contract_id, created_by, summary, risk_delta, created_at
                FROM app.contract_comparisons
                WHERE id = ?
                """,
                comparison_id,
            )
            row = cursor.fetchone()
        if row is None:
            return None
        return ComparisonDTO(
            id=self._normalize_id(row[0]),
            base_contract_id=self._normalize_id(row[1]),
            compare_contract_id=self._normalize_id(row[2]),
            created_by=self._normalize_id(row[3]),
            summary=row[4],
            risk_delta=row[5],
            created_at=row[6],
        )

    def get_latest_self_comparison(self, contract_id: str) -> ComparisonDTO | None:
        with get_connection(self._settings) as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                SELECT TOP 1
                    id, base_contract_id, compare_contract_id, created_by, summary, risk_delta, created_at
                FROM app.contract_comparisons
                WHERE base_contract_id = ? AND compare_contract_id = ?
                ORDER BY created_at DESC
                """,
                contract_id,
                contract_id,
            )
            row = cursor.fetchone()
        if row is None:
            return None
        return ComparisonDTO(
            id=self._normalize_id(row[0]),
            base_contract_id=self._normalize_id(row[1]),
            compare_contract_id=self._normalize_id(row[2]),
            created_by=self._normalize_id(row[3]),
            summary=row[4],
            risk_delta=row[5],
            created_at=row[6],
        )

    def list_changes(self, comparison_id: str) -> list[ComparisonChangeDTO]:
        with get_connection(self._settings) as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                SELECT id, comparison_id, change_type, category, description, old_value, new_value
                FROM app.comparison_changes
                WHERE comparison_id = ?
                ORDER BY change_type, category
                """,
                comparison_id,
            )
            rows = cursor.fetchall()
        return [
            ComparisonChangeDTO(
                id=self._normalize_id(row[0]),
                comparison_id=self._normalize_id(row[1]),
                change_type=row[2],
                category=row[3],
                description=row[4],
                old_value=row[5],
                new_value=row[6],
            )
            for row in rows
        ]

    @staticmethod
    def _normalize_id(value) -> str:
        return str(value) if isinstance(value, UUID) else value
