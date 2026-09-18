"""SQL Server repository for app.contract_documents."""

from typing import List, Optional, Tuple
from uuid import UUID

from config.settings import Settings, get_settings
from data.contract_dto import ContractDocumentDTO
from data.database import get_connection


class ContractDocumentRepository:
    """Reads and writes contract documents with binary content."""

    _SELECT_COLUMNS = """
        id, contract_id, file_name, file_size_bytes,
        document_type, mime_type, page_count, extraction_method, is_signed_version, uploaded_at
    """

    def __init__(self, settings: Settings | None = None):
        self._settings = settings or get_settings()

    def create(
        self,
        contract_id: str,
        file_name: str,
        file_content: bytes,
        file_size_bytes: int,
        document_type: str,
        mime_type: str,
        extracted_text: str | None = None,
        extraction_method: str | None = None,
        page_count: int | None = None,
        is_signed_version: bool = False,
    ) -> ContractDocumentDTO:
        """Insert a document with binary content and extracted text metadata."""
        with get_connection(self._settings) as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                INSERT INTO app.contract_documents (
                    contract_id,
                    file_name,
                    file_content,
                    file_size_bytes,
                    document_type,
                    mime_type,
                    extracted_text,
                    extraction_method,
                    page_count,
                    is_signed_version
                )
                OUTPUT
                    INSERTED.id,
                    INSERTED.contract_id,
                    INSERTED.file_name,
                    INSERTED.file_size_bytes,
                    INSERTED.document_type,
                    INSERTED.mime_type,
                    INSERTED.page_count,
                    INSERTED.extraction_method,
                    INSERTED.is_signed_version,
                    INSERTED.uploaded_at
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                contract_id,
                file_name,
                file_content,
                file_size_bytes,
                document_type,
                mime_type,
                extracted_text,
                extraction_method,
                page_count,
                1 if is_signed_version else 0,
            )
            row = cursor.fetchone()
            connection.commit()

        return self._row_to_document(row)

    def list_by_contract(self, contract_id: str) -> List[ContractDocumentDTO]:
        """List non-deleted documents for a contract."""
        with get_connection(self._settings) as connection:
            cursor = connection.cursor()
            cursor.execute(
                f"""
                SELECT {self._SELECT_COLUMNS}
                FROM app.contract_documents
                WHERE contract_id = ? AND is_deleted = 0
                ORDER BY uploaded_at ASC
                """,
                contract_id,
            )
            rows = cursor.fetchall()

        return [self._row_to_document(row) for row in rows]

    def soft_delete_by_contract(self, contract_id: str) -> None:
        """Mark all documents of a contract as deleted."""
        with get_connection(self._settings) as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                UPDATE app.contract_documents
                SET is_deleted = 1
                WHERE contract_id = ? AND is_deleted = 0
                """,
                contract_id,
            )
            connection.commit()

    def get_by_id(self, contract_id: str, document_id: str) -> Optional[ContractDocumentDTO]:
        """Find a non-deleted document by contract and document ID."""
        with get_connection(self._settings) as connection:
            cursor = connection.cursor()
            cursor.execute(
                f"""
                SELECT {self._SELECT_COLUMNS}
                FROM app.contract_documents
                WHERE contract_id = ? AND id = ? AND is_deleted = 0
                """,
                contract_id,
                document_id,
            )
            row = cursor.fetchone()
            return self._row_to_document(row) if row else None

    def get_content(self, contract_id: str, document_id: str) -> Optional[Tuple[str, str, bytes]]:
        """Return file name, mime type and binary content for download."""
        with get_connection(self._settings) as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                SELECT file_name, mime_type, file_content
                FROM app.contract_documents
                WHERE contract_id = ? AND id = ? AND is_deleted = 0
                """,
                contract_id,
                document_id,
            )
            row = cursor.fetchone()
            if row is None:
                return None
            return row[0], row[1] or "application/octet-stream", bytes(row[2])

    def get_extracted_text(
        self,
        contract_id: str,
        document_id: str,
    ) -> Optional[Tuple[str, str | None, int | None]]:
        """Return extracted text, method and page count for a document."""
        with get_connection(self._settings) as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                SELECT extracted_text, extraction_method, page_count
                FROM app.contract_documents
                WHERE contract_id = ? AND id = ? AND is_deleted = 0
                """,
                contract_id,
                document_id,
            )
            row = cursor.fetchone()
            if row is None:
                return None
            return row[0] or "", row[1], row[2]

    def soft_delete_by_document_type(self, contract_id: str, document_type: str) -> int:
        """Soft-delete active documents of a given type for a contract."""
        with get_connection(self._settings) as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                UPDATE app.contract_documents
                SET is_deleted = 1
                WHERE contract_id = ? AND document_type = ? AND is_deleted = 0
                """,
                contract_id,
                document_type,
            )
            deleted = cursor.rowcount
            connection.commit()
        return deleted

    def update_extracted_text(
        self,
        contract_id: str,
        document_id: str,
        extracted_text: str,
        extraction_method: str = "edited",
    ) -> bool:
        """Persist lawyer/client-visible text edits for a document."""
        with get_connection(self._settings) as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                UPDATE app.contract_documents
                SET extracted_text = ?, extraction_method = ?
                WHERE contract_id = ? AND id = ? AND is_deleted = 0
                """,
                extracted_text,
                extraction_method,
                contract_id,
                document_id,
            )
            updated = cursor.rowcount > 0
            connection.commit()
        return updated

    def get_combined_extracted_text(self, contract_id: str) -> str:
        """Return extracted text from all documents, main contract first."""
        return self.get_extracted_text_for_analysis_scope(contract_id, "original")

    def get_extracted_text_for_analysis_scope(self, contract_id: str, document_scope: str) -> str:
        """Return extracted text for an analysis scope (original bundle vs lawyer revision)."""
        if document_scope == "lawyer_revision":
            type_filter_sql = "document_type = N'lawyer_revision'"
            order_sql = "uploaded_at DESC"
        else:
            type_filter_sql = "document_type <> N'lawyer_revision'"
            order_sql = """
                CASE document_type
                    WHEN N'main_contract' THEN 0
                    WHEN N'annex' THEN 1
                    ELSE 2
                END,
                uploaded_at ASC
            """

        with get_connection(self._settings) as connection:
            cursor = connection.cursor()
            cursor.execute(
                f"""
                SELECT file_name, document_type, extracted_text
                FROM app.contract_documents
                WHERE contract_id = ? AND is_deleted = 0 AND {type_filter_sql}
                ORDER BY {order_sql}
                """,
                contract_id,
            )
            rows = cursor.fetchall()

        parts: list[str] = []
        for file_name, _doc_type, extracted_text in rows:
            if extracted_text and extracted_text.strip():
                parts.append(f"--- {file_name} ---\n{extracted_text.strip()}")
        return "\n\n".join(parts)

    @staticmethod
    def _normalize_id(value) -> str:
        return str(value) if isinstance(value, UUID) else value

    def _row_to_document(self, row) -> ContractDocumentDTO:
        return ContractDocumentDTO(
            id=self._normalize_id(row[0]),
            contract_id=self._normalize_id(row[1]),
            file_name=row[2],
            file_size_bytes=row[3],
            document_type=row[4],
            mime_type=row[5],
            page_count=row[6],
            extraction_method=row[7],
            is_signed_version=bool(row[8]),
            uploaded_at=row[9],
        )
