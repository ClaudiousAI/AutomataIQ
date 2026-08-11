"""FastAPI application factory (M01).

Boots the HTTP surface with:

- ``/health`` — liveness probe (NFR-005).
- ``/ready`` — readiness probe, currently always True until real
  services land in M03+.
- OpenTelemetry bootstrap on startup (idempotent).
- A typed error envelope so every JSON error response has the same shape
  (NFR-006: typed contract at every service boundary).

Traceability: NFR-005 (health/readiness on day one), NFR-006 (typed
config + error envelope), NFR-007 (idempotent factory — multiple calls
in the same process do not double-init OTel).
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from .settings import get_settings
from .telemetry import init_telemetry

logger = logging.getLogger(__name__)


#: Stable, versioned error envelope — every JSON error uses this shape.
#: Versioned so we can change fields without breaking older clients
#: that have already deserialised the response.
ERROR_ENVELOPE_VERSION = "1"


def create_app() -> FastAPI:
    """Build and return a fully-wired :class:`FastAPI` instance.

    A factory (rather than a module-level ``app``) means tests can build
    fresh instances with overridden settings, and uvicorn reloaders do
    not leak OTel providers between processes.
    """
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        docs_url="/docs",
        redoc_url=None,
    )

    # Idempotent: the second call (e.g. a reloader) is a no-op.
    init_telemetry(
        service_name=settings.app_name,
        service_namespace=settings.otel_service_namespace,
        otlp_endpoint=settings.otel_exporter_otlp_endpoint,
    )

    @app.get("/health", tags=["meta"])
    def health() -> dict[str, str]:
        """Liveness probe — process is up and serving HTTP."""
        return {"status": "ok", "service": settings.app_name}

    @app.get("/ready", tags=["meta"])
    def ready() -> dict[str, str]:
        """Readiness probe — process is ready to take traffic.

        M01 is single-tenant, no DB, no cache, so we are always ready.
        Real readiness gates (DB ping, Qdrant reachable, …) land in M03.
        """
        return {"status": "ready", "service": settings.app_name}

    @app.exception_handler(Exception)
    async def _envelope_errors(_request: Request, exc: Exception) -> JSONResponse:
        """Convert any unhandled exception into the typed error envelope.

        The body shape is stable across the product so clients can
        always parse ``error.code`` and ``error.message``.
        """
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
#: The factory above remains the canonical construction path.
app = create_app()
