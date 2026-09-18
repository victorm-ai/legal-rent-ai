"""SQL Server repository for app.finding_reviews (RF-68)."""

from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID

from config.settings import Settings, get_settings
from data.database import get_connection


class FindingReviewDTO:
    """Lawyer verdict on a finding."""

    def __init__(
        self,
        id: str,
        finding_id: str,
        lawyer_id: str,
        verdict: str,
        notes: Optional[str],
        created_at: datetime,
    ):
        self.id = id
        self.finding_id = finding_id
        self.lawyer_id = lawyer_id
        self.verdict = verdict
        self.notes = notes
        self.created_at = created_at


VALID_VERDICTS = frozenset({"correct", "incorrect", "not_relevant"})


class FindingReviewRepository:
    """Persists lawyer reviews of analysis findings."""

    def __init__(self, settings: Settings | None = None):
        self._settings = settings or get_settings()

    def upsert(
        self,
        finding_id: str,
        lawyer_id: str,
        verdict: str,
        notes: str | None = None,
    ) -> FindingReviewDTO:
        if verdict not in VALID_VERDICTS:
            raise ValueError(f"Invalid verdict: {verdict}")

        with get_connection(self._settings) as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                SELECT id FROM app.finding_reviews
                WHERE finding_id = ? AND lawyer_id = ?
                """,
                finding_id,
                lawyer_id,
            )
            existing = cursor.fetchone()

            if existing:
                cursor.execute(
                    """
                    UPDATE app.finding_reviews
                    SET verdict = ?, notes = ?, created_at = SYSUTCDATETIME()
                    OUTPUT
                        INSERTED.id,
                        INSERTED.finding_id,
                        INSERTED.lawyer_id,
                        INSERTED.verdict,
                        INSERTED.notes,
                        INSERTED.created_at
                    WHERE id = ?
                    """,
                    verdict,
                    notes,
                    self._normalize_id(existing[0]),
                )
            else:
                cursor.execute(
                    """
                    INSERT INTO app.finding_reviews (finding_id, lawyer_id, verdict, notes)
                    OUTPUT
                        INSERTED.id,
                        INSERTED.finding_id,
                        INSERTED.lawyer_id,
                        INSERTED.verdict,
                        INSERTED.notes,
                        INSERTED.created_at
                    VALUES (?, ?, ?, ?)
                    """,
                    finding_id,
                    lawyer_id,
                    verdict,
                    notes,
                )

            row = cursor.fetchone()
            connection.commit()
        return self._row_to_dto(row)

    def list_by_analysis(self, analysis_id: str) -> List[FindingReviewDTO]:
        with get_connection(self._settings) as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                SELECT
                    fr.id, fr.finding_id, fr.lawyer_id, fr.verdict, fr.notes, fr.created_at
                FROM app.finding_reviews fr
                INNER JOIN app.findings f ON f.id = fr.finding_id
                WHERE f.analysis_id = ?
                ORDER BY fr.created_at DESC
                """,
                analysis_id,
            )
            rows = cursor.fetchall()
        return [self._row_to_dto(row) for row in rows]

    def map_by_finding_for_analysis(self, analysis_id: str) -> Dict[str, FindingReviewDTO]:
        reviews = self.list_by_analysis(analysis_id)
        mapped: Dict[str, FindingReviewDTO] = {}
        for review in reviews:
            if review.finding_id not in mapped:
                mapped[review.finding_id] = review
        return mapped

    def list_all(self) -> list[dict]:
        with get_connection(self._settings) as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                SELECT fr.id, fr.finding_id, fr.lawyer_id, fr.verdict, fr.notes, fr.created_at,
                       f.analysis_id, f.title, f.finding_type, f.severity
                FROM app.finding_reviews fr
                INNER JOIN app.findings f ON f.id = fr.finding_id
                ORDER BY fr.created_at DESC
                """
            )
            rows = cursor.fetchall()
        return [
            {
                "id": self._normalize_id(row[0]),
                "finding_id": self._normalize_id(row[1]),
                "lawyer_id": self._normalize_id(row[2]),
                "verdict": row[3],
                "notes": row[4],
                "created_at": row[5].isoformat() if row[5] else None,
                "analysis_id": self._normalize_id(row[6]),
                "finding_title": row[7],
                "finding_type": row[8],
                "severity": row[9],
            }
            for row in rows
        ]

    @staticmethod
    def _normalize_id(value) -> str:
        return str(value) if isinstance(value, UUID) else value

    def _row_to_dto(self, row) -> FindingReviewDTO:
        return FindingReviewDTO(
            id=self._normalize_id(row[0]),
            finding_id=self._normalize_id(row[1]),
            lawyer_id=self._normalize_id(row[2]),
            verdict=row[3],
            notes=row[4],
            created_at=row[5],
        )
