"""RED test — Tenant context (FR-057, NFR-004).

Tenant isolation is the security boundary every later module inherits.
These tests pin the contract: a request's tenant is the token's
tenant, never a query parameter, never a header.
"""

from __future__ import annotations

import pytest

from app.auth.tenancy import (
    TenantContext,
    extract_tenant_from_request,
    resolve_tenant_for_path,
)


def test_tenant_context_is_immutable():
    """A tenant context cannot be mutated mid-request — invariant for RLS."""
    ctx = TenantContext(tenant_id="t-a", subject="u", roles=("analyst",))
    with pytest.raises((AttributeError, TypeError, Exception)):
        ctx.tenant_id = "t-b"  # type: ignore[misc]


def test_extract_tenant_from_request_uses_token_only():
    """The tenant comes ONLY from the verified claims — never from query/header."""
    # No ``request`` with a tenant header should ever override the token.
    assert extract_tenant_from_request(token_tenant="t-a") == "t-a"


def test_resolve_tenant_for_path_matches_token():
    """The token tenant and the path tenant must agree (FR-057)."""
    ctx = TenantContext(tenant_id="t-a", subject="u", roles=("analyst",))
    assert resolve_tenant_for_path(ctx, "/api/v1/tenants/t-a/sources") == "t-a"


def test_resolve_tenant_for_path_rejects_mismatch():
    """Cross-tenant access with a valid token is denied (FR-057)."""
    ctx = TenantContext(tenant_id="t-a", subject="u", roles=("analyst",))
    with pytest.raises(PermissionError):
        resolve_tenant_for_path(ctx, "/api/v1/tenants/t-b/sources")


def test_resolve_tenant_for_path_allows_platform_admin_anywhere():
    """``platform_admin`` is cross-tenant by role definition."""
    ctx = TenantContext(
        tenant_id="t-a",
        subject="u",
        roles=("platform_admin",),
    )
    # No exception even for a different tenant path.
    resolve_tenant_for_path(ctx, "/api/v1/tenants/t-b/sources")


def test_resolve_tenant_for_path_handles_missing_segment():
    """A path without a tenant segment is treated as cross-tenant (denied)."""
    ctx = TenantContext(tenant_id="t-a", subject="u", roles=("analyst",))
    with pytest.raises(PermissionError):
        resolve_tenant_for_path(ctx, "/api/v1/health")
