"""Regression test for the no-psql bootstrap path.

Locks the contract that the Linux / ``pytest-postgresql`` substrate
path can re-create the SAIE roles + grants WITHOUT a ``psql``
binary — i.e. that ``conftest._apply_role_bootstrap`` is a faithful
re-implementation of the relevant ``infra/postgres/init.sql``
statements in pure-SQL form.

Without this test the Linux CI path could regress silently:
``psycopg`` parses SQL, not psql metacommands, so feeding it the
verbatim ``init.sql`` (which contains ``\\set`` and ``\\gexec``)
raises ``SyntaxError`` the moment the fixture runs. This test
fires ``_apply_role_bootstrap`` directly against the freshly-created
``saie_test`` DB and asserts the end state — three roles with the
right ``rolbypassrls`` posture, schema grants in place — matches
what ``psql -f init.sql`` would produce.

Traceability: FR-057, NFR-004, NFR-007.
"""

from __future__ import annotations

import os

import psycopg

from app.db.tests.conftest import _apply_role_bootstrap


def _admin_conn_str() -> str:
    """Resolve the ephemeral admin DSN the session fixture exposed."""
    return (
        f"host={os.environ['SAIE_TEST_PGHOST']} "
        f"port={os.environ['SAIE_TEST_PGPORT']} "
        f"dbname={os.environ['SAIE_TEST_PGDBNAME']} "
        f"user={os.environ['SAIE_TEST_PGUSER']} "
        f"password={os.environ['SAIE_TEST_PGPASSWORD']}"
    )


def test_no_psql_bootstrap_creates_roles_with_correct_rls_posture() -> None:
    """Re-running the helper is idempotent and produces the right roles.

    The session-scoped ``saie_test_dsn`` fixture already called the
    helper once. We call it AGAIN here — if any of the ``DO $$
    ... EXCEPTION`` guards regress (e.g. someone deletes the
    duplicate-object check and we lose idempotency), this call
    errors out and the test fails before we even probe the rows.
    """
    dsn = _admin_conn_str()
    host_port_db = dsn.split(" user=")[0]
    h = host_port_db.split("host=")[1].split(" ")[0]
    p = host_port_db.split("port=")[1].split(" ")[0]
    # Re-run the bootstrap. Should succeed (idempotency).
    _apply_role_bootstrap(host=h, port=int(p), user="postgres", password="")

    # End-state assertions: every role is present with the right posture.
    with psycopg.connect(dsn) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT rolname, rolbypassrls, rolcanlogin "
                "FROM pg_roles "
                "WHERE rolname IN ('saie_migrator','saie_app','saie_platform_admin') "
                "ORDER BY rolname"
            )
            rows = {r[0]: (r[1], r[2]) for r in cur.fetchall()}

    assert rows == {
        "saie_app": (False, True),               # RLS-bound, login OK
        "saie_migrator": (True, True),            # BYPASSRLS for Alembic
        "saie_platform_admin": (False, True),    # RLS-bound, permissive policy
    }


def test_no_psql_bootstrap_grants_schema_usage() -> None:
    """The schema grants let ``saie_app`` and ``saie_migrator`` work end-to-end."""
    dsn = _admin_conn_str()
    with psycopg.connect(dsn) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT has_schema_privilege('saie_app', 'public', 'USAGE'), "
                "has_schema_privilege('saie_migrator', 'public', 'CREATE')"
            )
            row = cur.fetchone()
    assert row is not None, "has_schema_privilege() returned no row"
    app_usage, migrator_create = row
    assert app_usage is True, "saie_app missing USAGE on public schema"
    assert migrator_create is True, "saie_migrator missing CREATE on public schema"
