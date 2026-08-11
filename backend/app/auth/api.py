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

from fastapi import APIRouter, Depends, Request

from .audit import AuthAuditLogger, AuthEvent, AuthEventType
from .deps import AuthContext, require_auth

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
