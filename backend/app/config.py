"""Application configuration.

Configuration is loaded from environment variables (prefixed ``VEXA_``) and
optionally a ``.env`` file. All settings have sensible local-development
defaults so the backend runs out of the box.
"""

from __future__ import annotations

import os
import re
from functools import lru_cache
from typing import Self

from pydantic import AliasChoices, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class ConfigurationError(ValueError):
    """Raised when configuration violates architectural or governance constraints."""

    pass


DEFAULT_AGENT_PROVIDER_ROUTING: dict[str, dict[str, str]] = {
    "investigation_agent": {"primary": "mistral", "fallback": "groq"},
    "verification_agent": {"primary": "groq", "fallback": "gemini"},
    "close_controller": {"primary": "gemini", "fallback": "mistral"},
    "reconciliation_agent": {"primary": "groq", "fallback": "mistral"},
    "financial_analyst": {"primary": "groq", "fallback": "mistral"},
    "action_agent": {"primary": "groq", "fallback": "deterministic"},
}

AGENT_PROVIDER_ROUTING = DEFAULT_AGENT_PROVIDER_ROUTING


def validate_routing_independence(
    routing: dict[str, dict[str, str]],
    environment: str = "production",
    strict: bool = False,
) -> None:
    """Ensure investigation_agent and verification_agent never share primary provider."""
    inv_primary = routing.get("investigation_agent", {}).get("primary")
    ver_primary = routing.get("verification_agent", {}).get("primary")
    if inv_primary and ver_primary and inv_primary == ver_primary:
        if environment == "production" or strict:
            raise ConfigurationError(
                f"ConfigurationError: investigation_agent and verification_agent cannot share "
                f"primary provider '{inv_primary}' (violation of independent verification guarantee)."
            )


