"""SQL Server repository for app.findings and app.legal_citations (RF-27–RF-40)."""

from typing import Any, List
from uuid import UUID

from config.settings import Settings, get_settings
from data.analysis_dto import FindingDTO, LegalCitationDTO
from data.database import get_connection
from llm.findings_utils import ensure_finding_confidence, normalize_severity


class FindingRepository:
    """Persists contract analysis findings and legal citations."""

    _confidence_column: bool | None = None

    def __init__(self, settings: Settings | None = None):
        self._settings = settings or get_settings()

    def _supports_confidence(self, cursor) -> bool:
        if FindingRepository._confidence_column is not None:
            return FindingRepository._confidence_column
        cursor.execute("SELECT COL_LENGTH('app.findings', 'confidence')")
        row = cursor.fetchone()
        FindingRepository._confidence_column = bool(row and row[0] is not None)
        return FindingRepository._confidence_column

    def replace_for_analysis(
        self,
        analysis_id: str,
        findings: List[dict[str, Any]],
        clause_id_by_index: dict[int, str] | None = None,
        clause_id_resolver=None,
    ) -> List[FindingDTO]:
        """Replace all findings for an analysis and return saved records."""
        saved: List[FindingDTO] = []
        clause_id_by_index = clause_id_by_index or {}

        with get_connection(self._settings) as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                DELETE FROM app.legal_citations
                WHERE finding_id IN (
                    SELECT id FROM app.findings WHERE analysis_id = ?
                )
                """,
                analysis_id,
            )
            cursor.execute(
                "DELETE FROM app.findings WHERE analysis_id = ?",
                analysis_id,
            )

            supports_confidence = self._supports_confidence(cursor)

            for raw_finding in findings:
                finding = ensure_finding_confidence(dict(raw_finding))
                clause_id = None
                if clause_id_resolver:
                    clause_id = clause_id_resolver(finding)
                if clause_id is None:
                    clause_index = finding.get("clause_index")
                    if clause_index is not None:
                        try:
                            clause_id = clause_id_by_index.get(int(clause_index))
                        except (TypeError, ValueError):
                            pass

                if supports_confidence:
                    cursor.execute(
                        """
                        INSERT INTO app.findings (
                            analysis_id, clause_id, finding_type, severity, title, description,
                            legal_basis, source_law, evidence_text, evidence_page,
                            recommendation, suggested_rewording, sort_order, confidence
                        )
                        OUTPUT
                            INSERTED.id,
                            INSERTED.clause_id,
                            INSERTED.finding_type,
                            INSERTED.severity,
                            INSERTED.title,
                            INSERTED.description,
                            INSERTED.legal_basis,
                            INSERTED.source_law,
                            INSERTED.evidence_text,
                            INSERTED.evidence_page,
                            INSERTED.recommendation,
                            INSERTED.suggested_rewording,
                            INSERTED.sort_order,
                            INSERTED.confidence
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        analysis_id,
                        clause_id,
                        finding["finding_type"],
                        normalize_severity(finding.get("severity")),
                        finding["title"],
                        finding["description"],
                        finding.get("legal_basis"),
                        finding.get("source_law"),
                        finding.get("evidence_text"),
                        finding.get("evidence_page"),
                        finding.get("recommendation"),
                        finding.get("suggested_rewording"),
                        finding.get("sort_order", 0),
                        finding.get("confidence"),
                    )
                    row = cursor.fetchone()
                    confidence = float(row[13]) if row[13] is not None else finding.get("confidence")
                else:
                    cursor.execute(
                        """
                        INSERT INTO app.findings (
                            analysis_id, clause_id, finding_type, severity, title, description,
                            legal_basis, source_law, evidence_text, evidence_page,
                            recommendation, suggested_rewording, sort_order
                        )
                        OUTPUT
                            INSERTED.id,
                            INSERTED.clause_id,
                            INSERTED.finding_type,
                            INSERTED.severity,
                            INSERTED.title,
                            INSERTED.description,
                            INSERTED.legal_basis,
                            INSERTED.source_law,
                            INSERTED.evidence_text,
                            INSERTED.evidence_page,
                            INSERTED.recommendation,
                            INSERTED.suggested_rewording,
                            INSERTED.sort_order
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        analysis_id,
                        clause_id,
                        finding["finding_type"],
                        normalize_severity(finding.get("severity")),
                        finding["title"],
                        finding["description"],
                        finding.get("legal_basis"),
                        finding.get("source_law"),
                        finding.get("evidence_text"),
                        finding.get("evidence_page"),
                        finding.get("recommendation"),
                        finding.get("suggested_rewording"),
                        finding.get("sort_order", 0),
                    )
                    row = cursor.fetchone()
                    confidence = finding.get("confidence")

                finding_id = self._normalize_id(row[0])
                citations = self._insert_citations(
                    cursor, finding_id, finding.get("legal_citations") or []
                )
                saved.append(
                    FindingDTO(
                        id=finding_id,
                        clause_id=self._normalize_id(row[1]) if row[1] else None,
                        finding_type=row[2],
                        severity=row[3],
                        title=row[4],
                        description=row[5],
                        legal_basis=row[6],
                        source_law=row[7],
                        evidence_text=row[8],
                        evidence_page=row[9],
                        recommendation=row[10],
                        suggested_rewording=row[11],
                        sort_order=int(row[12]),
                        confidence=float(confidence) if confidence is not None else None,
                        legal_citations=citations,
                    )
                )

            connection.commit()
        return saved

    def get_by_id(self, finding_id: str) -> FindingDTO | None:
        with get_connection(self._settings) as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                SELECT
                    id, clause_id, finding_type, severity, title, description,
                    legal_basis, source_law, evidence_text, evidence_page,
                    recommendation, suggested_rewording, sort_order, analysis_id
                FROM app.findings
                WHERE id = ?
                """,
                finding_id,
            )
            row = cursor.fetchone()
            if row is None:
                return None

            finding_id_norm = self._normalize_id(row[0])
            cursor.execute(
                """
                SELECT id, law_code, article, excerpt, source_uri
                FROM app.legal_citations
                WHERE finding_id = ?
                ORDER BY law_code, article
                """,
                finding_id_norm,
            )
            citation_rows = cursor.fetchall()

        return FindingDTO(
            id=finding_id_norm,
            clause_id=self._normalize_id(row[1]) if row[1] else None,
            finding_type=row[2],
            severity=row[3],
            title=row[4],
            description=row[5],
            legal_basis=row[6],
            source_law=row[7],
            evidence_text=row[8],
            evidence_page=row[9],
            recommendation=row[10],
            suggested_rewording=row[11],
            sort_order=int(row[12]),
            legal_citations=[
                LegalCitationDTO(
                    id=self._normalize_id(citation[0]),
                    law_code=citation[1],
                    article=citation[2],
                    excerpt=citation[3],
                    source_uri=citation[4],
                )
                for citation in citation_rows
            ],
            analysis_id=self._normalize_id(row[13]),
        )

    def list_by_analysis(self, analysis_id: str) -> List[FindingDTO]:
        with get_connection(self._settings) as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                SELECT
                    id, clause_id, finding_type, severity, title, description,
                    legal_basis, source_law, evidence_text, evidence_page,
                    recommendation, suggested_rewording, sort_order
                FROM app.findings
                WHERE analysis_id = ?
                ORDER BY sort_order, severity DESC, title
                """,
                analysis_id,
            )
            rows = cursor.fetchall()

            findings: List[FindingDTO] = []
            for row in rows:
                finding_id = self._normalize_id(row[0])
                cursor.execute(
                    """
                    SELECT id, law_code, article, excerpt, source_uri
                    FROM app.legal_citations
                    WHERE finding_id = ?
                    ORDER BY law_code, article
                    """,
                    finding_id,
                )
                citation_rows = cursor.fetchall()
                findings.append(
                    FindingDTO(
                        id=finding_id,
                        clause_id=self._normalize_id(row[1]) if row[1] else None,
                        finding_type=row[2],
                        severity=row[3],
                        title=row[4],
                        description=row[5],
                        legal_basis=row[6],
                        source_law=row[7],
                        evidence_text=row[8],
                        evidence_page=row[9],
                        recommendation=row[10],
                        suggested_rewording=row[11],
                        sort_order=int(row[12]),
                        legal_citations=[
                            LegalCitationDTO(
                                id=self._normalize_id(citation[0]),
                                law_code=citation[1],
                                article=citation[2],
                                excerpt=citation[3],
                                source_uri=citation[4],
                            )
                            for citation in citation_rows
                        ],
                    )
                )
        return findings

    def _insert_citations(self, cursor, finding_id: str, citations: list) -> List[LegalCitationDTO]:
        saved: List[LegalCitationDTO] = []
        for citation in citations:
            if not citation.get("law_code"):
                continue
            cursor.execute(
                """
                INSERT INTO app.legal_citations (finding_id, law_code, article, excerpt, source_uri)
                OUTPUT INSERTED.id, INSERTED.law_code, INSERTED.article, INSERTED.excerpt, INSERTED.source_uri
                VALUES (?, ?, ?, ?, ?)
                """,
                finding_id,
                citation["law_code"],
                citation.get("article"),
                citation.get("excerpt"),
                citation.get("source_uri"),
            )
            row = cursor.fetchone()
            saved.append(
                LegalCitationDTO(
                    id=self._normalize_id(row[0]),
                    law_code=row[1],
                    article=row[2],
                    excerpt=row[3],
                    source_uri=row[4],
                )
            )
        return saved

    @staticmethod
    def _normalize_id(value) -> str:
        return str(value) if isinstance(value, UUID) else value
