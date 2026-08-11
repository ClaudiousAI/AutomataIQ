"""M02 — Authentication & Authorization package.

Public surface:

- :mod:`app.auth.roles`     — closed enum of the 7 RBAC roles + claim helpers.
- :mod:`app.auth.claims`    — typed JWT claims model at the service boundary.
- :mod:`app.auth.verifier`  — ``TokenVerifier`` interface + ``JwtVerifier``.
- :mod:`app.auth.tenancy`   — ``TenantContext`` + tenant-boundary checks (FR-057).
- :mod:`app.auth.audit`     — ``AuthAuditLogger`` interface + ``InMemoryAuditLogger``.
- :mod:`app.auth.middleware` — Bearer-token parsing middleware.
- :mod:`app.auth.deps`      — FastAPI dependencies: ``require_auth``, ``require_role``.

Traceability: FR-053 (RBAC), FR-054 (audit groundwork), FR-057 (tenant
isolation), NFR-004 (typed contract + no secrets committed).
"""
