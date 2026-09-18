"""Soft-delete Lawyer Edit Test contracts."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from auth.models import UserCredentials
from auth.service import AuthService
from config.settings import get_settings
from data.database import get_connection
from services.contract_service import ContractService

CONTRACT_TITLES = (
    "Lawyer Edit Test be14ffda",
    "Lawyer Edit Test 79b804bd",
)


def _client_user() -> dict:
    auth = AuthService()
    login = auth.login(
        UserCredentials(email="cliente@contractes.com", password="cliente123")
    )
    if login.success:
        return {
            "user_id": login.user.id,
            "email": login.user.email,
            "role": login.user.role,
        }
    raise RuntimeError("Could not authenticate the demo client user")


def main() -> int:
    with get_connection(get_settings()) as connection:
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT id, title
            FROM app.contracts
            WHERE title IN (?, ?) AND is_deleted = 0
            """,
            *CONTRACT_TITLES,
        )
        rows = cursor.fetchall()

    if not rows:
        print("No matching contracts found.")
        return 0

    client = _client_user()
    service = ContractService()

    for contract_id, title in rows:
        service.delete_contract(client, str(contract_id))
        print(f"Deleted: {title} ({contract_id})")

    with get_connection(get_settings()) as connection:
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT id, title, is_deleted
            FROM app.contracts
            WHERE title IN (?, ?)
            """,
            *CONTRACT_TITLES,
        )
        print("Remaining rows:", cursor.fetchall())

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
