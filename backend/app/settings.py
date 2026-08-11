"""Application settings loaded from environment / ``.env`` (M01 + M02).

M02 widened the schema to cover JWT verification. The key invariant
is *no secrets in the repo*: production deployments inject
``JWT_SIGNING_PUBLIC_KEY`` (PEM) or ``JWT_JWKS_URL`` via the
deployment secret store (NFR-004). Local dev uses the ``.env`` file,
which is gitignored.

Traceability: NFR-004, NFR-006.
"""

from __future__ import annotations

from typing import Any, cast

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Process-wide settings, populated from env / ``.env``."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Process identity (M01) --------------------------------------------
    app_name: str = Field(default="saie-api", description="Service name.")
    environment: str = Field(
        default="development",
        description="Deployment environment (development|staging|production).",
    )
    log_level: str = Field(
        default="INFO",
        description="Root log level (DEBUG|INFO|WARNING|ERROR).",
    )

    # --- OTel (M01) ---------------------------------------------------------
    otel_exporter_otlp_endpoint: str | None = Field(
        default=None,
        description="OTLP collector endpoint. None disables remote export.",
    )
    otel_service_namespace: str = Field(
        default="saie",
        description="OTel ``service.namespace`` resource attribute.",
    )

    # --- JWT verification (M02) ---------------------------------------------
    jwt_issuer: str = Field(
        default="https://saie.local/realms/saie",
        description="Expected ``iss`` claim (Keycloak realm URL in prod).",
    )
    jwt_audience: str = Field(
        default="saie-api",
        description="Expected ``aud`` claim (matches the API client ID).",
    )
    jwt_jwks_url: str | None = Field(
        default=None,
        description="URL to the JWKS document. Empty uses the offline path.",
    )
    jwt_jwks_inline: str | None = Field(
        default=None,
        description=(
            "Inline JWKS JSON for offline / dev use. Production MUST use "
            "``JWT_JWKS_URL``. "
        ),
    )

    @field_validator("jwt_audience")
    @classmethod
    def _audience_non_empty(cls, value: str) -> str:
        if not value:
            raise ValueError("JWT_AUDIENCE must not be empty")
        return value

    def resolved_jwks(self) -> dict[str, Any] | str | None:
        """Return the JWKS for the verifier.

        Returns the inline dict for offline mode (dev/test), the URL
        string for live Keycloak, or ``None`` if neither is set (which
        would only happen in a misconfigured deployment).
        """
        if self.jwt_jwks_inline:
            import json

            return cast("dict[str, Any]", json.loads(self.jwt_jwks_inline))
        return self.jwt_jwks_url


def get_settings() -> Settings:
    """Return a freshly-evaluated :class:`Settings` instance."""
    return Settings()
