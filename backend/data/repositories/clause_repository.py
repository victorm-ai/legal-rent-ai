"""SQL Server repository for app.clauses (RF-18)."""

from typing import List
from uuid import UUID

from config.settings import Settings, get_settings
from data.analysis_dto import ClauseDTO
from data.database import get_connection


class ClauseRepository:
    """Persists identified contract clauses."""

    def __init__(self, settings: Settings | None = None):
        self._settings = settings or get_settings()

    def replace_for_analysis(self, analysis_id: str, clauses: List[dict]) -> List[ClauseDTO]:
        """Insert clauses and return records with generated IDs."""
        saved: List[ClauseDTO] = []
        with get_connection(self._settings) as connection:
            cursor = connection.cursor()
            cursor.execute(
                "DELETE FROM app.clauses WHERE analysis_id = ?",
                analysis_id,
            )
            for clause in clauses:
                cursor.execute(
                    """
                    INSERT INTO app.clauses (
                        analysis_id, category, text, section, page, confidence
                    )
                    OUTPUT
                        INSERTED.id,
                        INSERTED.category,
                        INSERTED.text,
                        INSERTED.section,
                        INSERTED.page,
                        INSERTED.confidence
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    analysis_id,
                    clause["category"],
                    clause["text"],
                    clause.get("section"),
                    clause.get("page"),
                    clause.get("confidence", 0.75),
                )
                row = cursor.fetchone()
                saved.append(
                    ClauseDTO(
                        id=self._normalize_id(row[0]),
                        category=row[1],
                        text=row[2],
                        section=row[3],
                        page=row[4],
                        confidence=float(row[5]),
                    )
                )
            connection.commit()
        return saved

    def list_by_analysis(self, analysis_id: str) -> List[ClauseDTO]:
        with get_connection(self._settings) as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                SELECT id, category, text, section, page, confidence
                FROM app.clauses
                WHERE analysis_id = ?
                ORDER BY page, section
                """,
                analysis_id,
            )
            rows = cursor.fetchall()
        return [
            ClauseDTO(
                id=self._normalize_id(row[0]),
                category=row[1],
                text=row[2],
                section=row[3],
                page=row[4],
                confidence=float(row[5]),
            )
            for row in rows
        ]

    @staticmethod
    def _normalize_id(value) -> str:
        return str(value) if isinstance(value, UUID) else value
