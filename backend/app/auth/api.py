"""M02 — Authentication & Authorization route handlers.

Wires the user-facing auth surfaces:

- ``GET /api/v1/me`` — returns the authenticated principal.
- ``POST /api/v1/auth/logout`` — emits the LOGOUT audit row and (in
  production) adds the token's ``jti`` to a denylist. M16's deploy
  tests wire the denylist; for now the handler is a no-op success so
  the test matrix can exercise it.

The handlers are intentionally tiny — the security boundary is the
middleware + ``require_role`` dep; routes just expose verified state.
"""

from __future__ import annotations

import os
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from .audit import AuthAuditLogger, AuthEvent, AuthEventType
from .deps import AuthContext, require_auth
from .roles import Role

router = APIRouter(prefix="/api/v1", tags=["auth"])


@router.get("/me")
def me(ctx: AuthContext = Depends(require_auth)) -> dict[str, object]:
    """Return the authenticated principal.

    Useful for the SPA to render a user badge after login, and for
    CI to assert the OIDC wire-up end-to-end.
    """
    return {
        "sub": ctx.claims.subject,
        "username": ctx.claims.preferred_username,
        "email": ctx.claims.email,
        "tenant_id": ctx.claims.tenant_id,
        "roles": list(ctx.claims.roles),
    }


@router.post("/auth/logout", status_code=204)
def logout(request: Request, ctx: AuthContext = Depends(require_auth)) -> None:
    """Emit the LOGOUT audit row.

    Returns 204 on success. M16 will add a denylist check before the
    middleware accepts the token again.
    """
    audit: AuthAuditLogger | None = getattr(request.app.state, "audit", None)
    if audit is not None:
        audit.log(
            AuthEvent(
                event_type=AuthEventType.LOGOUT,
                subject=ctx.claims.subject,
                tenant_id=ctx.claims.tenant_id,
                ip=request.client.host if request.client else "",
                user_agent=request.headers.get("user-agent", ""),
                outcome="success",
            )
        )


class DevLoginRequest(BaseModel):
    """Body of ``POST /api/v1/auth/dev/login``.

    Carries the role(s) + tenant the caller wants the issued token to
    bind to. Production never sees this endpoint — ``SAIE_ENV=dev`` is
    the only gate.
    """

    subject: str = "dev-user"
    username: str = "dev-user"
    email: str = "dev@example.com"
    tenant_id: str = "tenant-a"
    roles: list[str] = [Role.ANALYST.value]


class DevLoginResponse(BaseModel):
    """Response payload mirroring the production Keycloak exchange."""

    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    principal: dict[str, Any]


@router.post("/auth/dev/login", response_model=DevLoginResponse)
def dev_login(request: Request, body: DevLoginRequest) -> DevLoginResponse:
    """**Dev-only.** Mint a JWT for the requested principal.

    Hard-gated on ``SAIE_ENV=dev``; production deployments get a 404
    — there is no way to invoke this surface against a Keycloak-backed
    realm.

    The actual JWT signing uses the in-memory RSA keypair the test
    issuer exposes, so the dev path is cryptographically real — not a
    string-only stand-in — and the verifier contract is exercised
    end-to-end.
    """
    if os.environ.get("SAIE_ENV", "production") != "dev":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="not found",
        )

    from app.auth.tests._issuer import Issuer

    issuer = Issuer.make()
    token = issuer.mint_token(
        subject=body.subject,
        roles=body.roles,
        tenant_id=body.tenant_id,
    )
    principal: dict[str, Any] = {
        "sub": body.subject,
        "username": body.username,
        "email": body.email,
        "tenant_id": body.tenant_id,
        "roles": body.roles,
    }
    audit: AuthAuditLogger | None = getattr(request.app.state, "audit", None)
    if audit is not None:
        audit.log(
            AuthEvent(
                event_type=AuthEventType.LOGIN_SUCCESS,
                subject=body.subject,
                tenant_id=body.tenant_id,
                ip=request.client.host if request.client else "",
                user_agent=request.headers.get("user-agent", ""),
                outcome="success",
                reason="dev_login",
            )
        )
    return DevLoginResponse(
        access_token=token,
        expires_in=300,
        principal=principal,
    )
