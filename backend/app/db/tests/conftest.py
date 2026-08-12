"""M03a test fixtures — Postgres + roles + RLS substrate.

Boots a private Postgres instance (via ``pgserver`` so this works on
developer machines without Docker), bootstraps the three SAIE roles,
creates the application database, runs the Alembic migration to
head, and then exposes typed connections for the RLS matrix tests.

The fixtures are scoped as follows:

- ``_pg_server`` — session scope: the Postgres server itself (kept
  alive for the whole pytest session).
- ``saie_db_with_schema`` — session scope, autouse: runs the init
  script + the Alembic migration to head once per session.
- ``app_conn_with_tenant_a`` / ``app_conn_with_tenant_b`` /
  ``admin_conn`` — function scope: short-lived connections with
  the tenant GUC pre-set via :func:`app.db.tenant.tenant_context`.

Every per-test connection rolls back at teardown so tests are
isolated and the migration state is preserved across the session.

Traceability: FR-057, NFR-004, NFR-007.
"""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import urllib.parse
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import psycopg
import pytest

# pgserver ships a portable Postgres binary used by the local Windows
# test runner (Docker is unavailable). On Linux CI the binary path is
# None and pytest-postgresql resolves pg_ctl itself. ``pgserver`` is
# not type-annotated upstream, so the fixture imports + use carry
# ``type: ignore[attr-defined]`` markers; this is the documented mypy
# escape hatch for untyped third-party packages.
try:  # pragma: no cover - environment-specific branch
    import pgserver as _pgserver_pkg  # noqa: F401
    from pgserver import PostgresServer as _PostgresServer  # type: ignore[attr-defined]

    _PGSERVER_BIN: Path | None = Path(_pgserver_pkg.__file__).parent / "pginstall" / "bin"
except Exception:  # noqa: BLE001 - any import failure means pgserver absent
    _PostgresServer = None  # type: ignore[assignment,misc]
    _PGSERVER_BIN = None


# ---------------------------------------------------------------------------
# Session-scoped Postgres server.
# ---------------------------------------------------------------------------

def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


@pytest.fixture(scope="session")
def _pg_server() -> Iterator[Any]:
    """Boot a session-scoped Postgres server (kept alive for the run)."""
    if _PostgresServer is None:  # pragma: no cover - environment-specific branch
        pytest.skip("pgserver is not available on this platform")

    pgdata = Path("C:/pgserver_data")
    pgdata.mkdir(parents=True, exist_ok=True)
    server = _PostgresServer(pgdata, cleanup_mode=None)
    yield server
    # No explicit stop — cleanup_mode=None keeps it running until process exit.


@pytest.fixture(scope="session")
def saie_test_dsn(_pg_server: Any) -> str:
    """Build the DSN string for the test DB and apply init.sql + migrations.

    On first call: creates the ``saie_test`` database, applies
    ``infra/postgres/init.sql``, runs ``alembic upgrade head``.
    """
    import psycopg

    uri = _pg_server.get_uri()
    parsed = urllib.parse.urlparse(uri)
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or 5432
    user = parsed.username or "postgres"
    password = parsed.password or ""
    admin_dsn = (
        f"host={host} port={port} dbname=postgres "
        f"user={user} password={password}"
    )

    # 1. Create saie_test DB.
    with psycopg.connect(admin_dsn, autocommit=True) as admin_conn:
        with admin_conn.cursor() as cur:
            cur.execute(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                "WHERE datname = 'saie_test' AND pid <> pg_backend_pid()"
            )
            cur.execute("DROP DATABASE IF EXISTS saie_test")
            cur.execute("CREATE DATABASE saie_test")

    # 2. Apply infra/postgres/init.sql as the postgres superuser.
    repo_root = Path(__file__).resolve().parents[4]
    init_sql = repo_root / "infra" / "postgres" / "init.sql"
    psql: Path | None = None
    if _PGSERVER_BIN is not None:
        for cand in ("psql.exe", "psql"):
            p = _PGSERVER_BIN / cand
            if p.exists():
                psql = p
                break
    env = os.environ.copy()
    env["PGPASSWORD"] = password
    if psql is not None:
        subprocess.run(
            [
                str(psql), "-h", host, "-p", str(port),
                "-U", user, "-d", "saie_test", "-v", "ON_ERROR_STOP=1",
                "-f", str(init_sql),
            ],
            check=True,
            env=env,
            capture_output=True,
        )
    else:
        # No psql: split on ``;`` and execute each statement via psycopg.
        with psycopg.connect(
            f"host={host} port={port} dbname=saie_test user={user} password={password}",
            autocommit=True,
        ) as conn:
            with conn.cursor() as cur:
                cur.execute(init_sql.read_text())

    # 3. Inject env vars so app.settings + alembic resolve the right URLs.
    os.environ["DATABASE_URL"] = (
        f"postgresql+psycopg://saie_app:saie_app@{host}:{port}/saie_test"
    )
    os.environ["MIGRATOR_DATABASE_URL"] = (
        f"postgresql+psycopg://saie_migrator:saie_migrator@{host}:{port}/saie_test"
    )
    # 3a. Inject the pgserver DSN pieces as standalone env vars so test
    # files that open their own raw ``psycopg.connect()`` (the tenant
    # reader/setter contract tests) can resolve the ephemeral host/port
    # without hardcoding 127.0.0.1:5432 — pgserver binds to a random
    # port chosen by ``_find_free_port``, NOT 5432.
    os.environ["SAIE_TEST_PGHOST"] = host
    os.environ["SAIE_TEST_PGPORT"] = str(port)
    os.environ["SAIE_TEST_PGDBNAME"] = "saie_test"
    os.environ["SAIE_TEST_PGUSER"] = "saie_app"
    os.environ["SAIE_TEST_PGPASSWORD"] = "saie_app"

    # 4. Run alembic upgrade head.
    backend_dir = repo_root / "backend"
    env["PYTHONPATH"] = str(backend_dir) + os.pathsep + env.get("PYTHONPATH", "")
    env["DATABASE_URL"] = os.environ["DATABASE_URL"]
    env["MIGRATOR_DATABASE_URL"] = os.environ["MIGRATOR_DATABASE_URL"]
    try:
        result = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            cwd=str(backend_dir),
            env=env,
            check=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError as exc:
        # Surface the actual migration error in the pytest output so the
        # root cause isn't buried in a CalledProcessError returncode-1.
        Path("C:/pgserver_data/m03a_alembic.err").write_bytes(
            exc.stderr or b"<no stderr>"
        )
        Path("C:/pgserver_data/m03a_alembic.out").write_bytes(
            exc.stdout or b"<no stdout>"
        )
        print("[conftest] alembic STDOUT:", (exc.stdout or b"").decode(errors="replace"))
        print("[conftest] alembic STDERR:", (exc.stderr or b"").decode(errors="replace"))
        raise
    print("[conftest] alembic upgrade head:", result.stdout.decode().strip())

    return (
        f"host={host} port={port} dbname=saie_test user=saie_app password=saie_app"
    )


