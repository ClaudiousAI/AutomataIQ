"""Typed JWT claims at the service boundary (NFR-006).

This model is the contract every downstream module reads. Drift here
silently breaks tenant scoping (FR-057) and audit attribution
(FR-054) — so the model is intentionally narrow and rejects unknown
shapes loudly.

RFC 7519 §4.1 drives the field set:

- ``iss`` (issuer)
- ``sub`` (subject)
- ``aud`` (audience — string OR list, normalised to tuple here)
- ``exp`` (expiration — REQUIRED for M02)
- ``nbf`` (not-before)
- ``iat`` (issued-at)
- ``realm_access`` (Keycloak's nested object; we only consume ``.roles``)
- ``tenant_id`` (custom claim; M02 contract)
"""

from __future__ import annotations

from typing import Annotated, Any

from pydantic import BaseModel, Field, StringConstraints


#: ``aud`` is allowed to be a single string or a list. The model
#: normalises both into a tuple so downstream code has one shape to
#: check.
def _normalise_audience(value: Any) -> tuple[str, ...]:
    if isinstance(value, str):
        return (value,)
    if isinstance(value, list):
        return tuple(str(v) for v in value)
    return ()


class Claims(BaseModel):
    """Typed JWT claims, validated at the service boundary (NFR-006)."""

    # Identity ----------------------------------------------------------------
    subject: Annotated[str, StringConstraints(min_length=1)]
    preferred_username: str | None = None
    email: str | None = None

    # Token metadata ----------------------------------------------------------
    issuer: Annotated[str, StringConstraints(min_length=1)]
    audience: tuple[str, ...] = Field(default_factory=tuple)
    issued_at: int
    expires_at: int
    not_before: int | None = None

    # Tenant + RBAC -----------------------------------------------------------
    tenant_id: Annotated[str, StringConstraints(min_length=1)]
    roles: tuple[str, ...] = Field(default_factory=tuple)

    @classmethod
    def model_validate(cls, obj: Any, *args: Any, **kwargs: Any) -> Claims:
        """Validate the raw claim dict, mapping ``aud`` / role list to typed fields."""
        if isinstance(obj, dict):
            obj = {
                "subject": obj.get("sub"),
                "preferred_username": obj.get("preferred_username"),
                "email": obj.get("email"),
                "issuer": obj.get("iss"),
                "audience": _normalise_audience(obj.get("aud")),
                "issued_at": obj.get("iat"),
                "expires_at": obj.get("exp"),
                "not_before": obj.get("nbf"),
                "tenant_id": obj.get("tenant_id"),
                "roles": _normalise_roles(obj.get("realm_access")),
            }
        return super().model_validate(obj, *args, **kwargs)


def _normalise_roles(realm_access: Any) -> tuple[str, ...]:
    """Pull a tuple of role strings out of the ``realm_access`` block."""
    if not isinstance(realm_access, dict):
        return ()
    raw = realm_access.get("roles", [])
    if not isinstance(raw, list):
        return ()
    return tuple(str(r) for r in raw if isinstance(r, str))
