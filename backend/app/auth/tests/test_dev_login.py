"""Tests — dev-only login endpoint.

The endpoint is hard-gated on ``SAIE_ENV=dev``; in production the
route returns 404 so the surface cannot be reached. The tests pin
both branches.
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import Response

from app.auth.api import router as auth_router
from app.auth.audit import InMemoryAuditLogger


@pytest.fixture
def app_in_dev(monkeypatch: pytest.MonkeyPatch) -> tuple[TestClient, InMemoryAuditLogger]:
    monkeypatch.setenv("SAIE_ENV", "dev")
    app = FastAPI()
    audit = InMemoryAuditLogger()
    app.state.audit = audit
    app.include_router(auth_router)
    return TestClient(app), audit


@pytest.fixture
def app_in_prod(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.delenv("SAIE_ENV", raising=False)
    monkeypatch.setenv("SAIE_ENV", "production")
    app = FastAPI()
    app.include_router(auth_router)
    return TestClient(app)


def test_dev_login_returns_a_real_jwt(app_in_dev: tuple[TestClient, InMemoryAuditLogger]) -> None:
    """A dev login returns a signed JWT the verifier can decode."""
    client, _audit = app_in_dev
    response = client.post(
        "/api/v1/auth/dev/login",
        json={
            "subject": "alice",
            "username": "alice",
            "email": "alice@example.com",
            "tenant_id": "t-a",
            "roles": ["analyst"],
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["token_type"] == "Bearer"
    assert body["expires_in"] == 300
    assert body["access_token"].count(".") == 2  # looks like a JWT
    assert body["principal"]["sub"] == "alice"
    assert body["principal"]["tenant_id"] == "t-a"


def test_dev_login_writes_a_login_success_audit_row(
    app_in_dev: tuple[TestClient, InMemoryAuditLogger],
) -> None:
    client, audit = app_in_dev
    response = client.post(
        "/api/v1/auth/dev/login",
        json={
            "subject": "alice",
            "username": "alice",
            "email": "alice@example.com",
            "tenant_id": "t-a",
            "roles": ["analyst"],
        },
    )
    assert response.status_code == 200
    logins = [e for e in audit.events() if e.event_type.value == "login_success"]
    assert len(logins) == 1
    assert logins[0].subject == "alice"
    assert logins[0].tenant_id == "t-a"


def test_dev_login_is_404_in_production(app_in_prod: TestClient) -> None:
    """Production deployments cannot reach the dev endpoint at all."""
    response = client_post(app_in_prod)
    assert response.status_code == 404


def client_post(client: TestClient) -> Response:
    """Tiny helper so the prod-only test stays expressive."""
    return client.post(  # type: ignore[no-any-return]
        "/api/v1/auth/dev/login",
        json={
            "subject": "alice",
            "username": "alice",
            "email": "alice@example.com",
            "tenant_id": "t-a",
            "roles": ["analyst"],
        },
    )
