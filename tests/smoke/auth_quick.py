#!/usr/bin/env python
"""Quick authentication smoke tests."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

def main():
    print("Running authentication smoke tests...")

    try:
        from auth.models import UserCredentials
        from auth.service import AuthService

        auth_service = AuthService()
        result = auth_service.login(
            UserCredentials(email="code.zemoreno@gmail.com", password="cliente123")
        )

        if not result.success:
            print(f"Login failed: {result.message}")
            return 1

        print("Login successful")
        print(f"  User: {result.user.email}")
        print(f"  Role: {result.user.role.value}")

        from auth.token import JWTTransformer
        from config.settings import get_settings

        transformer = JWTTransformer(secret_key=get_settings().secret_key)
        payload = transformer.decode(result.token.access_token)

        if payload is None:
            print("Token validation failed")
            return 1

        print("Token valid")
        print(f"  User ID: {payload.user_id}")

        wrong = auth_service.login(
            UserCredentials(email="code.zemoreno@gmail.com", password="wrong-password")
        )
        if wrong.success:
            print("Expected login to fail with wrong password")
            return 1

        print("Invalid credentials rejected correctly")
        print("\nAll smoke tests passed")
        return 0

    except Exception as e:
        print(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
