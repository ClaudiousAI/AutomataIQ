"""M03a — Database substrate package.

Public surface:

- :mod:`app.db.tenant` — Postgres session-var contract: ``TENANT_SESSION_VAR``,
  ``current_tenant_id()``, ``tenant_context()`` (ContextManager), and
  ``is_cross_tenant_role()``. The single source of truth for the
  tenant-scoping protocol (NFR-004 / FR-057).

Traceability: FR-001, FR-008, FR-019, FR-038, FR-043, FR-057, NFR-004,
NFR-006, NFR-007.
"""
