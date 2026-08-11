# ADR-0016 — JWT-only auth path with Keycloak-issued RS256 tokens

- **Status:** Accepted
- **Date:** 2026-08-11
- **Supersedes:** —
- **Amends:** [ADR-0010](./0010-keycloak-identity-provider.md), [ADR-0014](./0014-cost-minimized-open-source-stack.md)

## Context

ADR-0010 chose Keycloak as the identity provider; ADR-0014 locked the
open-source, self-hosted stack. With M02's acceptance criteria
(FR-053 RBAC, FR-054 audit, FR-057 tenant isolation, NFR-004 security)
we need to settle *how* the backend trusts an incoming request before
the first byte of M03+ can land.

Three concrete choices were on the table:

1. **JWT verification against the issuer's published JWKS** — the
   backend fetches the realm's JWKS once (and caches via
   `PyJWKClient`), verifies the RS256 signature, checks `iss` / `aud`
   / `exp` / `nbf`, and binds the typed `Claims` to the request
   context. No network round-trip per request after the JWKS is warm.
2. **RFC 7662 token introspection** — every request POSTs the access
   token to Keycloak's `/protocol/openid-connect/token/introspect`
   endpoint. Adds a synchronous dependency on Keycloak for every
   authenticated request; couples availability to Keycloak's.
3. **Opaque session cookies** — server-side session table, cookies
   carrying an opaque ID. Trades authN complexity for session-store
   cost and CSRF surface.

## Decision

**Adopt (1): JWT verification against the issuer's JWKS.**

The `TokenVerifier` Protocol (`backend/app/auth/verifier.py`) is the
seam. The CI-honoured implementation is `JwtVerifier` (cryptographic,
offline-capable via an inline JWKS dict). Production swaps in the
same interface against Keycloak's published JWKS URL — no caller
changes.

Three reasons make this the right call:

- **Avail­ability decoupling.** The backend can serve authenticated
  traffic while Keycloak is briefly unreachable. JWKS is cached; once
  cached, no per-request network call is made.
- **Math is deterministic.** RS256 signature verification is local
  CPU; no upstream coordination, no eventual-consistency windows.
- **M03 keeps a clean boundary.** PostgreSQL `SET LOCAL app.tenant_id`
  binds to the verified claim; no session-table lookup required.

## Consequences

### Positive

- **No `KeycloakIntrospector` needed for the M02–M15 path.** The
  introspector remains a future option behind the same `TokenVerifier`
  Protocol for the (genuinely edge-case) scenarios where a token's
  revocation must be checked synchronously — the only caller change is
  the factory wiring in `create_app()`.
- **Hermetic CI.** Tests run without a live Keycloak because the
  `Issuer` test fixture is a self-contained RSA keypair + JWKS — the
  same cryptographic path the production verifier takes.
- **Typed boundary.** `Claims` is a Pydantic model; downstream code
  never reads a raw `dict`. RFC 7519 normalisation (`aud` → tuple,
  `exp`/`iat`/`sub` required) happens once at the edge.

### Negative

- **Revocation lag.** A token that has been revoked by Keycloak is
  still accepted until `exp`. The compensating control is the token
  denylist, **deferred to M16** (the `/auth/logout` audit-row no-op
  is the documented seam; M16's deploy integration tests wire the
  `jti` denylist behind the same middleware).
- **Algorithm allow-list discipline.** PyJWT will sign-verify with
  whatever algorithm is configured; an attacker who flips `alg=HS256`
  and submits the public key as a secret is the classic alg-confusion
  attack. Mitigated here by `algorithms=("RS256",)` set explicitly,
  the JWKS limited to RSA keys, and the
  `test_verifier_rejects_token_signed_by_unknown_kid` canary.
- **No signature-free path.** A misconfigured deployment with no JWKS
  source makes `create_app()` fall back to a strict-refusal mode
  where every request is 401 (NFR-004 fail-closed). The
  `/ready` endpoint reports `auth_misconfigured` so the load balancer
  can drain the instance.

## Operational notes

- **JWKS rotation.** The verifier caches keys in-process. A second
  `kid` published by Keycloak during rotation must be honoured during
  the rollover window. M16's deploy integration tests assert the
  rollover behaviour.
- **Test issuer.** `backend/app/auth/tests/_issuer.py` is the
  self-contained `Issuer` (RSA keypair + JWKS + `mint_token`); the
  same cryptographic path is exercised as production.

## Traceability

- FR-053 (RBAC), FR-054 (audit groundwork), FR-057 (tenant isolation)
- NFR-004 (security, encrypted secrets, typed contract)
- NFR-005 (observability via the audit stream)
- NFR-006 (typed boundary via `Claims`)
- NFR-007 (audit failures never crash the auth path)
