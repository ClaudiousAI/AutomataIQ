"""Shared test fixtures for the M02 auth tests.

A self-contained JWKS issuer with a fixed RSA keypair — so the JWT
verifier tests can run without any external Keycloak instance, and
the tests that hit ``/me`` end-to-end use the same cryptographic
path the production verifier will use.

Why not use Keycloak itself: M02's CI must be deterministic and
self-contained. The real ``KeycloakIntrospector`` is exercised
behind the same ``TokenVerifier`` interface in M16's deploy
integration tests; here we keep the unit suite hermetic.
"""

from __future__ import annotations

import base64
import time
from dataclasses import dataclass
from typing import Any

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

#: RSA key size — 2048 is the modern baseline. Smaller keys fail
#: some strict JWT libraries; larger keys slow tests without value.
_RSA_KEY_SIZE = 2048


def _b64url_uint(value: int) -> str:
    """Encode an unsigned int as base64url (no padding), as RFC 7518 requires."""
    byte_length = (value.bit_length() + 7) // 8
    return base64.urlsafe_b64encode(value.to_bytes(byte_length, "big")).rstrip(b"=").decode()


@dataclass(frozen=True)
class Issuer:
    """A self-contained JWT issuer with private key + JWKS.

    Use ``issuer.mint_token(claims)`` to produce a signed JWT, and
    ``issuer.jwks`` to feed the verifier's JWKS URL.
    """

    private_key: rsa.RSAPrivateKey
    kid: str
    issuer: str
    audience: str

    @classmethod
    def make(
        cls,
        *,
        issuer: str = "https://saie-test.local/realms/saie",
        audience: str = "saie-api",
        kid: str = "test-key-1",
    ) -> Issuer:
        key = rsa.generate_private_key(public_exponent=65537, key_size=_RSA_KEY_SIZE)
        return cls(private_key=key, kid=kid, issuer=issuer, audience=audience)

    @property
    def public_jwk(self) -> dict[str, Any]:
        public_numbers = self.private_key.public_key().public_numbers()
        return {
            "kty": "RSA",
            "use": "sig",
            "alg": "RS256",
            "kid": self.kid,
            "n": _b64url_uint(public_numbers.n),
            "e": _b64url_uint(public_numbers.e),
        }

    @property
    def jwks(self) -> dict[str, Any]:
        return {"keys": [self.public_jwk]}

    @property
    def private_pem(self) -> str:
        return self.private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        ).decode()

    def mint_token(
        self,
        *,
        subject: str = "user-1",
        roles: list[str] | None = None,
        tenant_id: str = "tenant-a",
        expires_in: int = 300,
        not_before: int | None = None,
        issuer: str | None = None,
        audience: str | None = None,
        extra_claims: dict[str, Any] | None = None,
        kid: str | None = None,
        missing: tuple[str, ...] = (),
    ) -> str:
        now = int(time.time())
        claims: dict[str, Any] = {
            "sub": subject,
            "preferred_username": subject,
            "email": f"{subject}@example.com",
            "iss": issuer or self.issuer,
            "aud": audience or self.audience,
            "iat": now,
            "exp": now + expires_in,
            "nbf": not_before if not_before is not None else now,
            "realm_access": {"roles": roles or []},
            "tenant_id": tenant_id,
        }
        for m in missing:
            claims.pop(m, None)
        if extra_claims:
            claims.update(extra_claims)
        return jwt.encode(
            claims,
            self.private_pem,
            algorithm="RS256",
            headers={"kid": kid if kid is not None else self.kid},
        )
