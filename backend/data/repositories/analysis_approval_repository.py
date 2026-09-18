"""SQL Server repository for app.analysis_approvals (RF-69)."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from config.settings import Settings, get_settings
from data.database import get_connection


class AnalysisApprovalDTO:
    """Formal lawyer approval of an analysis."""

    def __init__(
        self,
        id: str,
        analysis_id: str,
        lawyer_id: str,
        approved_at: datetime,
        notes: Optional[str],
    ):
        self.id = id
        self.analysis_id = analysis_id
        self.lawyer_id = lawyer_id
        self.approved_at = approved_at
        self.notes = notes


class AnalysisApprovalRepository:
    """Persists formal analysis approvals."""

    def __init__(self, settings: Settings | None = None):
        self._settings = settings or get_settings()

    def create(
        self,
        analysis_id: str,
        lawyer_id: str,
        notes: str | None = None,
    ) -> AnalysisApprovalDTO:
        with get_connection(self._settings) as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                INSERT INTO app.analysis_approvals (analysis_id, lawyer_id, notes)
                OUTPUT
                    INSERTED.id,
                    INSERTED.analysis_id,
                    INSERTED.lawyer_id,
                    INSERTED.approved_at,
                    INSERTED.notes
                VALUES (?, ?, ?)
                """,
                analysis_id,
                lawyer_id,
                notes,
            )
            row = cursor.fetchone()
            connection.commit()
        return self._row_to_dto(row)

    def get_by_analysis(self, analysis_id: str) -> Optional[AnalysisApprovalDTO]:
        with get_connection(self._settings) as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                SELECT id, analysis_id, lawyer_id, approved_at, notes
                FROM app.analysis_approvals
                WHERE analysis_id = ?
                """,
                analysis_id,
            )
            row = cursor.fetchone()
        return self._row_to_dto(row) if row else None

    def list_all(self) -> list[dict]:
        with get_connection(self._settings) as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                SELECT id, analysis_id, lawyer_id, approved_at, notes
                FROM app.analysis_approvals
                ORDER BY approved_at DESC
                """
            )
            rows = cursor.fetchall()
        return [
            {
                "id": self._normalize_id(row[0]),
                "analysis_id": self._normalize_id(row[1]),
                "lawyer_id": self._normalize_id(row[2]),
                "approved_at": row[3].isoformat() if row[3] else None,
                "notes": row[4],
            }
            for row in rows
        ]

    @staticmethod
    def _normalize_id(value) -> str:
        return str(value) if isinstance(value, UUID) else value

    def _row_to_dto(self, row) -> AnalysisApprovalDTO:
        return AnalysisApprovalDTO(
            id=self._normalize_id(row[0]),
            analysis_id=self._normalize_id(row[1]),
            lawyer_id=self._normalize_id(row[2]),
            approved_at=row[3],
            notes=row[4],
        )
