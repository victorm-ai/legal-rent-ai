"""SQL Server repository for app.download_logs (RF-55, RNF-49)."""

from config.settings import Settings, get_settings
from data.database import get_connection


class DownloadLogRepository:
    """Persists download audit records."""

    def __init__(self, settings: Settings | None = None):
        self._settings = settings or get_settings()

    def log_download(self, user_id: str, resource_type: str, resource_id: str) -> None:
        """Insert a download log entry."""
        with get_connection(self._settings) as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                INSERT INTO app.download_logs (user_id, resource_type, resource_id)
                VALUES (?, ?, ?)
                """,
                user_id,
                resource_type,
                resource_id,
            )
            connection.commit()
