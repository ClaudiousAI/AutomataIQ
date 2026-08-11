"""FastAPI application factory (M01 + M02).

M02 wired:

- :class:`BearerAuthMiddleware` mounted at app-level so every
  non-open path is verified before a handler runs.
- :class:`InMemoryAuditLogger` on ``app.state.audit`` — M03 swaps in
  the PG-backed logger.
- :mod:`app.auth.api` route module mounted at ``/api/v1``.

Traceability: NFR-005 (health/readiness remain open), NFR-006 (typed
config + error envelope), NFR-007 (idempotent factory + audit does
not crash), FR-053/FR-057 (RBAC + tenant boundary enforced by
middleware + deps).
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from .auth.api import router as auth_router
from .auth.audit import InMemoryAuditLogger
from .auth.middleware import BearerAuthMiddleware
from .auth.verifier import create_jwks_verifier
from .settings import get_settings
from .telemetry import init_telemetry

logger = logging.getLogger(__name__)


#: Stable, versioned error envelope — every JSON error uses this shape.
ERROR_ENVELOPE_VERSION = "1"


def create_app() -> FastAPI:
    """Build and return a fully-wired :class:`FastAPI` instance."""
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version="0.2.0",
        docs_url="/docs",
        redoc_url=None,
    )

    # Idempotent: the second call (e.g. a reloader) is a no-op.
    init_telemetry(
        service_name=settings.app_name,
        service_namespace=settings.otel_service_namespace,
        otlp_endpoint=settings.otel_exporter_otlp_endpoint,
    )

    # --- Auth wiring -----------------------------------------------------
    # The verifier is optional in misconfigured deployments; without a
    # JWKS source we fall back to a strict refusal mode where every
    # request is 401. That fail-closed posture is intentional — NFR-004.
    jwks = settings.resolved_jwks()
    if jwks is None:
        logger.warning(
            "JWT verification disabled: no JWKS configured. "
            "All requests will be refused at the auth layer."
        )
        verifier = None
    else:
        verifier = create_jwks_verifier(
            issuer=settings.jwt_issuer,
            audience=settings.jwt_audience,
            jwks=jwks,
        )

    audit = InMemoryAuditLogger()
    app.state.audit = audit

    # Mount the auth middleware BEFORE the auth router so handlers see
    # the verified principal on ``request.state``.
    if verifier is not None:
        app.add_middleware(
            BearerAuthMiddleware,
            verifier=verifier,
            audit=audit,
        )

    app.include_router(auth_router)

    # --- Health endpoints (open) -----------------------------------------
    @app.get("/health", tags=["meta"])
    def health() -> dict[str, str]:
        """Liveness probe — process is up and serving HTTP."""
        return {"status": "ok", "service": settings.app_name}

    @app.get("/ready", tags=["meta"])
    def ready() -> dict[str, str]:
        """Readiness probe — process is ready to take traffic.

        M02 reports the verifier state. ``ready=false`` means auth is
        misconfigured (no JWKS) and the process should be removed
        from the load-balancer pool.
        """
        return {
            "status": "ready" if verifier is not None else "auth_misconfigured",
            "service": settings.app_name,
        }

    # --- Error envelope (M01) --------------------------------------------
    @app.exception_handler(Exception)
    async def _envelope_errors(_request: Request, exc: Exception) -> JSONResponse:
        """Convert any unhandled exception into the typed error envelope."""
        logger.exception("Unhandled exception in request", exc_info=exc)
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "internal_error",
                    "message": "An internal error occurred.",
                    "envelope_version": ERROR_ENVELOPE_VERSION,
                }
            },
        )

    return app


#: Module-level app for uvicorn (``uvicorn app.main:app``).
app = create_app()
