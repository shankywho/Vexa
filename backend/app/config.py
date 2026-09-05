"""Application configuration.

Configuration is loaded from environment variables (prefixed ``VEXA_``) and
optionally a ``.env`` file. All settings have sensible local-development
defaults so the backend runs out of the box.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for the ClosePilot backend."""

    model_config = SettingsConfigDict(
        env_prefix="VEXA_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application
    app_name: str = "ClosePilot Backend"
    environment: str = Field(default="development", description="development | test | production")
    debug: bool = False
    api_prefix: str = "/api"

    # Database
    db_url: str = "postgresql+asyncpg://localhost:5432/vexa"
    db_echo: bool = False
    db_pool_size: int = 10
    db_max_overflow: int = 20

    # Auth (foundation only - real auth lands in a later phase)
    auth_enabled: bool = False
    # When auth is disabled, requests run with this default tenant context.
    default_tenant_company_id: int | None = None

    # Seed
    seed_data_dir: str = "app/data"
    seed_deterministic: bool = True
    seed_random_seed: int = 42

    # LLM Investigation Agent
    llm_provider: str = Field(
        default="deterministic", description="deterministic | openai | anthropic | gemini | custom"
    )
    llm_model: str = Field(default="gpt-4o", description="Model identifier for external LLM calls")
    llm_api_key: str | None = Field(default=None, description="API key for external LLM calls")
    llm_base_url: str | None = Field(default=None, description="Base URL for external LLM calls")
    llm_timeout_seconds: float = Field(default=30.0, description="Timeout for external LLM calls")


@lru_cache
def get_settings() -> Settings:
    """Return the cached application settings (env-aware)."""
    return Settings()
