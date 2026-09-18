"""SQL Server repository for app.analyses (RF-52)."""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from config.settings import Settings, get_settings
from data.analysis_dto import AnalysisDTO
from data.database import get_connection

_ANALYSIS_SELECT = """
    id, contract_id, perspective, document_scope, status, summary_executive, general_risk,
    started_at, completed_at, created_at
"""


class AnalysisRepository:
    """Reads and writes contract analyses."""

    def __init__(self, settings: Settings | None = None):
        self._settings = settings or get_settings()

    def create(
        self,
        contract_id: str,
        perspective: str,
        document_scope: str = "original",
        status: str = "processing",
    ) -> AnalysisDTO:
        with get_connection(self._settings) as connection:
            cursor = connection.cursor()
            cursor.execute(
                f"""
                INSERT INTO app.analyses (contract_id, perspective, document_scope, status, started_at)
                OUTPUT
                    INSERTED.id,
                    INSERTED.contract_id,
                    INSERTED.perspective,
                    INSERTED.document_scope,
                    INSERTED.status,
                    INSERTED.summary_executive,
                    INSERTED.general_risk,
                    INSERTED.started_at,
                    INSERTED.completed_at,
                    INSERTED.created_at
                VALUES (?, ?, ?, ?, SYSUTCDATETIME())
                """,
                contract_id,
                perspective,
                document_scope,
                status,
            )
            row = cursor.fetchone()
            connection.commit()
        return self._row_to_analysis(row)

    def get_by_id(self, analysis_id: str) -> Optional[AnalysisDTO]:
        with get_connection(self._settings) as connection:
            cursor = connection.cursor()
            cursor.execute(
                f"""
                SELECT {_ANALYSIS_SELECT}
                FROM app.analyses
                WHERE id = ?
                """,
                analysis_id,
            )
            row = cursor.fetchone()
            return self._row_to_analysis(row) if row else None

    def get_by_contract_and_perspective(
        self,
        contract_id: str,
        perspective: str,
    ) -> Optional[AnalysisDTO]:
        """Return the latest original-scope analysis for a contract perspective."""
        return self.get_by_contract_perspective_scope(contract_id, perspective, "original")

    def get_by_contract_perspective_scope(
        self,
        contract_id: str,
        perspective: str,
        document_scope: str,
    ) -> Optional[AnalysisDTO]:
        with get_connection(self._settings) as connection:
            cursor = connection.cursor()
            cursor.execute(
                f"""
                SELECT TOP 1 {_ANALYSIS_SELECT}
                FROM app.analyses
                WHERE contract_id = ? AND perspective = ? AND document_scope = ?
                ORDER BY created_at DESC
                """,
                contract_id,
                perspective,
                document_scope,
            )
            row = cursor.fetchone()
            return self._row_to_analysis(row) if row else None

    def list_by_contract(self, contract_id: str) -> List[AnalysisDTO]:
        with get_connection(self._settings) as connection:
            cursor = connection.cursor()
            cursor.execute(
                f"""
                SELECT {_ANALYSIS_SELECT}
                FROM app.analyses
                WHERE contract_id = ?
                ORDER BY created_at DESC
                """,
                contract_id,
            )
            rows = cursor.fetchall()
        return [self._row_to_analysis(row) for row in rows]

    def reset_for_retry(self, analysis_id: str) -> Optional[AnalysisDTO]:
        with get_connection(self._settings) as connection:
            cursor = connection.cursor()
            cursor.execute(
                f"""
                UPDATE app.analyses
                SET
                    status = N'processing',
                    summary_executive = NULL,
                    general_risk = NULL,
                    started_at = SYSUTCDATETIME(),
                    completed_at = NULL
                OUTPUT
                    INSERTED.id,
                    INSERTED.contract_id,
                    INSERTED.perspective,
                    INSERTED.document_scope,
                    INSERTED.status,
                    INSERTED.summary_executive,
                    INSERTED.general_risk,
                    INSERTED.started_at,
                    INSERTED.completed_at,
                    INSERTED.created_at
                WHERE id = ?
                """,
                analysis_id,
            )
            row = cursor.fetchone()
            connection.commit()
        return self._row_to_analysis(row) if row else None

    def update_completed(
        self,
        analysis_id: str,
        status: str,
        summary_executive: str,
        general_risk: str,
    ) -> Optional[AnalysisDTO]:
        with get_connection(self._settings) as connection:
            cursor = connection.cursor()
            cursor.execute(
                f"""
                UPDATE app.analyses
                SET
                    status = ?,
                    summary_executive = ?,
                    general_risk = ?,
                    completed_at = SYSUTCDATETIME()
                OUTPUT
                    INSERTED.id,
                    INSERTED.contract_id,
                    INSERTED.perspective,
                    INSERTED.document_scope,
                    INSERTED.status,
                    INSERTED.summary_executive,
                    INSERTED.general_risk,
                    INSERTED.started_at,
                    INSERTED.completed_at,
                    INSERTED.created_at
                WHERE id = ?
                """,
                status,
                summary_executive,
                general_risk,
                analysis_id,
            )
            row = cursor.fetchone()
            connection.commit()
        return self._row_to_analysis(row) if row else None

    def update_status(self, analysis_id: str, status: str) -> Optional[AnalysisDTO]:
        with get_connection(self._settings) as connection:
            cursor = connection.cursor()
            cursor.execute(
                f"""
                UPDATE app.analyses
                SET status = ?
                OUTPUT
                    INSERTED.id,
                    INSERTED.contract_id,
                    INSERTED.perspective,
                    INSERTED.document_scope,
                    INSERTED.status,
                    INSERTED.summary_executive,
                    INSERTED.general_risk,
                    INSERTED.started_at,
                    INSERTED.completed_at,
                    INSERTED.created_at
                WHERE id = ?
                """,
                status,
                analysis_id,
            )
            row = cursor.fetchone()
            connection.commit()
        return self._row_to_analysis(row) if row else None

    def promote_ai_generated_to_pending_review(self, contract_id: str) -> int:
        """Move completed analyses into the lawyer review queue for a contract."""
        with get_connection(self._settings) as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                UPDATE app.analyses
                SET status = N'pending_review'
                WHERE contract_id = ? AND status = N'ai_generated'
                """,
                contract_id,
            )
            updated = cursor.rowcount
            connection.commit()
        return updated

    def log_llm_run(
        self,
        analysis_id: str,
        provider: str,
        model: str,
        tokens_input: int | None = None,
        tokens_output: int | None = None,
        duration_ms: int | None = None,
        prompt_id: str | None = None,
        model_version: str | None = None,
        response_storage_path: str | None = None,
    ) -> None:
        with get_connection(self._settings) as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                INSERT INTO app.analysis_llm_runs (
                    analysis_id, provider, model, model_version, prompt_id,
                    response_storage_path, tokens_input, tokens_output, duration_ms
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                analysis_id,
                provider,
                model,
                model_version,
                prompt_id,
                response_storage_path,
                tokens_input,
                tokens_output,
                duration_ms,
            )
            connection.commit()

    def get_latest_llm_metadata(self, analysis_id: str) -> dict:
        with get_connection(self._settings) as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                SELECT TOP 1
                    provider, model, prompt_id, duration_ms, tokens_input, tokens_output, created_at
                FROM app.analysis_llm_runs
                WHERE analysis_id = ?
                ORDER BY created_at DESC
                """,
                analysis_id,
            )
            row = cursor.fetchone()
        if row is None:
            return {}
        return {
            "provider": row[0],
            "model": row[1],
            "prompt_id": row[2],
            "duration_ms": row[3],
            "tokens_input": row[4],
            "tokens_output": row[5],
            "created_at": row[6].isoformat() if row[6] else None,
        }

    @staticmethod
    def _normalize_id(value) -> str:
        return str(value) if isinstance(value, UUID) else value

    def _row_to_analysis(self, row) -> AnalysisDTO:
        if len(row) == 9:
            return AnalysisDTO(
                id=self._normalize_id(row[0]),
                contract_id=self._normalize_id(row[1]),
                perspective=row[2],
                document_scope="original",
                status=row[3],
                summary_executive=row[4],
                general_risk=row[5],
                started_at=row[6],
                completed_at=row[7],
                created_at=row[8],
            )
        return AnalysisDTO(
            id=self._normalize_id(row[0]),
            contract_id=self._normalize_id(row[1]),
            perspective=row[2],
            document_scope=row[3] or "original",
            status=row[4],
            summary_executive=row[5],
            general_risk=row[6],
            started_at=row[7],
            completed_at=row[8],
            created_at=row[9],
        )
