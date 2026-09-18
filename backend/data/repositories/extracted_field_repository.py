"""SQL Server repository for app.extracted_fields (RF-13)."""

from typing import List
from uuid import UUID

from config.settings import Settings, get_settings
from data.analysis_dto import ExtractedFieldDTO
from data.database import get_connection


class ExtractedFieldRepository:
    """Persists structured fields extracted from contract text."""

    def __init__(self, settings: Settings | None = None):
        self._settings = settings or get_settings()

    def replace_for_analysis(self, analysis_id: str, fields: List[ExtractedFieldDTO]) -> None:
        with get_connection(self._settings) as connection:
            cursor = connection.cursor()
            cursor.execute(
                "DELETE FROM app.extracted_fields WHERE analysis_id = ?",
                analysis_id,
            )
            for field in fields:
                cursor.execute(
                    """
                    INSERT INTO app.extracted_fields (
                        analysis_id, field_name, field_value, confidence,
                        source_page, source_clause, source_section, source_text_snippet
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    analysis_id,
                    field.field_name,
                    field.field_value,
                    field.confidence,
                    field.source_page,
                    field.source_clause,
                    field.source_section,
                    field.source_text_snippet,
                )
            connection.commit()

    def list_by_analysis(self, analysis_id: str) -> List[ExtractedFieldDTO]:
        with get_connection(self._settings) as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                SELECT
                    field_name, field_value, confidence,
                    source_page, source_clause, source_section, source_text_snippet
                FROM app.extracted_fields
                WHERE analysis_id = ?
                ORDER BY field_name
                """,
                analysis_id,
            )
            rows = cursor.fetchall()
        return [self._row_to_field(row) for row in rows]

    @staticmethod
    def _row_to_field(row) -> ExtractedFieldDTO:
        return ExtractedFieldDTO(
            field_name=row[0],
            field_value=row[1] or "",
            confidence=float(row[2]),
            source_page=row[3],
            source_clause=row[4],
            source_section=row[5],
            source_text_snippet=row[6],
        )
