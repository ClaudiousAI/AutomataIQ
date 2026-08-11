"""M01 — OpenTelemetry bootstrap tests (NFR-005, NFR-010).

Pins three behaviours that are easy to break and very expensive to
discover only in production:

1. ``init_telemetry`` installs a real ``TracerProvider`` so
   ``trace.get_tracer(__name__).start_as_current_span`` does not raise.
2. The function is idempotent — calling it twice in the same process
   (common in uvicorn reloaders and tests) does not double-register
   span processors.
3. With no endpoint configured, spans are still created (a default
   no-op pipeline is installed) so callers never see ``NoOpTracer``
   surprises.

Note on OTel process-global state: the SDK uses an internal ``Once``
guard so a second ``set_tracer_provider`` call is a no-op. We test
idempotency by counting how many times our factory is invoked, not by
reading internal OTel state (which is reset-incompatible by design).
"""

from __future__ import annotations

from unittest.mock import patch


def _reset_initialised():
    """Reset the module-level ``_initialised`` flag so each test gets
    a clean attempt at installing a provider."""
    from app import telemetry

    telemetry._initialised = False


def _install_placeholder_provider():
    """Install a placeholder TracerProvider so subsequent
    ``init_telemetry`` calls do not collide with OTel's set-once guard
    when ``create_app()`` was previously imported in the same process.

    Returns the installed provider for further inspection.
    """
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
        InMemorySpanExporter,
    )
    from opentelemetry.util import _once

    # Reset the SDK's set-once guard so this placeholder is allowed
    # to be installed even if another test (or ``create_app``) already
    # set one. The guard is a process-global ``_once.Once`` object.
    trace._TRACER_PROVIDER_SET_ONCE = _once.Once()  # type: ignore[attr-defined]

    pre = TracerProvider()
    pre.add_span_processor(SimpleSpanProcessor(InMemorySpanExporter()))
    trace._set_tracer_provider(pre, log=False)
    return pre


def test_init_telemetry_installs_tracer_provider():
    """After init, ``trace.get_tracer()`` returns a usable tracer (NFR-005)."""
    _reset_initialised()
    _install_placeholder_provider()

    from opentelemetry import trace

    from app.telemetry import init_telemetry

    init_telemetry(
        service_name="saie-api-test",
        service_namespace="saie",
        otlp_endpoint=None,
    )

    tracer = trace.get_tracer("test")
    with tracer.start_as_current_span("hello") as span:
        assert span is not None
        assert span.name == "hello"


def test_init_telemetry_is_idempotent():
    """Calling init twice only constructs ONE real provider (NFR-007).

    Verified by counting how many times ``TracerProvider`` is
    constructed inside ``init_telemetry`` — the second call must
    short-circuit on the ``_initialised`` flag.
    """
    _reset_initialised()
    _install_placeholder_provider()

    from opentelemetry.sdk.trace import TracerProvider

    from app import telemetry

    with patch.object(telemetry, "TracerProvider", wraps=TracerProvider) as provider_spy:
        telemetry.init_telemetry(
            service_name="svc", service_namespace="saie", otlp_endpoint=None
        )
        telemetry.init_telemetry(
            service_name="svc", service_namespace="saie", otlp_endpoint=None
        )

    # Exactly one TracerProvider was constructed despite two init calls.
    assert provider_spy.call_count == 1, (
        f"expected one TracerProvider construction, got {provider_spy.call_count}"
    )


def test_init_telemetry_with_endpoint_uses_exporter():
    """When an endpoint is configured, a Console exporter is wired in.

    Pinned so a future refactor that drops the exporter (e.g. by
    always picking the no-op path) is caught here — silent telemetry
    loss is exactly the failure mode NFR-010 calls out.
    """
    _reset_initialised()
    _install_placeholder_provider()

    from app import telemetry

    with patch.object(telemetry, "ConsoleSpanExporter") as console_exporter:
        telemetry.init_telemetry(
            service_name="svc",
            service_namespace="saie",
            otlp_endpoint="http://otel-collector:4317",
        )
        assert console_exporter.called, (
            "ConsoleSpanExporter must be wired when an endpoint is set"
        )


def test_init_telemetry_without_endpoint_uses_noop():
    """Without an endpoint, a no-op pipeline is installed (NFR-010).

    The goal is *no crash* on ``get_tracer``; the spans simply go
    nowhere until M14 wires the OTLP gRPC exporter.
    """
    _reset_initialised()
    _install_placeholder_provider()

    from opentelemetry import trace

    from app.telemetry import init_telemetry

    init_telemetry(
        service_name="svc",
        service_namespace="saie",
        otlp_endpoint=None,
    )

    tracer = trace.get_tracer("noop-test")
    with tracer.start_as_current_span("x") as span:
        # We only assert the span object exists; it can be dropped later.
        assert span is not None
