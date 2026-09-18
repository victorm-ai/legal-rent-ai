"""Database connection utilities."""

from contextlib import contextmanager
from typing import Generator

import pyodbc

from config.settings import Settings, get_settings


@contextmanager
def get_connection(settings: Settings | None = None) -> Generator[pyodbc.Connection, None, None]:
    """Open a SQL Server connection and close it when done."""
    settings = settings or get_settings()
    connection = pyodbc.connect(settings.build_connection_string())
    try:
        yield connection
    finally:
        connection.close()
