#!/usr/bin/env python3
"""Verify LegalRentAI schema matches what the application expects."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_BACKEND = _REPO_ROOT / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from config.settings import get_settings
from data.database import get_connection

EXPECTED_TABLES = frozenset(
    {
        "roles",
        "users",
        "contracts",
        "contract_documents",
        "contract_parties",
        "analyses",
        "analysis_llm_runs",
        "extracted_fields",
        "clauses",
        "findings",
        "legal_citations",
        "chat_sessions",
        "chat_messages",
        "chat_llm_call_events",
        "reports",
        "download_logs",
        "notifications",
        "review_messages",
        "review_message_read_cursors",
        "contract_comparisons",
        "comparison_changes",
        "finding_reviews",
        "analysis_approvals",
    }
)

REQUIRED_COLUMNS: dict[str, frozenset[str]] = {
    "app.contracts": frozenset({"closure_notes", "status", "perspective"}),
    "app.analyses": frozenset({"perspective", "document_scope", "status"}),
    "app.contract_documents": frozenset(
        {"file_content", "extracted_text", "extraction_method", "document_type"}
    ),
    "app.findings": frozenset({"confidence", "severity", "finding_type"}),
}

EXPECTED_ROLES = frozenset({("lawyer", 1), ("client", 2)})


def main() -> int:
    settings = get_settings()
    errors: list[str] = []

    with get_connection(settings) as conn:
        cur = conn.cursor()

        cur.execute(
            """
            SELECT t.name
            FROM sys.tables t
            INNER JOIN sys.schemas s ON s.schema_id = t.schema_id
            WHERE s.name = N'app'
            """
        )
        tables = {row[0] for row in cur.fetchall()}
        missing_tables = EXPECTED_TABLES - tables
        if missing_tables:
            errors.append(f"Missing tables in [app]: {sorted(missing_tables)}")

        for table, columns in REQUIRED_COLUMNS.items():
            schema, name = table.split(".")
            for column in columns:
                cur.execute(
                    """
                    SELECT COL_LENGTH(?, ?)
                    """,
                    table,
                    column,
                )
                if cur.fetchone()[0] is None:
                    errors.append(f"Missing column {table}.{column}")

        cur.execute("SELECT code, id FROM app.roles ORDER BY id")
        roles = {(row[0], int(row[1])) for row in cur.fetchall()}
        if roles != EXPECTED_ROLES:
            errors.append(
                f"Role catalog mismatch (expected lawyer=1, client=2 only): {sorted(roles)}"
            )

        cur.execute(
            """
            SELECT i.name
            FROM sys.indexes i
            WHERE i.object_id = OBJECT_ID(N'app.analyses')
              AND i.name = N'UX_analyses_contract_perspective_scope'
            """
        )
        if cur.fetchone() is None:
            errors.append("Missing index UX_analyses_contract_perspective_scope on app.analyses")

    if errors:
        print("Schema verification FAILED:")
        for item in errors:
            print(f"  - {item}")
        print("\nRun from repo root: .\\apply_migrations.bat")
        return 1

    print("Schema verification OK (23 tables, roles, key columns).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
