"""SQL Server repository for app.reports (RF-46–RF-49)."""

from datetime import datetime
from typing import List
from uuid import UUID

from config.settings import Settings, get_settings
from data.delivery_dto import ReportDTO
from data.database import get_connection


class ReportRepository:
    def __init__(self, settings: Settings | None = None):
        self._settings = settings or get_settings()

    def create(
        self,
        analysis_id: str,
        format: str,
        storage_path: str,
        generated_by: str,
    ) -> ReportDTO:
        with get_connection(self._settings) as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                INSERT INTO app.reports (analysis_id, format, storage_path, generated_by)
                OUTPUT INSERTED.id, INSERTED.analysis_id, INSERTED.format,
                       INSERTED.storage_path, INSERTED.generated_by, INSERTED.generated_at
                VALUES (?, ?, ?, ?)
                """,
                analysis_id,
                format,
                storage_path,
                generated_by,
            )
            row = cursor.fetchone()
            connection.commit()
        return ReportDTO(
            id=self._normalize_id(row[0]),
            analysis_id=self._normalize_id(row[1]),
            format=row[2],
            storage_path=row[3],
            generated_by=self._normalize_id(row[4]),
            generated_at=row[5],
        )

    def get_by_id(self, report_id: str) -> ReportDTO | None:
        with get_connection(self._settings) as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                SELECT id, analysis_id, format, storage_path, generated_by, generated_at
                FROM app.reports WHERE id = ?
                """,
                report_id,
            )
            row = cursor.fetchone()
        if row is None:
            return None
        return ReportDTO(
            id=self._normalize_id(row[0]),
            analysis_id=self._normalize_id(row[1]),
            format=row[2],
            storage_path=row[3],
            generated_by=self._normalize_id(row[4]),
            generated_at=row[5],
        )

    def list_by_analysis(self, analysis_id: str) -> List[ReportDTO]:
        with get_connection(self._settings) as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                SELECT id, analysis_id, format, storage_path, generated_by, generated_at
                FROM app.reports WHERE analysis_id = ?
                ORDER BY generated_at DESC
                """,
                analysis_id,
            )
            rows = cursor.fetchall()
        return [
            ReportDTO(
                id=self._normalize_id(row[0]),
                analysis_id=self._normalize_id(row[1]),
                format=row[2],
                storage_path=row[3],
                generated_by=self._normalize_id(row[4]),
                generated_at=row[5],
            )
            for row in rows
        ]

    @staticmethod
    def _normalize_id(value) -> str:
        return str(value) if isinstance(value, UUID) else value
