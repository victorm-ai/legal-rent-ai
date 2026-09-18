"""
API module for the contract analyzer.
"""

from api.app import app


def create_application():
    """Create and return the FastAPI application."""
    return app


__all__ = ["app", "create_application"]
