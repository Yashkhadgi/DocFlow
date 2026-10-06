from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "local"
    secret_key: str = "change-me"
    access_token_expire_minutes: int = 1440
    cors_origins: str = "http://localhost:5173"

    database_url: str = "postgresql+psycopg2://docflow:docflow@db:5432/docflow"
    redis_url: str = "redis://redis:6379/0"

    s3_endpoint_url: str = "http://minio:9000"
    s3_region: str = "auto"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket: str = "docflow-documents"
    presigned_url_expires_seconds: int = 300

    max_file_size_mb: int = 10
    max_files_per_upload: int = 20

    anthropic_api_key: str | None = None
    llm_model: str = "claude-sonnet-5-5"
    confidence_threshold: float = 0.85
    use_stub_extractor: bool = True

    job_max_attempts: int = 3
    force_fail_filename_contains: str | None = Field(default="failme")
    force_fail_until_attempt: int = 0

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
