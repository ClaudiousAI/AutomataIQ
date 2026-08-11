"""Token verifier — the JWT / JWKS path used in dev, test, and prod.

M02 ships two implementations behind one interface:

- :class:`JwtVerifier` — local cryptographic verification using a JWKS
  document. This is the path CI uses (no Keycloak required) and the
  path M16 wires to Keycloak's published JWKS in production.
- A future ``KeycloakIntrospector`` (RFC 7662) handles opaque tokens
  and revocation; it lands alongside M16's deploy integration tests
  so this suite stays hermetic.

Every failure mode is a typed exception so middleware can map to the
correct 401 / 403 status without inspecting raw strings.

Traceability: NFR-004 (typed contract; no raw secrets in code),
NFR-006 (typed boundary).
"""

from __future__ import annotations

from typing import Any, Protocol

import jwt
from jwt import PyJWKClient

from .claims import Claims

# --- Public exceptions ----------------------------------------------------


class InvalidTokenError(Exception):
    """Base for all token-verification failures.

    Subclasses drive the HTTP status mapping in middleware:
    expired/wrong-issuer/wrong-audience/tampered → 401.
    Role + tenant checks happen AFTER verify succeeds, so they
    produce 403.
    """


class InvalidSignatureError(InvalidTokenError):
    """Signature did not validate against any published JWKS key."""


class TokenExpiredError(InvalidTokenError):
    """``exp`` is in the past."""


class TokenNotYetValidError(InvalidTokenError):
    """``nbf`` is in the future."""


class InvalidIssuerError(InvalidTokenError):
    """``iss`` does not match the configured issuer."""


class InvalidAudienceError(InvalidTokenError):
    """``aud`` does not include the configured audience."""


# --- Verifier interface ---------------------------------------------------


class TokenVerifier(Protocol):
    """The single interface M02 depends on.

    Implementations must be deterministic, side-effect-free, and
    raise a subclass of :class:`InvalidTokenError` on every failure.
    """

    def verify(self, token: str) -> Claims:  # pragma: no cover - interface
        ...


# --- JWKS verifier --------------------------------------------------------


class JwtVerifier:
    """Verify a JWT against a JWKS document.

    The verifier is constructed with the expected ``issuer`` and
    ``audience``; every token that fails to match is rejected.

    The verifier holds a small in-memory ``PyJWKClient`` per
    instance; do not construct per-request.
    """

    def __init__(
        self,
        *,
        issuer: str,
        audience: str,
        jwks: dict[str, Any] | str,
        algorithms: tuple[str, ...] = ("RS256",),
    ) -> None:
        self._issuer = issuer
        self._audience = audience
        self._algorithms = algorithms
        # ``PyJWKClient`` accepts a URL OR we can hand it the keys
        # directly via ``from_jwk_set``. For tests / offline use we
        # build the client with a data: URL so it has somewhere to
        # fetch from; in production the URL is the JWKS endpoint.
        if isinstance(jwks, dict):
            self._keys = jwt.PyJWK.from_dict(jwks["keys"][0]) if jwks.get("keys") else None
            self._jwks_keys = jwks.get("keys", [])
            self._client: PyJWKClient | None = None
        else:
            self._keys = None
            self._jwks_keys = []
            self._client = PyJWKClient(jwks)

    def _key_for(self, token: str) -> Any:
        if self._client is not None:
            return self._client.get_signing_key_from_jwt(token).key
        # Offline mode: the JWKS is already in memory. Pick the right
        # key by the token's ``kid`` header.
        try:
            unverified = jwt.get_unverified_header(token)
        except jwt.PyJWTError as exc:
            raise InvalidTokenError(str(exc)) from exc
        kid = unverified.get("kid")
        for jwk_dict in self._jwks_keys:
            if jwk_dict.get("kid") == kid:
                return jwt.PyJWK(jwk_dict).key
        # No matching kid — treat as a signature failure (an attacker
        # shouldn't be able to discover which kids are valid).
        raise InvalidSignatureError(f"unknown kid: {kid!r}")

    def verify(self, token: str) -> Claims:
        """Verify the token and return typed claims.

        Raises:
            InvalidTokenError: subclass matching the failure mode.
        """
        if not isinstance(token, str) or token.count(".") != 2:
            raise InvalidTokenError("malformed JWT")

        key = self._key_for(token)
        try:
            unverified_claims = jwt.decode(
                token,
                key=key,
                algorithms=self._algorithms,
                issuer=self._issuer,
                audience=self._audience,
                options={"require": ["exp", "iat", "iss", "aud", "sub"]},
            )
        except jwt.ExpiredSignatureError as exc:
            raise TokenExpiredError("token expired") from exc
        except jwt.ImmatureSignatureError as exc:
            raise TokenNotYetValidError("token not yet valid") from exc
        except jwt.InvalidIssuerError as exc:
            raise InvalidIssuerError(f"issuer mismatch: {exc}") from exc
        except jwt.InvalidAudienceError as exc:
            raise InvalidAudienceError(f"audience mismatch: {exc}") from exc
        except jwt.InvalidSignatureError as exc:
            raise InvalidSignatureError("signature invalid") from exc
        except jwt.PyJWTError as exc:
            raise InvalidTokenError(str(exc)) from exc

        # Custom claim ``tenant_id`` is mandatory for M02 (FR-057).
        if not unverified_claims.get("tenant_id"):
            raise InvalidTokenError("missing tenant_id claim")

        return Claims.model_validate(unverified_claims)


def create_jwks_verifier(
    *,
    issuer: str,
    audience: str,
    jwks: dict[str, Any] | str,
    algorithms: tuple[str, ...] = ("RS256",),
) -> TokenVerifier:
    """Factory: construct a :class:`JwtVerifier` with the right options."""
    return JwtVerifier(
        issuer=issuer,
        audience=audience,
        jwks=jwks,
        algorithms=algorithms,
    )
