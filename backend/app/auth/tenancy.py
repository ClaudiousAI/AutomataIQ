"""Tenant context — the M02 contract every later module inherits.

The tenant boundary is the security boundary. This module owns:

- The :class:`TenantContext` dataclass (immutable — pinned by test).
- The token-only tenant extractor (NEVER honours query/header — pinned
  by test).
- The path-vs-token reconciliation (FR-057 — pinned by test).

M03 will wrap this into PostgreSQL ``SET LOCAL app.tenant_id`` calls;
M15 will use it for policy decisions. Both depend on this module
staying narrow.

Traceability: FR-057, NFR-004.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class TenantContext:
    """The resolved principal for a single request.

    Frozen so a handler cannot mutate the tenant mid-request — the
    invariant M03's RLS helper relies on.
    """

    tenant_id: str
    subject: str
    roles: tuple[str, ...]

    @property
    def is_platform_admin(self) -> bool:
        return "platform_admin" in self.roles


def extract_tenant_from_request(*, token_tenant: str) -> str:
    """Return the tenant the token asserts.

    Deliberately only accepts ``token_tenant``: query parameters and
    ``X-Tenant-*`` headers are NEVER consulted here, because doing
    so would re-introduce the horizontal-privilege escalation
    vectors FR-057 was written to close.
    """
    if not token_tenant:
        raise PermissionError("token carries no tenant")
    return token_tenant


#: ``/api/v1/tenants/{tenant_id}/...`` is the canonical tenant-scoped
#: path shape (M04 will ratify this). The regex captures the segment
#: after ``/tenants/`` and before the next ``/``.
_TENANT_PATH_RE = re.compile(r"^/api/v\d+/tenants/([^/]+)(?:/|$)")


def resolve_tenant_for_path(ctx: TenantContext, path: str) -> str:
    """Return the tenant the URL refers to, or raise.

    Args:
        ctx: The verified request context.
        path: The HTTP request path.

    Returns:
        The tenant id from the path (matches ``ctx.tenant_id``).

    Raises:
        PermissionError: If the path's tenant does not match the
            token's tenant, or the path has no tenant segment and
            the caller is not ``platform_admin``.
    """
    match = _TENANT_PATH_RE.match(path)
    if match is None:
        # No tenant in the path. ``platform_admin`` may pass through;
        # everyone else is rejected.
        if not ctx.is_platform_admin:
            raise PermissionError("path has no tenant and caller is not platform_admin")
        return ctx.tenant_id

    path_tenant = match.group(1)
    if path_tenant != ctx.tenant_id and not ctx.is_platform_admin:
        raise PermissionError(
            f"cross-tenant access denied: token={ctx.tenant_id} path={path_tenant}"
        )
    return path_tenant
