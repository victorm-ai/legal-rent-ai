#!/usr/bin/env python
"""Helper script to start the backend development server."""

import sys
import os

script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)


def install_dependencies():
    """Install missing dependencies if needed."""
    print("Checking dependencies...")

    try:
        import uvicorn
        import fastapi
        import jwt
        import pydantic
        print("All dependencies are installed.")
        return True
    except ImportError as e:
        print(f"Missing dependency: {e}")
        print("Installing dependencies...")

        import subprocess
        packages = [
            "PyJWT>=2.8.0",
            "fastapi>=0.104.0",
            "uvicorn[standard]>=0.24.0",
            "pydantic>=2.5.0",
            "python-dotenv>=1.0.0",
        ]
        result = subprocess.run([sys.executable, "-m", "pip", "install", *packages])

        if result.returncode != 0:
            print("Failed to install dependencies.")
            return False

        print("Dependencies installed successfully.")
        return True


def main():
    print("=" * 60)
    print("Legal Rent AI - Backend")
    print("=" * 60)

    if not install_dependencies():
        sys.exit(1)

    print("\nStarting server at http://localhost:8000")
    print("Press Ctrl+C to stop")
    print("Swagger UI: http://localhost:8000/docs\n")

    import uvicorn

    try:
        uvicorn.run(
            "api.app:app",
            host="0.0.0.0",
            port=8000,
            reload=True,
        )
    except KeyboardInterrupt:
        print("\nServer stopped.")
        sys.exit(0)


if __name__ == "__main__":
    main()
