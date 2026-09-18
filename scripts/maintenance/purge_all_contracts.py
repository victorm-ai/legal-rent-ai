"""Remove all contracts and dependent rows (dev/demo reset). Keeps users and roles."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from config.settings import Settings, get_settings
from data.database import get_connection

# Child tables first (FK-safe order).
_PURGE_STATEMENTS = [
    "DELETE FROM app.comparison_changes",
    "DELETE FROM app.contract_comparisons",
    "DELETE FROM app.review_message_read_cursors",
    "DELETE FROM app.chat_llm_call_events",
    "DELETE FROM app.chat_messages",
    "DELETE FROM app.chat_sessions",
    "DELETE FROM app.finding_reviews",
    "DELETE FROM app.legal_citations",
    "DELETE FROM app.findings",
    "DELETE FROM app.analysis_approvals",
    "DELETE FROM app.review_messages",
    "DELETE FROM app.analysis_llm_runs",
    "DELETE FROM app.extracted_fields",
    "DELETE FROM app.reports",
    "DELETE FROM app.clauses",
    "DELETE FROM app.notifications",
    "DELETE FROM app.analyses",
    "DELETE FROM app.download_logs WHERE resource_type IN (N'contract', N'document', N'report')",
    "DELETE FROM app.contract_documents",
    "DELETE FROM app.contract_parties",
    "DELETE FROM app.contracts",
]


def _apply_azure_overrides(settings: Settings) -> Settings:
    repo = Path(__file__).resolve().parents[1]
    state_path = repo / "secrets" / "azure-lidr-deploy.state.env"
    if not state_path.is_file():
        return settings
    overrides: dict[str, str] = {}
    for line in state_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        overrides[key.strip()] = value.strip()
    sql_password = overrides.get("AZURE_SQL_ADMIN_PASSWORD")
    if not sql_password:
        return settings
    return settings.model_copy(
        update={
            "db_server": "legalrentlidr-sql.database.windows.net",
            "db_name": "LegalRentAI",
            "db_user": "legalrentadmin",
            "db_password": sql_password,
            "db_driver": "ODBC Driver 18 for SQL Server",
            "db_trusted_connection": False,
        }
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Purge all contracts from Legal Rent AI database.")
    parser.add_argument(
        "--azure",
        action="store_true",
        help="Connect to Azure SQL in lidr (uses secrets/azure-lidr-deploy.state.env).",
    )
    args = parser.parse_args()

    settings = get_settings()
    if args.azure:
        settings = _apply_azure_overrides(settings)

    with get_connection(settings) as connection:
        cursor = connection.cursor()
        cursor.execute("SELECT COUNT(*) FROM app.contracts")
        (before,) = cursor.fetchone()
        print(f"Contracts to remove: {before} (server={settings.db_server})")

        if before == 0:
            print("Nothing to delete.")
            return 0

        for sql in _PURGE_STATEMENTS:
            cursor.execute(sql)
            print(f"  {cursor.rowcount:6d}  {sql.split()[2]}")

        cursor.execute("SELECT COUNT(*) FROM app.contracts")
        (after,) = cursor.fetchone()
        connection.commit()

    print(f"Done. Remaining contracts: {after}")
    return 0 if after == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
