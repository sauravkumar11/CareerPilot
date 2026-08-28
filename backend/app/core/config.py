"""
Application configuration.

All configuration is sourced from environment variables (see .env.example).
Nothing sensitive is hard-coded. Settings are cached as a singleton via
`get_settings()` so the environment is only parsed once per process.
"""
from functools import lru_cache
from typing import List

from pydantic import AnyUrl, Field, field_validator
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
    BACKEND_CORS_ORIGINS: List[str] = Field(default_factory=lambda: ["http://localhost:3000"])

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def _split_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

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
    ALLOWED_RESUME_MIME_TYPES: List[str] = Field(
        default_factory=lambda: [
            "application/pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ]
    )

    # --- AI-call rate limiting (per user, per endpoint family) ---
    AI_CALL_RATE_LIMIT_PER_HOUR: int = Field(default=20)


@lru_cache
def get_settings() -> Settings:
    return Settings()
