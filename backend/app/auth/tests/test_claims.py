"""RED test — JWT claims model (NFR-006).

Claims are the typed contract at the service boundary. Drift here
silently breaks every downstream module (M03+ tenant scoping,
M05+ audit attribution, …). These tests pin the field set, types,
and required-vs-optional behaviour.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.auth.claims import Claims


def _base() -> dict[str, object]:
    return {
        "sub": "user-1",
        "preferred_username": "user-1",
        "email": "u@example.com",
        "iss": "https://saie.local/realms/saie",
        "aud": "saie-api",
        "iat": 1_700_000_000,
        "exp": 1_700_000_300,
        "nbf": 1_700_000_000,
        "realm_access": {"roles": ["analyst"]},
        "tenant_id": "t-a",
    }


def test_claims_round_trip_a_valid_payload():
    """All required fields deserialize cleanly."""
    claims = Claims.model_validate(_base())
    assert claims.subject == "user-1"
    assert claims.tenant_id == "t-a"
    # ``aud`` is normalised to a tuple per RFC 7519 §4.1.3.
    assert "saie-api" in claims.audience
    assert claims.issuer == "https://saie.local/realms/saie"
    assert claims.roles == ("analyst",)


def test_claims_audience_accepts_list_or_string():
    """``aud`` is permitted to be either a string or a list (RFC 7519 §4.1.3)."""
    base = _base()
    base["aud"] = ["saie-api", "another"]
    claims = Claims.model_validate(base)
    # The model normalises to a tuple.
    assert "saie-api" in claims.audience


def test_claims_subject_is_required():
    """``sub`` is the principal identity — must be present."""
    payload = _base()
    payload.pop("sub")
    with pytest.raises(ValidationError):
        Claims.model_validate(payload)


def test_claims_tenant_id_is_required():
    """``tenant_id`` is mandatory for FR-057 tenant isolation."""
    payload = _base()
    payload.pop("tenant_id")
    with pytest.raises(ValidationError):
        Claims.model_validate(payload)


def test_claims_roles_default_to_empty():
    """Missing ``realm_access`` is fine; roles is an empty tuple."""
    payload = _base()
    payload.pop("realm_access")
    claims = Claims.model_validate(payload)
    assert claims.roles == ()


def test_claims_expiry_is_required():
    """``exp`` is mandatory — tokens without expiry are rejected at parse time."""
    payload = _base()
    payload.pop("exp")
    with pytest.raises(ValidationError):
        Claims.model_validate(payload)
