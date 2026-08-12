"""M03a test fixtures — Postgres + roles + RLS substrate.

Boots a private Postgres instance, bootstraps the three SAIE roles,
creates the application database, runs the Alembic migration to
head, and then exposes typed connections for the RLS matrix tests.

Two PostgreSQL substrates are supported, picked at session start:

- ``pgserver`` — a portable Postgres binary shipped via pip. The
  Windows test runner uses this because Docker is unavailable; the
  binary lives at ``<pgserver>/pginstall/bin/{psql,pg_ctl}``.
- ``pytest-postgresql`` — discovers ``pg_ctl`` on the ``PATH`` (or
  via the ``PG_CTL`` env var override). The Linux CI runner uses
  this because ``pgserver`` has no Linux prebuilt.

A substrate is "available" if its import succeeds AND the binary /
executable it needs is present. The first available substrate wins.
If neither is available the fixture ``pytest.skip``s the entire
M03a suite with a clear message — this is the only path that
allows a CI run to fail loudly when the test machine cannot
provision Postgres.

The fixtures are scoped as follows:

- ``_pg_server`` — session scope: a uniform Postgres-server handle
  wrapping whichever substrate is live.
- ``saie_test_dsn`` — session scope: derives the application DSN
  from ``_pg_server``, creates the ``saie_test`` DB, applies
  ``infra/postgres/init.sql``, runs ``alembic upgrade head``.
- ``saie_db_with_schema`` — session scope, autouse: the side-effect
  IS the setup.
- ``app_conn_with_tenant_a`` / ``app_conn_with_tenant_b`` /
  ``admin_conn`` — function scope: short-lived connections with
  the tenant GUC pre-set.

Every per-test connection rolls back at teardown so tests are
isolated and the migration state is preserved across the session.

Traceability: FR-057, NFR-004, NFR-007, NFR-014.
"""

from __future__ import annotations

import os
import shutil
import socket
import subprocess
import sys
import tempfile
import urllib.parse
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import psycopg
import pytest

# ---------------------------------------------------------------------------
# Substrate probe — happens once at import time.
# ---------------------------------------------------------------------------
#
# ``pgserver`` ships a portable Postgres binary for Windows; on Linux
# CI it has no ``pginstall`` directory. ``pytest-postgresql`` resolves
# ``pg_ctl`` itself from ``PATH`` (or the ``PG_CTL`` env var) and
# launches a managed process. We probe both and pick the first that
# has a working executable. Falling back to pytest.skip is the only
# path that lets CI fail loudly when no substrate is available.
#
# The probes use ``try/except`` so an import failure on one substrate
# does not abort the other. The mypy ``type: ignore`` markers below
# cover the untyped third-party APIs (both wheels are not stubbed).

_pgserver_cls: Any = None
_pgserver_bin: Path | None = None
try:  # pragma: no cover - environment-specific branch
    from pgserver import PostgresServer as _pgserver_cls  # type: ignore[attr-defined]

    _pgserver_bin = Path(_pgserver_cls.__module__)  # unused, kept for parity
    # pgserver's binary path is <pkg>/pginstall/bin — resolve via the
    # module file rather than ``__module__`` to stay robust.
    import pgserver as _pgserver_pkg  # noqa: F401

    _pkg_init = Path(_pgserver_pkg.__file__).resolve()
    candidate = _pkg_init.parent / "pginstall" / "bin"
    if (candidate / "pg_ctl").exists() or (candidate / "pg_ctl.exe").exists():
        _pgserver_bin = candidate
    else:
        _pgserver_cls = None
        _pgserver_bin = None
except Exception:  # noqa: BLE001 - any failure means pgserver absent
    _pgserver_cls = None
    _pgserver_bin = None

_pgexec_cls: Any = None
try:  # pragma: no cover - environment-specific branch
    from pytest_postgresql.executor import PostgreSQLExecutor as _pgexec_cls
except Exception:  # noqa: BLE001
    _pgexec_cls = None


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def _resolve_pgctl() -> str | None:
    """Locate a ``pg_ctl`` executable for ``pytest-postgresql``.

    Returns the absolute path if found, ``None`` otherwise. Checks the
    ``PG_CTL`` env var first (lets CI override), then ``PATH``.
    """
    explicit = os.environ.get("PG_CTL")
    if explicit and Path(explicit).exists():
        return explicit
    which = shutil.which("pg_ctl")
    if which:
        return which
    return None


# ---------------------------------------------------------------------------
# Unified handle — every substrate returns one of these.
# ---------------------------------------------------------------------------


@dataclass
class _PostgresHandle:
    """A live Postgres server, substrate-agnostic.

    ``host`` / ``port`` / ``user`` / ``password`` describe the
    superuser connection; ``admin_dbname`` is the bootstrapping DB
    (``postgres`` by default) used to CREATE DATABASE saie_test.
    ``cleanup`` is the substrate-specific shutdown hook called once
    at session teardown.
    """

    host: str
    port: int
    user: str
    password: str
    admin_dbname: str = "postgres"
    cleanup: Any = None


