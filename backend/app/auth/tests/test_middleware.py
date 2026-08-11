"""Integration tests — Auth middleware / FastAPI dependency (FR-053, FR-057, NFR-004).

The integration test that exercises the full HTTP path: a real
``TestClient``, a real JWT signed by the test issuer, and a
representative protected endpoint set that exercises the role +
tenant matrix.
"""

from __future__ import annotations

import pytest
from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from app.auth.api import router as auth_router
from app.auth.audit import InMemoryAuditLogger
from app.auth.deps import AuthContext, require_auth, require_role
from app.auth.middleware import BearerAuthMiddleware
from app.auth.roles import Role
from app.auth.verifier import create_jwks_verifier

from ._issuer import Issuer


@pytest.fixture
def issuer() -> Issuer:
    return Issuer.make()


#: Path of a role-owned endpoint — each role gets exactly one
#: ``/api/v1/role/<role>`` route protected by ``require_role(<role>)``
#: so the matrix can verify that the named role authenticates and
#: that every other role is denied.
def _role_endpoint(role: Role) -> str:
    return f"/api/v1/role/{role.value}"


@pytest.fixture
def app_with_auth(issuer: Issuer) -> tuple[FastAPI, InMemoryAuditLogger]:
    """Build a small FastAPI app that exercises every M02 surface."""
    verifier = create_jwks_verifier(
        issuer=issuer.issuer,
        audience=issuer.audience,
        jwks=issuer.jwks,
    )
    audit = InMemoryAuditLogger()
    app = FastAPI()
    app.state.audit = audit
    # ``add_middleware`` is the production wiring path — the test
    # exercises the same code the real server does.
    app.add_middleware(BearerAuthMiddleware, verifier=verifier, audit=audit)

    # /health mirrors the production app so the open-path exemption is
    # exercised end-to-end (NFR-005).
    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "service": "saie-api"}

    # Mount the real /api/v1/auth router so /me and /auth/logout are
    # covered. They declare ``require_auth`` so any valid token passes.
    app.include_router(auth_router)

    # One role-owned endpoint per role — drives the 7×7 RBAC matrix.
    for _role in Role:
        _dep = require_role(_role)

        @app.get(_role_endpoint(_role))
        def _role_route(
            _ctx: AuthContext = Depends(_dep),
            __role: Role = _role,
        ) -> dict[str, str]:
            return {"role": __role.value, "ok": "true"}

    # Tenant-scoped read endpoint — drives the cross-tenant matrix.
    @app.get("/api/v1/tenants/{tenant_id}/sources")
    def list_sources(
        tenant_id: str,
        ctx: AuthContext = Depends(require_auth),
    ) -> dict[str, str]:
        from app.auth.tenancy import resolve_tenant_for_path

        resolve_tenant_for_path(ctx.tenant, f"/api/v1/tenants/{tenant_id}/sources")
        return {"tenant_id": tenant_id}

    @app.exception_handler(PermissionError)
    def _perm(_request: Request, exc: PermissionError) -> JSONResponse:
        return JSONResponse(
            status_code=403,
            content={
                "error": {
                    "code": "forbidden",
                    "message": str(exc),
                    "envelope_version": "1",
                }
            },
        )

    return app, audit


def _client(app_with_auth: tuple[FastAPI, InMemoryAuditLogger]) -> tuple[TestClient, InMemoryAuditLogger]:
    app, audit = app_with_auth
    return TestClient(app), audit


def test_health_endpoint_is_open_without_a_token(
    app_with_auth: tuple[FastAPI, InMemoryAuditLogger],
) -> None:
    """``/health`` and ``/ready`` are unauthenticated by design (NFR-005)."""
    client, _ = _client(app_with_auth)
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_unauthenticated_request_to_protected_path_returns_401_envelope(
    app_with_auth: tuple[FastAPI, InMemoryAuditLogger],
) -> None:
    """Missing token → 401 with the versioned error envelope (NFR-006)."""
    client, _ = _client(app_with_auth)
    resp = client.get("/api/v1/me")
    assert resp.status_code == 401
    body = resp.json()
    assert body["error"]["code"] == "missing_authorization"
    assert body["error"]["envelope_version"] == "1"