class Settings(BaseSettings):
    """Runtime configuration for the ClosePilot backend."""

    model_config = SettingsConfigDict(
        env_prefix="VEXA_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    # Application
    app_name: str = "ClosePilot Backend"
    environment: str = Field(
        default="development",
        validation_alias=AliasChoices("VEXA_ENVIRONMENT", "ENVIRONMENT", "ENV"),
        description="development | test | production",
    )
    debug: bool = False
    api_prefix: str = "/api"

    # CORS
    cors_origins: list[str] = Field(
        default=[
            "https://vexa-autonomous.vercel.app",
            "http://localhost:3000",
            "http://localhost:5173",
            "http://localhost:8000",
        ],
        description="Allowed CORS origins",
    )

    # Database
    db_url: str = Field(
        default="postgresql+asyncpg://localhost:5432/vexa",
        validation_alias=AliasChoices("DATABASE_URL", "VEXA_DB_URL"),
        description="PostgreSQL connection string with asyncpg driver",
    )
    db_echo: bool = False
    db_pool_size: int = 10
    db_max_overflow: int = 20

    @field_validator("app_name", mode="before")
    @classmethod
    def clean_app_name(cls, v: Any) -> str:
        if isinstance(v, str):
            return v.strip().strip("\"'")
        return str(v)

    @field_validator("seed_random_seed", "db_pool_size", "db_max_overflow", "investigation_max_steps", mode="before")
    @classmethod
    def clean_int_fields(cls, v: Any) -> int:
        if isinstance(v, str):
            m = re.search(r"-?\d+", v)
            if m:
                return int(m.group(0))
        return int(v) if v is not None else 42

    @field_validator("investigation_max_seconds", "llm_timeout_seconds", mode="before")
    @classmethod
    def clean_float_fields(cls, v: Any) -> float:
        if isinstance(v, str):
            m = re.search(r"-?\d+(\.\d+)?", v)
            if m:
                return float(m.group(0))
        return float(v) if v is not None else 30.0

    @field_validator("db_url", mode="before")
    @classmethod
    def normalize_db_url(cls, v: str | None) -> str:
        cloud_url = os.environ.get("DATABASE_URL")
        if cloud_url and "localhost" not in cloud_url and (not v or "localhost" in str(v)):
            v = cloud_url
        if not v:
            return "postgresql+asyncpg://localhost:5432/vexa"
        url = str(v).strip()
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgresql://") and not url.startswith("postgresql+asyncpg://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        if "sslmode=require" in url:
            url = url.replace("sslmode=require", "ssl=require")
        elif "sslmode=prefer" in url:
            url = url.replace("sslmode=prefer", "ssl=prefer")
        elif any(cloud_host in url for cloud_host in [".render.com", ".neon.tech", ".supabase.co"]):
            if "ssl=" not in url and "sslmode=" not in url:
                delimiter = "&" if "?" in url else "?"
                url = f"{url}{delimiter}ssl=require"
        return url

    # Auth (foundation only - real auth lands in a later phase)
    auth_enabled: bool = False
    # When auth is disabled, requests run with this default tenant context.
    default_tenant_company_id: int | None = None

    # Seed
    seed_data_dir: str = "app/data"
    seed_deterministic: bool = True
    seed_random_seed: int = 42

    # Multi-Provider LLM Credentials & Endpoints
    groq_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("VEXA_GROQ_API_KEY", "GROQ_API_KEY"),
        description="API key for Groq LLM provider",
    )
    groq_model: str = Field(
        default="qwen/qwen3.8-27b",
        validation_alias=AliasChoices("VEXA_GROQ_MODEL", "GROQ_MODEL"),
        description="Model identifier for Groq provider",
    )
    groq_base_url: str = Field(
        default="https://api.groq.com/openai/v1",
        validation_alias=AliasChoices("VEXA_GROQ_BASE_URL", "GROQ_BASE_URL"),
        description="Base URL for Groq API",
    )

    mistral_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("VEXA_MISTRAL_API_KEY", "MISTRAL_API_KEY"),
        description="API key for Mistral LLM provider",
    )
    mistral_model: str = Field(
        default="codestral-latest",
        validation_alias=AliasChoices("VEXA_MISTRAL_MODEL", "MISTRAL_MODEL"),
        description="Model identifier for Mistral provider",
    )
    mistral_base_url: str = Field(
        default="https://api.mistral.ai/v1",
        validation_alias=AliasChoices("VEXA_MISTRAL_BASE_URL", "MISTRAL_BASE_URL"),
        description="Base URL for Mistral API",
    )

    gemini_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("VEXA_GEMINI_API_KEY", "GEMINI_API_KEY"),
        description="API key for Gemini LLM provider",
    )
    gemini_model: str = Field(
        default="gemini-3.5-flash-lite",
        validation_alias=AliasChoices("VEXA_GEMINI_MODEL", "GEMINI_MODEL"),
        description="Model identifier for Gemini provider",
    )
    gemini_base_url: str = Field(
        default="https://generativelanguage.googleapis.com/v1beta/models",
        validation_alias=AliasChoices("VEXA_GEMINI_BASE_URL", "GEMINI_BASE_URL"),
        description="Base URL for Gemini API",
    )

    # Agent Provider Routing
    agent_provider_routing: dict[str, dict[str, str]] = Field(
        default_factory=lambda: dict(DEFAULT_AGENT_PROVIDER_ROUTING),
        description="Routing configuration for agents to primary and fallback LLM providers",
    )

    # Legacy / Generic LLM Provider (backward compatibility)
    llm_provider: str = Field(
        default="deterministic", description="deterministic | openai | anthropic | gemini | custom"
    )
    llm_model: str = Field(default="gpt-4o", description="Model identifier for external LLM calls")
    llm_api_key: str | None = Field(default=None, description="API key for external LLM calls")
    llm_base_url: str | None = Field(default=None, description="Base URL for external LLM calls")
    llm_timeout_seconds: float = Field(default=30.0, description="Timeout for external LLM calls")

    # Investigation Agent Circuit Breaker
    investigation_max_steps: int = Field(
        default=15, description="Maximum agent steps before circuit breaker trips"
    )
    investigation_max_seconds: float = Field(
        default=30.0, description="Maximum wall-clock seconds for an investigation"
    )

    @model_validator(mode="after")
    def validate_verification_independence(self) -> Self:
        validate_routing_independence(
            self.agent_provider_routing,
            environment=self.environment,
            strict=False,
        )
        return self


@lru_cache
def get_settings() -> Settings:
    """Return the cached application settings (env-aware)."""
    return Settings()
