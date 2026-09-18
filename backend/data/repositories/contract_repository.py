"""SQL Server repository for app.contracts."""

from datetime import datetime, timedelta
from typing import List, Optional
from uuid import UUID

from config.settings import Settings, get_settings
from data.contract_dto import ContractDTO, ContractSummaryDTO
from data.database import get_connection


class ContractRepository:
    """Reads and writes contracts in SQL Server."""

    def __init__(self, settings: Settings | None = None):
        self._settings = settings or get_settings()

    def create(
        self,
        user_id: str,
        perspective: str,
        title: str | None = None,
    ) -> ContractDTO:
        """Insert a new contract in draft status."""
        with get_connection(self._settings) as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                INSERT INTO app.contracts (user_id, perspective, status, title)
                OUTPUT
                    INSERTED.id,
                    INSERTED.user_id,
                    INSERTED.perspective,
                    INSERTED.jurisdiction,
                    INSERTED.status,
                    INSERTED.title,
                    INSERTED.closure_notes,
                    INSERTED.created_at,
                    INSERTED.updated_at
                VALUES (?, ?, N'draft', ?)
                """,
                user_id,
                perspective,
                title,
            )
            row = cursor.fetchone()
            connection.commit()

        return self._row_to_contract(row, documents=[])

    def get_by_id(self, contract_id: str) -> Optional[ContractDTO]:
        """Find a non-deleted contract by ID."""
        with get_connection(self._settings) as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                SELECT
                    id, user_id, perspective, jurisdiction, status, title,
                    closure_notes, created_at, updated_at
                FROM app.contracts
                WHERE id = ? AND is_deleted = 0
                """,
                contract_id,
            )
            row = cursor.fetchone()
            if row is None:
                return None
            return self._row_to_contract(row, documents=[])

    def list_for_user(self, user_id: str) -> List[ContractSummaryDTO]:
        """List non-deleted contracts owned by a user."""
        with get_connection(self._settings) as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                SELECT
                    c.id,
                    c.user_id,
                    c.perspective,
                    c.jurisdiction,
                    c.status,
                    c.title,
                    COUNT(d.id) AS document_count,
                    (
                        SELECT STRING_AGG(x.document_type, ',')
                            WITHIN GROUP (ORDER BY x.document_type)
                        FROM (
                            SELECT DISTINCT d2.document_type
                            FROM app.contract_documents d2
                            WHERE d2.contract_id = c.id AND d2.is_deleted = 0
                        ) x
                    ) AS document_types,
                    c.is_deleted,
                    c.deleted_at,
                    c.created_at,
                    c.updated_at
                FROM app.contracts c
                LEFT JOIN app.contract_documents d
                    ON d.contract_id = c.id AND d.is_deleted = 0
                WHERE c.user_id = ? AND c.is_deleted = 0
                GROUP BY
                    c.id, c.user_id, c.perspective, c.jurisdiction, c.status,
                    c.title, c.is_deleted, c.deleted_at, c.created_at, c.updated_at
                ORDER BY c.created_at DESC
                """,
                user_id,
            )
            rows = cursor.fetchall()

        return [self._row_to_summary(row) for row in rows]

    def list_all(self, include_deleted: bool = False) -> List[ContractSummaryDTO]:
        """List contracts; optional inclusion of soft-deleted records."""
        deleted_filter = "" if include_deleted else "WHERE c.is_deleted = 0"
        with get_connection(self._settings) as connection:
            cursor = connection.cursor()
            cursor.execute(
                f"""
                SELECT
                    c.id,
                    c.user_id,
                    c.perspective,
                    c.jurisdiction,
                    c.status,
                    c.title,
                    COUNT(d.id) AS document_count,
                    (
                        SELECT STRING_AGG(x.document_type, ',')
                            WITHIN GROUP (ORDER BY x.document_type)
                        FROM (
                            SELECT DISTINCT d2.document_type
                            FROM app.contract_documents d2
                            WHERE d2.contract_id = c.id AND d2.is_deleted = 0
                        ) x
                    ) AS document_types,
                    c.is_deleted,
                    c.deleted_at,
                    c.created_at,
                    c.updated_at
                FROM app.contracts c
                LEFT JOIN app.contract_documents d
                    ON d.contract_id = c.id AND d.is_deleted = 0
                {deleted_filter}
                GROUP BY
                    c.id, c.user_id, c.perspective, c.jurisdiction, c.status,
                    c.title, c.is_deleted, c.deleted_at, c.created_at, c.updated_at
                ORDER BY c.created_at DESC
                """
            )
            rows = cursor.fetchall()

        return [self._row_to_summary(row) for row in rows]

    def list_for_lawyer(self) -> List[ContractSummaryDTO]:
        """List non-deleted contracts visible to lawyers (excludes draft)."""
        with get_connection(self._settings) as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                SELECT
                    c.id,
                    c.user_id,
                    c.perspective,
                    c.jurisdiction,
                    c.status,
                    c.title,
                    COUNT(d.id) AS document_count,
                    (
                        SELECT STRING_AGG(x.document_type, ',')
                            WITHIN GROUP (ORDER BY x.document_type)
                        FROM (
                            SELECT DISTINCT d2.document_type
                            FROM app.contract_documents d2
                            WHERE d2.contract_id = c.id AND d2.is_deleted = 0
                        ) x
                    ) AS document_types,
                    c.is_deleted,
                    c.deleted_at,
                    c.created_at,
                    c.updated_at
                FROM app.contracts c
                LEFT JOIN app.contract_documents d
                    ON d.contract_id = c.id AND d.is_deleted = 0
                WHERE c.is_deleted = 0 AND c.status <> N'draft'
                GROUP BY
                    c.id, c.user_id, c.perspective, c.jurisdiction, c.status,
                    c.title, c.is_deleted, c.deleted_at, c.created_at, c.updated_at
                ORDER BY c.created_at DESC
                """
            )
            rows = cursor.fetchall()

        return [self._row_to_summary(row) for row in rows]

    def soft_delete(self, contract_id: str) -> bool:
        """Mark a contract as deleted without removing database rows."""
        with get_connection(self._settings) as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                UPDATE app.contracts
                SET
                    is_deleted = 1,
                    deleted_at = SYSUTCDATETIME(),
                    updated_at = SYSUTCDATETIME()
                WHERE id = ? AND is_deleted = 0
                """,
                contract_id,
            )
            updated = cursor.rowcount > 0
            connection.commit()

        return updated

    def list_purge_eligible_ids(self, cutoff: datetime) -> List[str]:
        """Return soft-deleted contracts past retention without blocking dependencies."""
        with get_connection(self._settings) as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                SELECT c.id
                FROM app.contracts c
                WHERE c.is_deleted = 1
                  AND c.deleted_at IS NOT NULL
                  AND c.deleted_at <= ?
                  AND NOT EXISTS (
                      SELECT 1 FROM app.analyses a WHERE a.contract_id = c.id
                  )
                  AND NOT EXISTS (
                      SELECT 1
                      FROM app.contract_comparisons cc
                      WHERE cc.base_contract_id = c.id
                         OR cc.compare_contract_id = c.id
                  )
                ORDER BY c.deleted_at ASC
                """,
                cutoff,
            )
            rows = cursor.fetchall()

        return [self._normalize_id(row[0]) for row in rows]

    def count_soft_deleted_with_dependencies(self, cutoff: datetime) -> int:
        """Count expired soft-deleted contracts blocked from purge by dependencies."""
        with get_connection(self._settings) as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                SELECT COUNT(*)
                FROM app.contracts c
                WHERE c.is_deleted = 1
                  AND c.deleted_at IS NOT NULL
                  AND c.deleted_at <= ?
                  AND (
                      EXISTS (SELECT 1 FROM app.analyses a WHERE a.contract_id = c.id)
                      OR EXISTS (
                          SELECT 1
                          FROM app.contract_comparisons cc
                          WHERE cc.base_contract_id = c.id
                             OR cc.compare_contract_id = c.id
                      )
                  )
                """,
                cutoff,
            )
            row = cursor.fetchone()

        return int(row[0]) if row else 0

    def hard_delete_soft_deleted(self, contract_id: str) -> bool:
        """Permanently remove a soft-deleted contract and its documents."""
        with get_connection(self._settings) as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                SELECT 1
                FROM app.contracts
                WHERE id = ? AND is_deleted = 1
                """,
                contract_id,
            )
            if cursor.fetchone() is None:
                return False

            cursor.execute(
                "SELECT 1 FROM app.analyses WHERE contract_id = ?",
                contract_id,
            )
            if cursor.fetchone() is not None:
                return False

            cursor.execute(
                """
                SELECT 1
                FROM app.contract_comparisons
                WHERE base_contract_id = ? OR compare_contract_id = ?
                """,
                contract_id,
                contract_id,
            )
            if cursor.fetchone() is not None:
                return False

            cursor.execute(
                "DELETE FROM app.contract_documents WHERE contract_id = ?",
                contract_id,
            )
            cursor.execute(
                "DELETE FROM app.contract_parties WHERE contract_id = ?",
                contract_id,
            )
            cursor.execute(
                "DELETE FROM app.contracts WHERE id = ? AND is_deleted = 1",
                contract_id,
            )
            deleted = cursor.rowcount > 0
            connection.commit()

        return deleted

    def user_owns_contract(self, contract_id: str, user_id: str) -> bool:
        """Return True if the contract belongs to the user."""
        with get_connection(self._settings) as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                SELECT 1
                FROM app.contracts
                WHERE id = ? AND user_id = ? AND is_deleted = 0
                """,
                contract_id,
                user_id,
            )
            return cursor.fetchone() is not None

    def touch_updated_at(self, contract_id: str) -> None:
        """Refresh contract updated_at after related document changes."""
        with get_connection(self._settings) as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                UPDATE app.contracts
                SET updated_at = SYSUTCDATETIME()
                WHERE id = ? AND is_deleted = 0
                """,
                contract_id,
            )
            connection.commit()

    def update_contract(
        self,
        contract_id: str,
        status: str | None = None,
        title: str | None = None,
        closure_notes: str | None = None,
    ) -> Optional[ContractDTO]:
        """Update contract metadata and return the refreshed record."""
        updates: list[str] = ["updated_at = SYSUTCDATETIME()"]
        params: list = []

        if status is not None:
            updates.append("status = ?")
            params.append(status)
        if title is not None:
            updates.append("title = ?")
            params.append(title)
        if closure_notes is not None:
            updates.append("closure_notes = ?")
            params.append(closure_notes)

        if len(updates) == 1:
            return self.get_by_id(contract_id)

        params.append(contract_id)
        with get_connection(self._settings) as connection:
            cursor = connection.cursor()
            cursor.execute(
                f"""
                UPDATE app.contracts
                SET {", ".join(updates)}
                OUTPUT
                    INSERTED.id,
                    INSERTED.user_id,
                    INSERTED.perspective,
                    INSERTED.jurisdiction,
                    INSERTED.status,
                    INSERTED.title,
                    INSERTED.closure_notes,
                    INSERTED.created_at,
                    INSERTED.updated_at
                WHERE id = ? AND is_deleted = 0
                """,
                *params,
            )
            row = cursor.fetchone()
            connection.commit()

        if row is None:
            return None
        return self._row_to_contract(row, documents=[])

    def update_jurisdiction(self, contract_id: str, jurisdiction: str) -> None:
        """Persist detected jurisdiction on the contract (RF-10)."""
        with get_connection(self._settings) as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                UPDATE app.contracts
                SET jurisdiction = ?, updated_at = SYSUTCDATETIME()
                WHERE id = ? AND is_deleted = 0
                """,
                jurisdiction.strip(),
                contract_id,
            )
            connection.commit()

    def clear_jurisdiction(self, contract_id: str) -> None:
        """Clear jurisdiction when detection finds missing or inconsistent data (RF-11)."""
        with get_connection(self._settings) as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                UPDATE app.contracts
                SET jurisdiction = NULL, updated_at = SYSUTCDATETIME()
                WHERE id = ? AND is_deleted = 0
                """,
                contract_id,
            )
            connection.commit()

    @staticmethod
    def _normalize_id(value) -> str:
        return str(value) if isinstance(value, UUID) else value

    def _row_to_contract(self, row, documents) -> ContractDTO:
        return ContractDTO(
            id=self._normalize_id(row[0]),
            user_id=self._normalize_id(row[1]),
            perspective=row[2],
            jurisdiction=row[3],
            status=row[4],
            title=row[5],
            closure_notes=row[6],
            created_at=row[7],
            updated_at=row[8],
            documents=documents,
        )

    def _row_to_summary(self, row) -> ContractSummaryDTO:
        raw_types = row[7]
        document_types = raw_types.split(",") if raw_types else []
        is_deleted = bool(row[8])
        deleted_at = row[9]
        purge_eligible_at = None
        if is_deleted and deleted_at is not None:
            purge_eligible_at = deleted_at + timedelta(
                days=self._settings.soft_delete_retention_days
            )
        return ContractSummaryDTO(
            id=self._normalize_id(row[0]),
            user_id=self._normalize_id(row[1]),
            perspective=row[2],
            jurisdiction=row[3],
            status=row[4],
            title=row[5],
            document_count=row[6],
            document_types=document_types,
            is_deleted=is_deleted,
            deleted_at=deleted_at,
            purge_eligible_at=purge_eligible_at,
            created_at=row[10],
            updated_at=row[11],
        )
