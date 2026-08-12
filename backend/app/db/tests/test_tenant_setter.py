"""RED-then-GREEN — tenant-setter (`tenant_context` ContextManager).

Pins the contract:
- The GUC is visible INSIDE the context.
- The GUC is cleared on EXIT (SET LOCAL semantics — NFR-007).
- The GUC is cleared on EXCEPTION (rollback, not commit).
- Nested contexts raise — re-scoping an outer transaction silently
  leaks the inner GUC into the outer work.
- The context refuses to enter when the caller already has a
  transaction open.

Traceability: FR-057, NFR-004, NFR-007.
"""

from __future__ import annotations

import os

import psycopg
import pytest

from app.auth.roles import Role
from app.db.tenant import current_tenant_id, tenant_context


def _raw_conn() -> psycopg.Connection:
    """Open a fresh ``saie_app`` connection with no tenant GUC.

    pgserver binds to a random port (NOT 5432) chosen at session
    start by ``_find_free_port``, so we resolve host/port from the
    env vars the ``saie_test_dsn`` fixture injects (see
    ``conftest.py``). Hardcoding ``127.0.0.1`` silently connects
    to a non-existent Postgres on the wrong port and the connection
    times out.
    """
    dsn = (
        f"host={os.environ['SAIE_TEST_PGHOST']} "
        f"port={os.environ['SAIE_TEST_PGPORT']} "
        f"dbname={os.environ['SAIE_TEST_PGDBNAME']} "
        f"user={os.environ['SAIE_TEST_PGUSER']} "
        f"password={os.environ['SAIE_TEST_PGPASSWORD']}"
    )
    return psycopg.connect(dsn)


def test_tenant_context_sets_local_guv() -> None:
    """Inside the context, the GUC equals ``tenant_id``."""
    conn = _raw_conn()
    try:
        with tenant_context(conn, "tenant_1", Role.TENANT_ADMIN):
            assert current_tenant_id(conn) == "tenant_1"
    finally:
        conn.close()


def test_tenant_context_clears_guv_on_clean_exit() -> None:
    """``SET LOCAL`` is transaction-scoped: exit commits, GUC cleared."""
    conn = _raw_conn()
    try:
        with tenant_context(conn, "tenant_1", Role.TENANT_ADMIN):
            assert current_tenant_id(conn) == "tenant_1"
        # Outside the context: GUC cleared.
        assert current_tenant_id(conn) is None
    finally:
        conn.close()


def test_tenant_context_rolls_back_on_exception() -> None:
    """An exception inside the context rolls back; GUC still cleared on exit."""
    conn = _raw_conn()
    try:
        with pytest.raises(RuntimeError, match="boom"):
            with tenant_context(conn, "should-rollback", Role.TENANT_ADMIN):
                # Insert a row that should be rolled back. The tenant_id
                # GUC must match the row's ``id`` so the tenants-table
                # RLS policy ``app_tenant_matches(id)`` lets the INSERT
                # through (RLS is enforced at row-write time, not just
                # at read time).
                with conn.cursor() as cur:
                    cur.execute(
                        "INSERT INTO public.tenants (id, name) "
                        "VALUES ('should-rollback', 'rb')"
                    )
                raise RuntimeError("boom")
        # The exception must have triggered a rollback — the row never
        # persisted.
        assert current_tenant_id(conn) is None
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM public.tenants WHERE id = 'should-rollback'")
            assert cur.fetchone() is None
    finally:
        conn.close()


def test_tenant_context_rejects_empty_tenant_id() -> None:
    """An empty tenant id is a programming error and must raise."""
    conn = _raw_conn()
    try:
        with pytest.raises(ValueError):
            with tenant_context(conn, "", Role.TENANT_ADMIN):
                pass
    finally:
        conn.close()


def test_tenant_context_refuses_to_nest() -> None:
    """Re-scoping an outer transaction silently leaks the inner GUC.

    ``tenant_context`` MUST refuse to nest — the second entry raises
    ``InvalidTransactionState`` and the caller must commit/rollback
    the outer transaction first.
    """
    conn = _raw_conn()
    try:
        with tenant_context(conn, "tenant_outer", Role.TENANT_ADMIN):
            with pytest.raises(psycopg.errors.InvalidTransactionState):
                with tenant_context(conn, "tenant_inner", Role.TENANT_ADMIN):
                    pass
    finally:
        conn.close()


def test_tenant_context_with_platform_admin_role() -> None:
    """``platform_admin`` is a cross-tenant role — context still sets the GUC.

    The platform_admin role bypasses RLS via its permissive policy;
    the GUC still gets set so audit rows can attribute the bypass.
    """
    conn = _raw_conn()
    try:
        with tenant_context(conn, "any_tenant", Role.PLATFORM_ADMIN):
            assert current_tenant_id(conn) == "any_tenant"
    finally:
        conn.close()


def test_tenant_context_persists_changes_inside_block() -> None:
    """INSERTs inside the block are committed on clean exit (no rollback)."""
    conn = _raw_conn()
    try:
        with tenant_context(conn, "persist-x", Role.TENANT_ADMIN):
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO public.tenants (id, name) VALUES ('persist-x', 'p')"
                )
        # After exit, the row is committed. The verification SELECT
        # also runs inside ``tenant_context`` because the ``tenants``
        # table has RLS enabled: without the GUC set, the SELECT
        # returns zero rows (default-deny posture).
        with tenant_context(conn, "persist-x", Role.PLATFORM_ADMIN):
            with conn.cursor() as cur:
                cur.execute("SELECT 1 FROM public.tenants WHERE id = 'persist-x'")
                assert cur.fetchone() is not None
            # Clean up. The platform_admin cross-tenant role's
            # permissive policy lets the DELETE through regardless of
            # the GUC value.
            with conn.cursor() as cur:
                cur.execute("DELETE FROM public.tenants WHERE id = 'persist-x'")
    finally:
        conn.close()
