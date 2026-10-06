from __future__ import annotations

from functools import lru_cache
import logging
import os

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger("docflow.config")

REQUIRED_ENV_VARS = [
    "DATABASE_URL",
    "REDIS_URL",
    "SECRET_KEY",
    "CORS_ORIGINS",
    "S3_ENDPOINT_URL",
    "S3_ACCESS_KEY",
    "S3_SECRET_KEY",
    "S3_BUCKET",
    "ANTHROPIC_API_KEY",
]


class Settings(BaseSettings):
    app_env: str = "local"
    port: int = Field(default=8000, validation_alias="PORT")
    secret_key: str = "change-me"
    access_token_expire_minutes: int = 1440
    cors_origins: str = "http://localhost:5173"

    database_url: str = "postgresql+psycopg2://docflow:docflow@db:5432/docflow"
    redis_url: str = "redis://redis:6379/0"

    s3_endpoint_url: str = "http://minio:9000"
    s3_public_endpoint_url: str | None = None
    s3_region: str = "auto"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket: str = "docflow-documents"
    presigned_url_expires_seconds: int = 300

    max_file_size_mb: int = 10
    max_files_per_upload: int = 20

    anthropic_api_key: str | None = None
    llm_model: str = "claude-haiku-4-5-20251001"
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-3.1-flash-lite"
    gemini_fallback_enabled: bool = True
    llm_budget_usd: float = Field(default=0.15, gt=0)
    llm_max_input_tokens: int = Field(default=8000, ge=1)
    llm_max_output_tokens: int = Field(default=1024, ge=1, le=4096)
    llm_max_pdf_pages: int = Field(default=5, ge=1, le=100)
    confidence_threshold: float = 0.85
    use_stub_extractor: bool = True

    job_max_attempts: int = 3
    force_fail_filename_contains: str | None = Field(default="failme")
    force_fail_until_attempt: int = 0

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_database_url(cls, v: str) -> str:
        if isinstance(v, str):
            if v.startswith("postgres://"):
                return "postgresql+psycopg2://" + v[len("postgres://") :]
            if v.startswith("postgresql://") and not v.startswith("postgresql+"):
                return "postgresql+psycopg2://" + v[len("postgresql://") :]
        return v

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


def get_missing_env_vars() -> list[str]:
    """Return names of required environment variables that are missing or empty."""
    return [name for name in REQUIRED_ENV_VARS if not os.environ.get(name)]


def log_missing_env_vars() -> list[str]:
    """Log which environment variables are missing (names only, never values)."""
    missing = get_missing_env_vars()
    if missing:
        names = ", ".join(sorted(missing))
        logger.warning("Startup check: missing environment variables: %s", names)
        print(f"[STARTUP] Missing environment variables: {names}", flush=True)
    else:
        logger.info("Startup check: all required environment variables are set.")
        print("[STARTUP] All required environment variables are set.", flush=True)
    return missing


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
