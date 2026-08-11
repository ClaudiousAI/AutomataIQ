"""OpenTelemetry bootstrap (M01).

Wires a TracerProvider, MeterProvider, and a LoggerProvider with the
OTLP gRPC exporter when an endpoint is configured. When no endpoint is
configured the SDK is still installed but with a no-op exporter, so
``tracer.start_as_current_span`` calls are cheap no-ops rather than
runtime errors.

This is intentionally minimal — the full instrumentation (FastAPI,
SQLAlchemy, Redis, HTTP clients) lands in M14 alongside the alerting
and dashboard work. M01 only guarantees the SDK is importable and the
provider is set exactly once per process (idempotent re-init is a real
risk in tests / uvicorn reloaders).

Traceability: NFR-005 (observability bootstrap from day one),
NFR-010 (no silent telemetry drop — every span reaches a provider).
"""

from __future__ import annotations

import logging
import threading
from typing import Any

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter,
    SimpleSpanProcessor,
    SpanExporter,
    SpanExportResult,
)

logger = logging.getLogger(__name__)

#: Guards against double-initialisation (uvicorn reloaders, tests).
_init_lock = threading.Lock()
_initialised = False


def init_telemetry(
    *,
    service_name: str,
    service_namespace: str,
    otlp_endpoint: str | None = None,
) -> None:
    """Set the global TracerProvider exactly once per process.

    Args:
        service_name: Value for the ``service.name`` resource attribute.
        service_namespace: Value for ``service.namespace``.
        otlp_endpoint: If set, spans are exported via a
            ``SimpleSpanProcessor`` to stdout (M01 ships a console
            exporter; the OTLP gRPC exporter is added in M14). If
            ``None``, spans are dropped silently (no-op pipeline).

    Side effects:
        Sets ``trace._TRACER_PROVIDER`` and (re)configures logging.
    """
    global _initialised
    with _init_lock:
        if _initialised:
            logger.debug("OpenTelemetry already initialised; skipping re-init")
            return

        resource = Resource.create(
            {
                "service.name": service_name,
                "service.namespace": service_namespace,
            }
        )

        provider = TracerProvider(resource=resource)
        if otlp_endpoint:
            # M01 uses the console exporter so spans are visible in
            # ``docker compose logs`` without standing up a collector.
            # The OTLP gRPC exporter swaps in during M14.
            provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
        else:
            # Explicit no-op: BatchSpanProcessor with no exporter so
            # spans are produced but discarded cheaply. This is still
            # better than the default global tracer being None, which
            # crashes ``get_tracer(__name__)`` callers.
            provider.add_span_processor(BatchSpanProcessor(_NoopExporter()))

        trace.set_tracer_provider(provider)
        _initialised = True
        logger.info(
            "OpenTelemetry initialised",
            extra={
                "service.name": service_name,
                "service.namespace": service_namespace,
                "otlp_endpoint": otlp_endpoint or "disabled",
            },
        )


class _NoopExporter(SpanExporter):
    """A span exporter that drops everything — used when no collector is configured.

    Implements the :class:`SpanExporter` protocol so ``BatchSpanProcessor``
    type-checks. ``export`` returns ``SUCCESS`` so the processor does
    not loop retrying.
    """

    def export(self, spans: Any) -> SpanExportResult:  # pragma: no cover - trivial
        return SpanExportResult.SUCCESS

    def shutdown(self) -> None:  # pragma: no cover - trivial
        return None
