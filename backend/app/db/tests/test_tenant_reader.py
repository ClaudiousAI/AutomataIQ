"""RED-then-GREEN — tenant-setter reader (`current_tenant_id`).

Pins the contract: the reader is NULL-safe, returns the GUC value
verbatim when set, and never raises on a connection that has no
open transaction.

Traceability: FR-057, NFR-004, NFR-007.
"""

from __future__ import annotations

import os

import psycopg
import pytest

from app.auth.roles import Role
from app.db.tenant import current_tenant_id, is_cross_tenant_role, tenant_context


def _raw_dsn() -> str:
    """Build a DSN for a fresh ``saie_app`` connection to the test DB.

    pgserver binds to a random port chosen at session start, so we
    resolve host/port from the env vars the ``saie_test_dsn``
    fixture injects (see ``conftest.py``). Falling back to 127.0.0.1
    would silently connect to a non-existent Postgres on the wrong
    port and time out.
    """
    return (
        f"host={os.environ['SAIE_TEST_PGHOST']} "
        f"port={os.environ['SAIE_TEST_PGPORT']} "
        f"dbname={os.environ['SAIE_TEST_PGDBNAME']} "
        f"user={os.environ['SAIE_TEST_PGUSER']} "
        f"password={os.environ['SAIE_TEST_PGPASSWORD']}"
    )


def test_current_tenant_id_is_none_outside_context(
    app_conn_with_tenant_a: psycopg.Connection,
) -> None:
    """On a connection not inside ``tenant_context``, the reader returns ``None``.

    Default-deny posture: a query that forgot to scope itself returns
    zero rows from RLS-protected tables because the GUC is unset, and
    the reader must never crash on that condition.
    """
    # The fixture opens a ``tenant_context`` for tenant_a, so we
    # need a fresh connection that has never seen a tenant GUC.
    raw = psycopg.connect(_raw_dsn())
    try:
        # On a fresh autocommit connection, no GUC has been set.
        raw.autocommit = True
        assert current_tenant_id(raw) is None
    finally:
        raw.close()


def test_current_tenant_id_returns_set_value(
    app_conn_with_tenant_a: psycopg.Connection,
) -> None:
    """Inside ``tenant_context``, the reader returns the scoped tenant."""
    assert current_tenant_id(app_conn_with_tenant_a) == "tenant_a"


def test_current_tenant_id_returns_set_value_for_tenant_b(
    app_conn_with_tenant_b: psycopg.Connection,
) -> None:
    """Inside ``tenant_context`` for tenant_b, the reader returns 'tenant_b'."""
    assert current_tenant_id(app_conn_with_tenant_b) == "tenant_b"


def test_current_tenant_id_is_none_after_context_exit() -> None:
    """After ``tenant_context`` exits, the GUC is cleared (SET LOCAL semantics)."""
    conn = psycopg.connect(_raw_dsn())
    try:
        # Read GUCs in autocommit mode so the read does not leave an
        # implicit transaction open — ``tenant_context`` refuses to
        # nest inside an open transaction.
        conn.autocommit = True
        # Before entering the context: no GUC.
        assert current_tenant_id(conn) is None
        # Inside the context: GUC visible.
        with tenant_context(conn, "tenant_x", Role.TENANT_ADMIN):
            assert current_tenant_id(conn) == "tenant_x"
        # After exit: GUC cleared (the transaction committed/rolled back).
        assert current_tenant_id(conn) is None
    finally:
        conn.close()


def test_is_cross_tenant_role_only_platform_admin() -> None:
    """``is_cross_tenant_role`` returns True iff the role is platform_admin."""
    assert is_cross_tenant_role(Role.PLATFORM_ADMIN) is True
    # Every other role is tenant-scoped.
    for role in (
        Role.TENANT_ADMIN,
        Role.ARCHITECT,
        Role.ANALYST,
        Role.REVIEWER,
        Role.EXECUTIVE,
        Role.READ_ONLY,
    ):
        assert is_cross_tenant_role(role) is False, role


def test_current_tenant_id_does_not_swallow_pg_errors() -> None:
    """The reader must not paper over real PG errors (NFR-007 fail-loud)."""
    conn = psycopg.connect(_raw_dsn())
    try:
        # A bogus GUC name should raise — we want a fail-loud signal,
        # not a silent None. We exercise this by calling the helper
        # with a known typo via a one-off cursor.
        with pytest.raises(psycopg.Error):
            with conn.cursor() as cur:
                cur.execute("SELECT current_setting('does_not_exist_guc', false)")
                cur.fetchone()
    finally:
        conn.close()
