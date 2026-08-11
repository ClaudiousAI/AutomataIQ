"""Application settings loaded from environment / ``.env`` (M01).

Single source of truth for service boundaries. Pydantic v2 ensures every
field is type-checked at import time — a missing env var crashes the
process on startup, not deep in a worker.

M01 scope is intentionally narrow: only what the FastAPI app factory
needs. Real secrets (DB password, LLM keys, …) come online in later
modules and are added here as their owning module lands.

Traceability: NFR-004 (no secrets committed; env injection only),
NFR-006 (typed config contract at every service boundary).
"""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Process-wide settings, populated from env / ``.env``.

    ``env_file`` is set to the project-root ``.env`` (the python-dotenv
    convention). Real environment variables ALWAYS take precedence over
    ``.env`` values — Pydantic enforces that.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Process identity --------------------------------------------------
    app_name: str = Field(default="saie-api", description="Service name.")
    environment: str = Field(
        default="development",
        description="Deployment environment (development|staging|production).",
    )
    log_level: str = Field(
        default="INFO",
        description="Root log level (DEBUG|INFO|WARNING|ERROR).",
    )

    # --- OTel --------------------------------------------------------------
    otel_exporter_otlp_endpoint: str | None = Field(
        default=None,
        description="OTLP collector endpoint. None disables remote export.",
    )
    otel_service_namespace: str = Field(
        default="saie",
        description="OTel ``service.namespace`` resource attribute.",
    )


def get_settings() -> Settings:
    """Return a freshly-evaluated :class:`Settings` instance.

    A function (not a module-level singleton) means tests can mutate
    ``os.environ`` between calls and the new values are picked up.
    """
    return Settings()
