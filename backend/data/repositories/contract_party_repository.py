"""SQL Server repository for app.contract_parties (RF-12)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from config.settings import Settings, get_settings
from data.database import get_connection
from llm.party_extraction import build_party_records


class ContractPartyRepository:
    def __init__(self, settings: Settings | None = None):
        self._settings = settings or get_settings()

    def replace_for_contract(
        self,
        contract_id: str,
        extracted_fields: list[dict[str, Any]],
    ) -> int:
        """Merge extracted party fields into contract-level party records."""
        new_parties = build_party_records(extracted_fields)
        if not new_parties:
            return len(self.list_by_contract(contract_id))

        existing = {item["party_type"]: item for item in self.list_by_contract(contract_id)}
        for party in new_parties:
            existing[party["party_type"]] = party
        merged = list(existing.values())

        with get_connection(self._settings) as connection:
            cursor = connection.cursor()
            cursor.execute(
                "DELETE FROM app.contract_parties WHERE contract_id = ?",
                contract_id,
            )
            for party in merged:
                cursor.execute(
                    """
                    INSERT INTO app.contract_parties (
                        contract_id, party_type, name, legal_representative, confidence, source_page
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    contract_id,
                    party["party_type"],
                    party["name"],
                    party.get("legal_representative"),
                    party.get("confidence"),
                    party.get("source_page"),
                )
            connection.commit()
        return len(merged)

    def list_by_contract(self, contract_id: str) -> list[dict[str, Any]]:
        with get_connection(self._settings) as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                SELECT party_type, name, legal_representative, confidence, source_page
                FROM app.contract_parties
                WHERE contract_id = ?
                ORDER BY party_type
                """,
                contract_id,
            )
            rows = cursor.fetchall()
        return [
            {
                "party_type": row[0],
                "name": row[1],
                "legal_representative": row[2],
                "confidence": float(row[3]) if row[3] is not None else None,
                "source_page": row[4],
            }
            for row in rows
        ]

    def list_by_contract_ids(self, contract_ids: list[str]) -> dict[str, list[dict[str, Any]]]:
        if not contract_ids:
            return {}

        placeholders = ",".join("?" for _ in contract_ids)
        with get_connection(self._settings) as connection:
            cursor = connection.cursor()
            cursor.execute(
                f"""
                SELECT contract_id, party_type, name, legal_representative, confidence, source_page
                FROM app.contract_parties
                WHERE contract_id IN ({placeholders})
                ORDER BY contract_id, party_type
                """,
                *contract_ids,
            )
            rows = cursor.fetchall()

        grouped: dict[str, list[dict[str, Any]]] = {contract_id: [] for contract_id in contract_ids}
        for row in rows:
            contract_id = self._normalize_id(row[0])
            grouped.setdefault(contract_id, []).append(
                {
                    "party_type": row[1],
                    "name": row[2],
                    "legal_representative": row[3],
                    "confidence": float(row[4]) if row[4] is not None else None,
                    "source_page": row[5],
                }
            )
        return grouped

    @staticmethod
    def _normalize_id(value) -> str:
        return str(value) if isinstance(value, UUID) else value