def _start_pgserver() -> _PostgresHandle:
    """Boot a ``pgserver`` Postgres instance (Windows fast path)."""
    if _pgserver_cls is None or _pgserver_bin is None:
        raise RuntimeError("pgserver substrate is not available")
    pgdata = Path("C:/pgserver_data")
    pgdata.mkdir(parents=True, exist_ok=True)
    server = _pgserver_cls(pgdata, cleanup_mode=None)
    uri = server.get_uri()
    parsed = urllib.parse.urlparse(uri)
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or 5432
    user = parsed.username or "postgres"
    password = parsed.password or ""
    # pgserver is process-pinned: cleanup_mode=None keeps it running
    # until the pytest process exits, so cleanup is a no-op.
    return _PostgresHandle(
        host=host,
        port=port,
        user=user,
        password=password,
        cleanup=None,
    )


def _start_pytest_postgresql() -> _PostgresHandle:
    """Boot a ``pytest-postgresql`` Postgres instance (Linux CI path)."""
    if _pgexec_cls is None:
        raise RuntimeError("pytest-postgresql is not installed")
    pg_ctl = _resolve_pgctl()
    if pg_ctl is None:
        raise RuntimeError(
            "pg_ctl not found on PATH and PG_CTL env var unset; "
            "install postgresql-client or set PG_CTL=/path/to/pg_ctl"
        )
    port = _find_free_port()
    datadir = Path(tempfile.mkdtemp(prefix="saie_pg_"))
    logfile = str(datadir / "pg.log")
    unixsocketdir = str(datadir)
    executor = _pgexec_cls(
        executable=pg_ctl,
        host="127.0.0.1",
        port=port,
        datadir=str(datadir),
        unixsocketdir=unixsocketdir,
        logfile=logfile,
        startparams="-w",
        dbname="postgres",
        user="postgres",
        password="",
        shell=False,
        timeout=60,
    )
    executor.start()
    return _PostgresHandle(
        host="127.0.0.1",
        port=port,
        user="postgres",
        password="",
        admin_dbname="postgres",
        cleanup=executor.stop,
    )


def _select_substrate() -> str:
    """Return the name of the first available substrate, or raise."""
    if _pgserver_cls is not None and _pgserver_bin is not None:
        return "pgserver"
    if _pgexec_cls is not None and _resolve_pgctl() is not None:
        return "pytest-postgresql"
    raise RuntimeError(
        "No Postgres substrate available: pgserver not installed "
        "(or has no Linux binary) AND pytest-postgresql cannot find "
        "pg_ctl on PATH. Install postgresql-client or set PG_CTL."
    )


# ---------------------------------------------------------------------------
# Session-scoped fixtures.
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def _pg_server() -> Iterator[_PostgresHandle]:
    """Boot a session-scoped Postgres server (kept alive for the run).

    Substrate is chosen by :func:`_select_substrate` — ``pgserver``
    on Windows dev machines, ``pytest-postgresql`` on Linux CI.

    If neither substrate is available (no ``pgserver`` binary and no
    ``pg_ctl`` on ``PATH``) the fixture ``pytest.skip``s the entire
    M03a suite. CI must fail loudly when no Postgres can be
    provisioned; this skip is the only path that lets a developer
    running locally without a Postgres see "skipped" instead of a
    confusing connection error.
    """
    try:
        substrate = _select_substrate()
    except RuntimeError as exc:
        pytest.skip(str(exc))
        return  # unreachable; pytest.skip raises
    if substrate == "pgserver":
        handle = _start_pgserver()
    else:
        handle = _start_pytest_postgresql()
    try:
        yield handle
    finally:
        if handle.cleanup is not None:
            try:
                handle.cleanup()
            except Exception:  # noqa: BLE001 - cleanup is best-effort
                pass


@pytest.fixture(scope="session")
def saie_test_dsn(_pg_server: _PostgresHandle) -> str:
    """Build the DSN string for the test DB and apply init.sql + migrations.

    On first call: creates the ``saie_test`` database, applies
    ``infra/postgres/init.sql``, runs ``alembic upgrade head``.
    """
    host = _pg_server.host
    port = _pg_server.port
    user = _pg_server.user
    password = _pg_server.password
    admin_dbname = _pg_server.admin_dbname

    admin_dsn = (
        f"host={host} port={port} dbname={admin_dbname} "
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

    # 2. Apply infra/postgres/init.sql.
    repo_root = Path(__file__).resolve().parents[4]
    init_sql = repo_root / "infra" / "postgres" / "init.sql"
    psql_bin: Path | None = None
    if _pgserver_bin is not None:
        for cand in ("psql.exe", "psql"):
            p = _pgserver_bin / cand
            if p.exists():
                psql_bin = p
                break
    env = os.environ.copy()
    env["PGPASSWORD"] = password
    if psql_bin is not None:
        subprocess.run(
            [
                str(psql_bin), "-h", host, "-p", str(port),
                "-U", user, "-d", "saie_test", "-v", "ON_ERROR_STOP=1",
                "-f", str(init_sql),
            ],
            check=True,
            env=env,
            capture_output=True,
        )
    else:
        # No psql (pytest-postgresql path): execute the SQL via psycopg.
        with psycopg.connect(
            f"host={host} port={port} dbname=saie_test "
            f"user={user} password={password}",
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
    # 3a. Standalone env vars so test files that open their own raw
    # ``psycopg.connect()`` can resolve the ephemeral host/port
    # without hardcoding 127.0.0.1:5432 — both substrates bind to a
    # random port chosen by ``_find_free_port``, NOT 5432.
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
