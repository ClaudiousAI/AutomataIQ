"""Bearer-token middleware — the only place ``Authorization`` is parsed.

The middleware's job is narrow:

1. Parse ``Authorization: Bearer <token>`` (no header → 401).
2. Call the configured :class:`TokenVerifier`; on any failure → 401
   plus an audit row of type ``TOKEN_INVALID``.
3. On success, attach an :class:`AuthContext` to ``request.state``
   so downstream dependencies can read it without re-parsing.

Role + tenant checks are NOT done here — they live in the
:func:`app.auth.deps.require_role` dependency, so the per-endpoint
policy is co-located with the endpoint declaration.

Traceability: FR-053, FR-057, NFR-004.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

from .audit import AuthAuditLogger, AuthEvent, AuthEventType
from .deps import build_auth_context
from .verifier import InvalidTokenError, TokenVerifier

#: Endpoints exempt from authentication. ``/health`` and ``/ready``
#: must be reachable from load balancers and orchestrators without
#: a token; everything under ``/api/v1/`` is gated.
_OPEN_PATHS: tuple[str, ...] = ("/health", "/ready", "/docs", "/openapi.json")


class BearerAuthMiddleware(BaseHTTPMiddleware):
    """ASGI middleware that verifies a Bearer token on every request."""

    def __init__(
        self,
        app: ASGIApp,
        *,
        verifier: TokenVerifier,
        audit: AuthAuditLogger,
    ) -> None:
        super().__init__(app)
        self._verifier = verifier
        self._audit = audit

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        # Always let open paths through.
        if any(request.url.path == p or request.url.path.startswith(p + "/") for p in _OPEN_PATHS):
            return await call_next(request)

        token = _extract_bearer(request)
        if token is None:
            self._safe_audit(
                request,
                AuthEvent(
                    event_type=AuthEventType.TOKEN_INVALID,
                    subject="anonymous",
                    tenant_id="",
                    ip=request.client.host if request.client else "",
                    user_agent=request.headers.get("user-agent", ""),
                    outcome="failure",
                    reason="missing_authorization",
                ),
            )
            return _error_response(
                code="missing_authorization",
                message="Authorization header is required.",
                status_code=401,
            )

        try:
            claims = self._verifier.verify(token)
        except InvalidTokenError as exc:
            self._safe_audit(
                request,
                AuthEvent(
                    event_type=AuthEventType.TOKEN_INVALID,
                    subject="anonymous",
                    tenant_id="",
                    ip=request.client.host if request.client else "",
                    user_agent=request.headers.get("user-agent", ""),
                    outcome="failure",
                    reason=type(exc).__name__,
                ),
            )
            return _error_response(
                code="invalid_token",
                message=str(exc) or "The provided token is invalid.",
                status_code=401,
            )

        request.state.auth_context = build_auth_context(claims)
        return await call_next(request)

    def _safe_audit(self, request: Request, event: AuthEvent) -> None:
        """Audit must never crash the auth path (NFR-007)."""
        try:
            self._audit.log(event)
        except Exception:  # noqa: BLE001
            # Defensive — ``InMemoryAuditLogger`` already swallows; this
            # belt-and-braces catch protects a future PG impl.
            pass


def _extract_bearer(request: Request) -> str | None:
    """Parse ``Authorization: Bearer <token>`` or return ``None``."""
    header = request.headers.get("authorization")
    if not header:
        return None
    parts = header.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    token = parts[1].strip()
    return token or None


def _error_response(*, code: str, message: str, status_code: int) -> JSONResponse:
    """Wrap a 401/403 in the typed error envelope (M01 contract)."""
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "envelope_version": "1",
            }
        },
    )