def test_expired_token_returns_401(
    app_with_auth: tuple[FastAPI, InMemoryAuditLogger], issuer: Issuer
) -> None:
    client, _ = _client(app_with_auth)
    token = issuer.mint_token(roles=["analyst"], expires_in=-3600)
    resp = client.get("/api/v1/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401


def test_me_returns_the_verified_principal(
    app_with_auth: tuple[FastAPI, InMemoryAuditLogger], issuer: Issuer
) -> None:
    client, _ = _client(app_with_auth)
    token = issuer.mint_token(roles=["analyst"], subject="alice", tenant_id="t-a")
    resp = client.get("/api/v1/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["sub"] == "alice"
    assert body["tenant_id"] == "t-a"
    assert body["username"] == "alice"
    assert "analyst" in body["roles"]


@pytest.mark.parametrize("granted_role", list(Role))
def test_rbac_matrix_each_role_hits_its_own_endpoint(
    app_with_auth: tuple[FastAPI, InMemoryAuditLogger], issuer: Issuer, granted_role: Role
) -> None:
    """A token carrying ONLY ``granted_role`` reaches ``/role/<granted_role>``."""
    client, _ = _client(app_with_auth)
    token = issuer.mint_token(roles=[granted_role.value], tenant_id="t-a")
    resp = client.get(_role_endpoint(granted_role), headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200, (
        f"role={granted_role.value} should reach {_role_endpoint(granted_role)}, "
        f"got {resp.status_code} {resp.text}"
    )


@pytest.mark.parametrize("granted_role", list(Role))
@pytest.mark.parametrize("target_role", list(Role))
def test_rbac_matrix_role_isolation(
    app_with_auth: tuple[FastAPI, InMemoryAuditLogger],
    issuer: Issuer,
    granted_role: Role,
    target_role: Role,
) -> None:
    """Matrix: each role can reach its OWN endpoint only."""
    client, _ = _client(app_with_auth)
    if granted_role == target_role:
        pytest.skip("diagonal — covered by the positive test")
    token = issuer.mint_token(roles=[granted_role.value], tenant_id="t-a")
    resp = client.get(_role_endpoint(target_role), headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403, (
        f"role={granted_role.value} must be denied {_role_endpoint(target_role)}, "
        f"got {resp.status_code}"
    )


def test_analyst_role_denied_writes_role_denied_audit(
    app_with_auth: tuple[FastAPI, InMemoryAuditLogger], issuer: Issuer
) -> None:
    """A role denial writes a ``ROLE_DENIED`` audit row (FR-054)."""
    client, audit = _client(app_with_auth)
    token = issuer.mint_token(roles=["analyst"], tenant_id="t-a")
    resp = client.get(
        _role_endpoint(Role.PLATFORM_ADMIN), headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 403
    denied = [e for e in audit.events() if e.event_type.value == "role_denied"]
    assert denied, "expected a ROLE_DENIED audit row"


def test_logout_emits_audit_row(
    app_with_auth: tuple[FastAPI, InMemoryAuditLogger], issuer: Issuer
) -> None:
    client, audit = _client(app_with_auth)
    token = issuer.mint_token(roles=["analyst"], tenant_id="t-a")
    resp = client.post("/api/v1/auth/logout", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 204
    logouts = [e for e in audit.events() if e.event_type.value == "logout"]
    assert len(logouts) == 1


def test_tenant_boundary_blocks_cross_tenant_access(
    app_with_auth: tuple[FastAPI, InMemoryAuditLogger], issuer: Issuer
) -> None:
    """A token for tenant-a is rejected when hitting /tenants/tenant-b/... (FR-057)."""
    client, _ = _client(app_with_auth)
    token = issuer.mint_token(roles=["analyst"], tenant_id="tenant-a")
    resp = client.get(
        "/api/v1/tenants/tenant-b/sources",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


def test_platform_admin_can_access_any_tenant(
    app_with_auth: tuple[FastAPI, InMemoryAuditLogger], issuer: Issuer
) -> None:
    """``platform_admin`` is the only role that crosses the tenant boundary."""
    client, _ = _client(app_with_auth)
    token = issuer.mint_token(roles=["platform_admin"], tenant_id="platform")
    resp = client.get(
        "/api/v1/tenants/tenant-b/sources",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
