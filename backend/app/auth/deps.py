"""FastAPI dependencies — the seam between middleware and handlers.

These are the dependencies every protected endpoint declares. The
RBAC matrix test (test_middleware.py::test_rbac_matrix) is the
canary: any drift here is caught by enumerating the seven roles
across a representative endpoint set.

Two usage patterns are supported:

- ``Depends(require_auth)`` — any authenticated principal.
- ``Depends(require_role(Role.PLATFORM_ADMIN))`` — additionally
  requires the named role.

Traceability: FR-053, FR-057, NFR-004.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from fastapi import HTTPException, Request, status

from .audit import AuthAuditLogger, AuthEvent, AuthEventType
from .claims import Claims
from .roles import Role, role_set_from_claims
from .tenancy import TenantContext
from .verifier import (
    InvalidTokenError,
    TokenVerifier,
)


@dataclass(frozen=True)
class AuthContext:
    """The view of the principal a handler sees.

    Wraps :class:`TenantContext` and adds the typed claims so a
    handler that wants the user's email or preferred_username can
    grab it without re-parsing the token.
    """

    claims: Claims
    tenant: TenantContext


def _attach_auth_context(request: Request) -> AuthContext:
    """Pull the verified principal from ``request.state``.

    Middleware has already done the verification; we just rebind it
    into a typed object here. This split keeps middleware focused on
    parsing and lets dependencies stay testable.
    """
    ctx_obj = getattr(request.state, "auth_context", None)
    if ctx_obj is None:  # pragma: no cover - middleware guarantees it
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="missing auth context",
        )
    return ctx_obj  # type: ignore[no-any-return]


def require_auth(request: Request) -> AuthContext:
    """FastAPI dependency: any authenticated principal.

    Use as::

        @app.get("/me")
        def me(ctx: AuthContext = Depends(require_auth)):
            ...

    The middleware has already verified the token; this just exposes
    the typed context.
    """
    return _attach_auth_context(request)


def require_role(required: Role) -> Callable[[Request], AuthContext]:
    """Build a dependency that enforces ``required`` role membership.

    Usage::

        @app.get("/admin")
        def admin(_ctx: AuthContext = Depends(require_role(Role.PLATFORM_ADMIN))):
            ...

    The audit row is written here — not in middleware — so the row
    carries the role name that was actually required.
    """

    def _enforce(request: Request) -> AuthContext:
        ctx = _attach_auth_context(request)
        granted = role_set_from_claims({"realm_access": {"roles": list(ctx.claims.roles)}})
        if required not in granted:
            _safe_audit(
                request,
                AuthEvent(
                    event_type=AuthEventType.ROLE_DENIED,
                    subject=ctx.claims.subject,
                    tenant_id=ctx.claims.tenant_id,
                    ip=request.client.host if request.client else "",
                    user_agent=request.headers.get("user-agent", ""),
                    outcome="failure",
                    reason=f"required={required.value}",
                ),
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"role {required.value} required",
            )
        return ctx

    return _enforce


def _safe_audit(request: Request, event: AuthEvent) -> None:
    """Best-effort audit write; never raises."""
    audit_logger = getattr(request.app.state, "audit", None)
    if isinstance(audit_logger, AuthAuditLogger):
        audit_logger.log(event)


# --- Helper used by middleware to build the AuthContext --------------------


def build_auth_context(claims: Claims) -> AuthContext:
    """Construct the context the middleware attaches to ``request.state``."""
    roles = role_set_from_claims({"realm_access": {"roles": list(claims.roles)}})
    return AuthContext(
        claims=claims,
        tenant=TenantContext(
            tenant_id=claims.tenant_id,
            subject=claims.subject,
            roles=tuple(r.value for r in roles),
        ),
    )


# Re-export for callers that want them at a stable import path.
__all__ = [
    "AuthContext",
    "InvalidTokenError",
    "Role",
    "TenantContext",
    "TokenVerifier",
    "build_auth_context",
    "require_auth",
    "require_role",
]
