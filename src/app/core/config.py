"""Application configuration using Pydantic Settings."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ──────────────────────────────────────────────
    app_env: str = "development"
    app_name: str = "OSINT Intelligence API"
    app_version: str = "0.1.0"
    debug: bool = False

    # ── Database ─────────────────────────────────────────────────
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/osint"
    db_pool_size: int = 5
    db_max_overflow: int = 10

    # ── Redis ────────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"

    # ── OSINT Execution ──────────────────────────────────────────
    request_timeout: int = 30
    max_concurrent_providers: int = 5

    # ── Feature Flags ────────────────────────────────────────────
    enable_auth: bool = Field(
        default=False,
        description="Toggle API key authentication on/off",
    )
    enable_rate_limiting: bool = Field(
        default=False,
        description="Toggle rate limiting on/off",
    )
    enable_background_workers: bool = Field(
        default=False,
        description="Toggle Redis-backed background workers on/off",
    )
    enable_database: bool = Field(
        default=False,
        description="Toggle PostgreSQL persistence on/off",
    )

    # ── Authentication (only used when enable_auth=True) ─────────
    api_keys: list[str] = Field(
        default_factory=list,
        description="Comma-separated list of valid API keys",
    )
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"

    # ── Rate Limiting (only used when enable_rate_limiting=True) ─
    rate_limit_requests: int = 30
    rate_limit_window_seconds: int = 60

    # ── PhoneInfoga ──────────────────────────────────────────────
    phoneinfoga_url: str = "http://localhost:5000"

    # ── Logging ──────────────────────────────────────────────────
    log_level: str = "INFO"
    log_format: str = "json"


# Singleton settings instance
settings = Settings()
