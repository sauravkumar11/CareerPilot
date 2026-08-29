"""
Application configuration.

All configuration is sourced from environment variables (see .env.example).
Nothing sensitive is hard-coded. Settings are cached as a singleton via
`get_settings()` so the environment is only parsed once per process.
"""
from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- General ---
    ENVIRONMENT: str = Field(default="development")
    PROJECT_NAME: str = "CareerPilot AI"
    API_V1_PREFIX: str = "/api/v1"
    DEBUG: bool = False

    # --- Security ---
    SECRET_KEY: str = Field(..., description="Used to sign JWTs. Must be set via env in prod.")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24h
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 30  # 30d
    JWT_ALGORITHM: str = "HS256"

    # --- CORS ---
    # Deliberately a plain str, not List[str]: pydantic-settings attempts to
    # JSON-decode any List[...]-typed env var before custom field_validators
    # ever run, so a bare comma-separated string here (e.g. from a real
    # deployment's env var, not a JSON array) raised a hard-to-diagnose
    # SettingsError at import time — reproduced and confirmed against the
    # exact installed pydantic-settings version. Use `.cors_origins` (below)
    # to get the parsed list.
    BACKEND_CORS_ORIGINS: str = Field(default="http://localhost:3000")

    @property
    def cors_origins(self) -> List[str]:
        return [origin.strip() for origin in self.BACKEND_CORS_ORIGINS.split(",") if origin.strip()]

    # --- Database ---
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://careerpilot:careerpilot@localhost:5432/careerpilot",
    )

    # --- Redis / Celery ---
    REDIS_URL: str = Field(default="redis://localhost:6379/0")
    CELERY_BROKER_URL: str = Field(default="redis://localhost:6379/1")
    CELERY_RESULT_BACKEND: str = Field(default="redis://localhost:6379/2")

    # --- AI ---
    ANTHROPIC_API_KEY: str = Field(default="")
    ANTHROPIC_MODEL: str = Field(default="claude-sonnet-4-6")

    # --- Rate limiting ---
    RATE_LIMIT_PER_MINUTE: int = 60

    # --- Job sync ---
    JOB_SYNC_INTERVAL_MINUTES: int = 60
    JOB_MAX_AGE_DAYS: int = 30

    # --- Storage / uploads ---
    STORAGE_ROOT: str = Field(default="/app/storage")
    MAX_UPLOAD_SIZE_BYTES: int = Field(default=5 * 1024 * 1024)  # 5MB
    # Same List[str]-via-env-var pitfall as BACKEND_CORS_ORIGINS above —
    # kept as a plain comma-separated str for the same reason.
    ALLOWED_RESUME_MIME_TYPES: str = Field(
        default="application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )

    @property
    def allowed_resume_mime_types(self) -> List[str]:
        return [t.strip() for t in self.ALLOWED_RESUME_MIME_TYPES.split(",") if t.strip()]

    # --- AI-call rate limiting (per user, per endpoint family) ---
    AI_CALL_RATE_LIMIT_PER_HOUR: int = Field(default=20)


@lru_cache
def get_settings() -> Settings:
    return Settings()
