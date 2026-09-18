"""Application configuration."""

from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = BACKEND_ROOT.parent

load_dotenv(REPO_ROOT / ".env", override=True)


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=str(REPO_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    host: str = "0.0.0.0"
    port: int = 8000

    secret_key: str = "your-secret-key-change-in-production"
    token_expiration_minutes: int = 60

    db_server: str = "localhost"
    db_name: str = "LegalRentAI"
    db_driver: str = "ODBC Driver 17 for SQL Server"
    db_trusted_connection: bool = True
    db_user: str = ""
    db_password: str = ""

    max_upload_size_bytes: int = 25 * 1024 * 1024
    soft_delete_retention_days: int = 365
    ocr_enabled: bool = False
    ocr_max_pages: int = 30
    max_extraction_pdf_pages: int = 100

    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-3-5-haiku-20241022"
    llm_provider: str = "openai"  # openai, anthropic, heuristic, azure, local
    azure_openai_endpoint: str = ""
    azure_openai_api_key: str = ""
    azure_openai_api_version: str = "2024-02-15-preview"
    azure_openai_deployment: str = "gpt-4o-mini"
    local_llm_base_url: str = "http://localhost:11434"
    local_llm_model: str = "llama3.2"
    lease_type: str = "residential"
    analysis_async: bool = False
    confidence_review_threshold: float = 0.8
    analysis_sla_ms: int = 60000
    force_https: bool = False
    download_token_ttl_seconds: int = 300
    azure_key_vault_url: str = ""
    llm_max_input_chars: int = 120000
    legal_cag_enabled: bool = True
    legal_cag_corpus_path: str = "docs/legal-sources/cag-corpus-v1.md"
    guardrails_enabled: bool = True
    guardrails_lease_min_score: float = 0.22

    reports_storage_dir: str = "storage/reports"
    llm_responses_dir: str = "storage/llm-runs"

    # Offline LLM evaluation (evals/ — separate from production storage)
    eval_runs_dir: str = "evals/runs"
    eval_judge_provider: str = "openai"
    eval_judge_openai_model: str = "gpt-4o"
    eval_judge_anthropic_model: str = "claude-3-5-sonnet-20241022"
    app_base_url: str = "http://localhost:8000"
    frontend_base_url: str = "http://localhost:3000"

    azure_communication_connection_string: str = ""
    azure_communication_sender_address: str = "DoNotReply@legalrentai.local"
    signing_schedule_slot_minutes: int = 45
    signing_schedule_weeks_ahead: int = 4
    signing_schedule_days_ahead: int = 30

    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "noreply@legalrentai.local"
    smtp_use_tls: bool = True
    notification_dev_mode: bool = True  # log email instead of SMTP when no host

    def reports_path(self) -> Path:
        path = Path(self.reports_storage_dir)
        if not path.is_absolute():
            path = BACKEND_ROOT / path
        path.mkdir(parents=True, exist_ok=True)
        return path

    def llm_responses_path(self) -> Path:
        path = Path(self.llm_responses_dir)
        if not path.is_absolute():
            path = BACKEND_ROOT / path
        path.mkdir(parents=True, exist_ok=True)
        return path

    def eval_runs_path(self) -> Path:
        path = Path(self.eval_runs_dir)
        if not path.is_absolute():
            path = REPO_ROOT / path
        path.mkdir(parents=True, exist_ok=True)
        return path

    def build_connection_string(self) -> str:
        """Build a pyodbc connection string for SQL Server."""
        parts = [
            f"DRIVER={{{self.db_driver}}}",
            f"SERVER={self.db_server}",
            f"DATABASE={self.db_name}",
            "TrustServerCertificate=yes",
        ]
        if self.db_trusted_connection:
            parts.append("Trusted_Connection=yes")
        else:
            parts.append(f"UID={self.db_user}")
            parts.append(f"PWD={self.db_password}")
        return ";".join(parts)


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings()
