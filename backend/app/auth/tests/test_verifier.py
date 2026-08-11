"""RED test — JWT verifier (FR-053, NFR-004, NFR-006).

Pins the verifier contract that every M02 surface depends on:

- Accepts only the configured issuer / audience / algorithm.
- Rejects tampered / expired / wrong-key tokens deterministically.
- Returns a typed claims object — never ``dict`` — at the boundary.
"""

from __future__ import annotations

import time

import pytest

from app.auth.verifier import (
    InvalidAudienceError,
    InvalidIssuerError,
    InvalidSignatureError,
    InvalidTokenError,
    TokenExpiredError,
    TokenNotYetValidError,
    create_jwks_verifier,
)

from ._issuer import Issuer


@pytest.fixture
def issuer() -> Issuer:
    return Issuer.make()


def test_verifier_accepts_a_well_formed_token(issuer: Issuer) -> None:
    """Happy path: a freshly-minted token from the trusted issuer verifies."""
    verifier = create_jwks_verifier(
        issuer=issuer.issuer,
        audience=issuer.audience,
        jwks=issuer.jwks,
    )
    token = issuer.mint_token(roles=["analyst"], tenant_id="tenant-a")
    claims = verifier.verify(token)
    assert claims.subject == "user-1"
    assert claims.tenant_id == "tenant-a"
    # ``aud`` is normalised to a tuple per RFC 7519 §4.1.3.
    assert issuer.audience in claims.audience
    assert claims.issuer == issuer.issuer


def test_verifier_rejects_tampered_signature(issuer: Issuer) -> None:
    """A one-byte flip in the signature is fatal."""
    verifier = create_jwks_verifier(
        issuer=issuer.issuer,
        audience=issuer.audience,
        jwks=issuer.jwks,
    )
    token = issuer.mint_token(roles=["analyst"])
    tampered = token[:-2] + ("AA" if token[-2:] != "AA" else "BB")
    with pytest.raises(InvalidSignatureError):
        verifier.verify(tampered)


def test_verifier_rejects_expired_token(issuer: Issuer) -> None:
    """``exp`` in the past fails closed."""
    verifier = create_jwks_verifier(
        issuer=issuer.issuer,
        audience=issuer.audience,
        jwks=issuer.jwks,
    )
    # A token that expired an hour ago.
    token = issuer.mint_token(roles=["analyst"], expires_in=-3600)
    with pytest.raises(TokenExpiredError):
        verifier.verify(token)


def test_verifier_rejects_token_not_yet_valid(issuer: Issuer) -> None:
    """``nbf`` in the future fails closed (RFC 7519 §4.1.5)."""
    verifier = create_jwks_verifier(
        issuer=issuer.issuer,
        audience=issuer.audience,
        jwks=issuer.jwks,
    )
    future = int(time.time()) + 3600
    token = issuer.mint_token(roles=["analyst"], not_before=future)
    with pytest.raises(TokenNotYetValidError):
        verifier.verify(token)


def test_verifier_rejects_wrong_issuer(issuer: Issuer) -> None:
    """An attacker who mints a token from a different realm is rejected."""
    verifier = create_jwks_verifier(
        issuer=issuer.issuer,
        audience=issuer.audience,
        jwks=issuer.jwks,
    )
    token = issuer.mint_token(roles=["analyst"], issuer="https://evil.example.com")
    with pytest.raises(InvalidIssuerError):
        verifier.verify(token)


def test_verifier_rejects_wrong_audience(issuer: Issuer) -> None:
    """A token for a different client API is rejected."""
    verifier = create_jwks_verifier(
        issuer=issuer.issuer,
        audience=issuer.audience,
        jwks=issuer.jwks,
    )
    token = issuer.mint_token(roles=["analyst"], audience="other-api")
    with pytest.raises(InvalidAudienceError):
        verifier.verify(token)


def test_verifier_rejects_token_signed_by_unknown_kid(issuer: Issuer) -> None:
    """A token whose ``kid`` is not in the JWKS is rejected."""
    verifier = create_jwks_verifier(
        issuer=issuer.issuer,
        audience=issuer.audience,
        jwks=issuer.jwks,
    )
    # Sign with the right key, but lie about the kid.
    token = issuer.mint_token(roles=["analyst"], kid="not-the-real-kid")
    with pytest.raises(InvalidSignatureError):
        verifier.verify(token)


def test_verifier_rejects_malformed_token(issuer: Issuer) -> None:
    """Garbage in the Authorization slot is rejected, not crashed on."""
    verifier = create_jwks_verifier(
        issuer=issuer.issuer,
        audience=issuer.audience,
        jwks=issuer.jwks,
    )
    with pytest.raises(InvalidTokenError):
        verifier.verify("not-a-jwt")
    with pytest.raises(InvalidTokenError):
        verifier.verify("only.two.parts")
