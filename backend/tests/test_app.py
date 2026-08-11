"""M01 — FastAPI skeleton tests (NFR-005, NFR-006).

The health and readiness probes are the contract every container is
expected to satisfy from day one. If these fail, ``docker compose
up`` cannot be considered healthy and the deployment pipeline rejects
the image.
"""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_health_returns_ok():
    """``GET /health`` returns 200 with ``status: ok`` (NFR-005)."""
    from app.main import create_app

    client = TestClient(create_app())
    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "service" in body


def test_ready_returns_ready():
    """``GET /ready`` returns 200 with ``status: ready`` (NFR-005)."""
    from app.main import create_app

    client = TestClient(create_app())
    response = client.get("/ready")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"


def test_error_envelope_shape():
    """Unhandled exceptions serialise into the typed error envelope (NFR-006).

    Asserts the field set, not just the status, so a future refactor
    that drops ``envelope_version`` is caught here.
    """

    from app.main import ERROR_ENVELOPE_VERSION, create_app

    # Build a tiny app that re-uses our error handler but always raises,
    # so we exercise the envelope path without touching business logic.
    app = create_app()

    @app.get("/boom")
    def boom() -> None:
        raise RuntimeError("kaboom")

    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/boom")

    assert response.status_code == 500
    body = response.json()
    assert "error" in body
    err = body["error"]
    assert err["code"] == "internal_error"
    assert isinstance(err["message"], str) and err["message"]
    assert err["envelope_version"] == ERROR_ENVELOPE_VERSION
