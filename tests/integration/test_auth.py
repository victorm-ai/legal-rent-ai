#!/usr/bin/env python
"""Authentication module tests."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from auth.models import UserCredentials, PasswordHash, TokenPayload
from domain.entities import Role


def test_password_hash():
    print("=== Password hashing ===")

    password = "secure_password123"
    hash_result = PasswordHash.generate(password)

    assert hash_result.verify(password)
    print("Correct password verification: PASSED")

    assert not hash_result.verify("wrong_password")
    print("Wrong password rejection: PASSED")
    print()


def test_auth_service():
    print("=== Auth service ===")

    import uuid

    from auth.service import AuthService

    auth_service = AuthService()

    result = auth_service.login(
        UserCredentials(email="abogado@contractes.com", password="abogado123")
    )
    assert result.success
    assert result.token is not None
    print(f"Login successful: {result.user.email} ({result.user.role.value})")

    wrong = auth_service.login(
        UserCredentials(email="abogado@contractes.com", password="wrong")
    )
    assert not wrong.success
    print("Invalid password rejected: PASSED")

    missing = auth_service.login(
        UserCredentials(email="missing@contractes.com", password="any")
    )
    assert not missing.success
    print("Unknown user rejected: PASSED")

    unique_email = f"new-{uuid.uuid4().hex[:8]}@contractes.com"
    register = auth_service.register(
        email=unique_email,
        name="New User",
        role=Role.CLIENT,
        password="newpassword123",
    )
    assert register.success
    print(f"Registration successful: {register.user.email}")

    duplicate = auth_service.register(
        email=unique_email,
        name="Duplicate",
        role=Role.CLIENT,
        password="other",
    )
    assert not duplicate.success
    print("Duplicate registration rejected: PASSED")
    print()


def test_token_generation():
    print("=== JWT tokens ===")

    from auth.token import JWTTransformer
    from config.settings import get_settings

    transformer = JWTTransformer(secret_key=get_settings().secret_key)
    payload = TokenPayload.create(
        user_id="test-user-001",
        email="test@contractes.com",
        role=Role.CLIENT,
    )

    token_str = transformer.encode(payload)
    decoded = transformer.decode(token_str)

    assert decoded is not None
    assert decoded.user_id == payload.user_id
    print("Token encode/decode: PASSED")

    assert transformer.decode("invalid.token.here") is None
    print("Invalid token rejected: PASSED")
    print()


def main():
    print("=" * 60)
    print("Legal Rent AI - Authentication Tests")
    print("=" * 60)
    print()

    try:
        test_password_hash()
        test_auth_service()
        test_token_generation()
        print("=" * 60)
        print("ALL TESTS PASSED")
        print("=" * 60)
        return 0
    except AssertionError as e:
        print(f"\nTest failed: {e}")
        return 1
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
