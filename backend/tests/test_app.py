"""M01 — FastAPI skeleton tests (NFR-005, NFR-006).

The health and readiness probes are the contract every container is
expected to satisfy from day one. If these fail, ``docker compose
up`` cannot be considered healthy and the deployment pipeline rejects
the image.

M02 contract overlay: ``/ready`` now reports the JWT-verifier state.
Configured JWKS → ``ready``; otherwise ``auth_misconfigured`` (the
process is up but the auth layer is not safe to take traffic).
"""

from __future__ import annotations

import json

import pytest
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


def test_ready_returns_ready_when_jwks_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    """``GET /ready`` returns ``ready`` when the M02 verifier is wired (NFR-005).

    M02 binds the readiness probe to the verifier state: a configured
    JWKS means the auth layer is safe to take traffic. Without a
    JWKS the app stays up but reports ``auth_misconfigured`` so the
    load-balancer removes it from the pool.
    """
    # Mint a self-contained JWKS so the verifier succeeds and the
    # readiness probe reports the happy path. The kid here is arbitrary
    # — no token is decoded in this test, only the JWKS integrity check.
    from app.auth.tests._issuer import Issuer

    jwks = Issuer.make().jwks
    monkeypatch.setenv("JWT_JWKS_INLINE", json.dumps(jwks))

    from app.main import create_app

    client = TestClient(create_app())
    response = client.get("/ready")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"


def test_ready_reports_auth_misconfigured_when_jwks_missing() -> None:
    """``GET /ready`` returns ``auth_misconfigured`` when no JWKS is set (NFR-004).

    With no JWKS the M02 verifier runs in fail-closed mode and refuses
    every request. The readiness probe must surface that — a process
    that "looks ready" but cannot verify a token is a deployment hazard.
    """
    import os

    os.environ.pop("JWT_JWKS_INLINE", None)
    os.environ.pop("JWT_JWKS_URL", None)

    from app.main import create_app

    client = TestClient(create_app())
    response = client.get("/ready")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "auth_misconfigured"


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