@pytest.fixture(scope="session", autouse=True)
def saie_db_with_schema(saie_test_dsn: str) -> Iterator[None]:
    """Session-scoped autouse fixture — the side-effect IS the setup."""
    yield


# ---------------------------------------------------------------------------
# Per-test connections.
# ---------------------------------------------------------------------------

@pytest.fixture
def app_conn_with_tenant_a(saie_test_dsn: str) -> Iterator[psycopg.Connection]:
    """An ``saie_app`` connection scoped to ``tenant_a``."""
    yield from _app_conn_for_tenant(saie_test_dsn, "tenant_a")


@pytest.fixture
def app_conn_with_tenant_b(saie_test_dsn: str) -> Iterator[psycopg.Connection]:
    """An ``saie_app`` connection scoped to ``tenant_b``."""
    yield from _app_conn_for_tenant(saie_test_dsn, "tenant_b")


@pytest.fixture
def admin_conn(saie_test_dsn: str) -> Iterator[psycopg.Connection]:
    """An ``saie_platform_admin`` connection (no tenant GUC)."""
    host = saie_test_dsn.split("host=")[1].split(" ")[0]
    port = saie_test_dsn.split("port=")[1].split(" ")[0]
    dbname = "saie_test"
    dsn = (
        f"host={host} port={port} dbname={dbname} "
        f"user=saie_platform_admin password=saie_platform_admin"
    )
    conn = psycopg.connect(dsn)
    try:
        yield conn
    finally:
        conn.rollback()
        conn.close()


def _app_conn_for_tenant(dsn: str, tenant_id: str) -> Iterator[psycopg.Connection]:
    """Open an ``saie_app`` connection, set the tenant GUC, yield.

    The transaction is always rolled back at teardown so per-test
    inserts do not leak into the session-wide DB (the migration
    runs once per session; per-test rows must not survive across
    tests). We cannot use ``tenant_context`` here because it
    commits on clean exit, which would leak rows.
    """
    # Replace the user/password in the DSN so we connect as saie_app.
    dsn = (
        dsn.replace("user=postgres", "user=saie_app")
        .replace("password=postgres", "password=saie_app")
    )
    if "user=" not in dsn:
        dsn += " user=saie_app password=saie_app"
    conn = psycopg.connect(dsn)
    try:
        # Set the tenant GUC inside a transaction that ALWAYS rolls
        # back at teardown. We can't use ``tenant_context`` here
        # because it commits on clean exit — leaking per-test rows
        # into the session-wide DB and tripping unique constraints
        # on the next test's seeded parents. The GUC must be
        # transaction-scoped (``SET LOCAL``), so we manage the
        # transaction explicitly.
        from psycopg import sql

        from app.db.tenant import TENANT_SESSION_VAR

        conn.autocommit = False
        conn.execute(
            sql.SQL("SET LOCAL {name} = {value}").format(
                name=sql.Identifier(TENANT_SESSION_VAR),
                value=sql.Literal(tenant_id),
            ),
        )
        try:
            yield conn
        finally:
            conn.rollback()
    finally:
        conn.close()
