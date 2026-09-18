"""Document retention policy tests (RF-54)."""

import os
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from auth.models import UserCredentials
from auth.service import AuthService
from config.settings import Settings, get_settings
from data.database import get_connection
from services.contract_service import ContractService
from services.retention_service import RetentionService
from test_contracts import _minimal_pdf


def test_retention_policy_defaults():
    service = RetentionService(settings=Settings(soft_delete_retention_days=180))
    policy = service.get_policy()
    assert policy.soft_delete_retention_days == 180
    assert "180 days" in policy.description


def test_retention_purge_flow():
    auth_service = AuthService()
    login = auth_service.login(
        UserCredentials(email="code.zemoreno@gmail.com", password="cliente123")
    )
    assert login.success

    current_user = {
        "user_id": login.user.id,
        "email": login.user.email,
        "role": login.user.role,
    }

    contract_service = ContractService()
    contract = contract_service.create_contract_with_document(
        current_user=current_user,
        perspective="tenant",
        validated_document=contract_service.validate_upload(
            "retention-test.pdf",
            _minimal_pdf(),
            "application/pdf",
        ),
        title=f"Retention Test {uuid.uuid4().hex[:8]}",
    )
    contract_service.delete_contract(current_user, contract.id)

    settings = get_settings()
    with get_connection(settings) as connection:
        cursor = connection.cursor()
        cursor.execute(
            """
            UPDATE app.contracts
            SET deleted_at = DATEADD(day, ?, SYSUTCDATETIME())
            WHERE id = ?
            """,
            -(settings.soft_delete_retention_days + 10),
            contract.id,
        )
        connection.commit()

    retention_service = RetentionService(settings=settings)
    status = retention_service.get_status()
    assert status.purge_eligible_count >= 1

    result = retention_service.purge_expired()
    assert result.purged_contracts >= 1

    with get_connection(settings) as connection:
        cursor = connection.cursor()
        cursor.execute("SELECT 1 FROM app.contracts WHERE id = ?", contract.id)
        assert cursor.fetchone() is None


def main():
    print("=" * 60)
    print("Legal Rent AI - Retention Policy Tests")
    print("=" * 60)
    print()

    try:
        test_retention_policy_defaults()
        print("Retention policy defaults: PASSED")

        test_retention_purge_flow()
        print("Retention purge flow: PASSED")

        print()
        print("=" * 60)
        print("ALL TESTS PASSED")
        print("=" * 60)
        return 0
    except Exception as exc:
        print(f"\nTest failed: {exc}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
