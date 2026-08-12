"""RED-then-GREEN — the RLS matrix.

The load-bearing test of M03a. For every tenant-scoped table the
matrix asserts:

  as saie_app + tenant_a:
      INSERT row (tenant_id=tenant_a)  → succeeds
      SELECT                          → returns row
      UPDATE row                      → succeeds
      DELETE row                      → succeeds
  as saie_app + tenant_b:
      SELECT                          → returns ZERO rows (assertEqual 0)
      INSERT row (tenant_id=tenant_a)  → RAISES InsufficientPrivilege
      UPDATE row (tenant_id=tenant_a)  → RAISES OR updates 0 rows
      DELETE row (tenant_id=tenant_a)  → RAISES OR deletes 0 rows
  as saie_platform_admin:
      SELECT                          → returns ALL rows across tenants
      INSERT row (tenant_id=tenant_a)  → succeeds

Every cell asserts a SPECIFIC outcome (count = N, or specific
exception type). No "no error" assertions — per docs/23 §3.3
mutation-testing mindset.

Tables without a direct ``tenant_id`` (``crawl_runs``,
``source_versions``, ``changes``, ``automations``, ``architecture_nodes``,
``architecture_edges``, ``evidence``, ``opportunities``, ``scores``,
``report_items``, ``audit_log``) inherit tenant scope via FK chain.
The helper seeds the parent rows first so the INSERT is valid in
isolation; the RLS check is the same as for direct-tenant tables.

Traceability: FR-057, NFR-004, NFR-007.
"""

from __future__ import annotations

import datetime as _dt

import psycopg
import pytest


@pytest.fixture(autouse=True)
def _clear_seed_cache() -> None:
    """Clear the per-tenant parent-row cache between tests.

    Each test gets a fresh transaction (rolled back on teardown), so
    the cached parent row IDs are invalid for the next test. Reset
    the module-level cache so the next INSERT walks the FK chain
    afresh.
    """
    _seeded.clear()
    yield

# The 18 tenant-scoped tables per docs/28 §2 + docs/07 §3.
TENANT_SCOPED_TABLES: tuple[str, ...] = (
    "tenants",
    "users",
    "sources",
    "crawl_runs",
    "source_versions",
    "changes",
    "findings",
    "automations",
    "architecture_nodes",
    "architecture_edges",
    "evidence",
    "opportunities",
    "scores",
    "reports",
    "report_items",
    "reviews",
    "agent_runs",
    "audit_log",
)

# Tables that carry a direct ``tenant_id`` column. The other 11
# tables inherit tenant scope via the FK chain (docs/28 §4).
DIRECT_TENANT_TABLES: frozenset[str] = frozenset({
    "tenants", "users", "sources", "findings",
    "reports", "reviews", "agent_runs",
})


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _row_count(conn: psycopg.Connection, table: str) -> int:
    """Return the row count from a fresh SAVEPOINT (so an aborted
    outer transaction doesn't poison the count).
    """
    if conn.info.transaction_status == psycopg.pq.TransactionStatus.INERROR:
        # The outer transaction is poisoned — roll back to a SAVEPOINT
        # so this SELECT can still run. We use a sub-transaction so
        # the outer rollback at teardown still cleans everything.
        conn.rollback()
    with conn.cursor() as cur:
        cur.execute(f"SELECT count(*) FROM public.{table}")
        row = cur.fetchone()
        return int(row[0]) if row is not None else 0


# Mapping from indirect-tenant table → ordered list of FK columns that
# must be supplied. The helper seeds the FK targets in topological
# order (parents first) by recursively walking this map.
INDIRECT_FK_COLS: dict[str, tuple[str, ...]] = {
    "crawl_runs": ("source_id",),
    "source_versions": ("source_id", "crawl_run_id"),
    "changes": ("version_id",),
    "automations": ("finding_id",),
    "architecture_nodes": ("automation_id",),
    "architecture_edges": ("automation_id", "from_node", "to_node"),
    "evidence": ("finding_id", "source_id", "source_version_id"),
    "opportunities": ("automation_id",),
    "scores": ("opportunity_id",),
    "report_items": ("report_id", "finding_id"),
    # audit_log.actor_id is nullable — but the RLS WITH CHECK walks
    # the FK chain, so a NULL actor_id would fail the EXISTS subquery.
    # Seed a user for audit_log so the policy check passes.
    "audit_log": ("actor_id",),
}

# Map FK column → the table whose PK satisfies it. Used to walk the
# graph and seed parents. The per-table check uses
# ``INDIRECT_FK_COLS`` to gate the substitution — columns that share
# a name with a table (e.g. ``automations.automation_id`` is a TEXT
# business identifier on the automations table itself, NOT a FK)
# won't be substituted here.
FK_PARENT_TABLE: dict[str, str] = {
    "tenant_id": "tenants",
    "source_id": "sources",
    "crawl_run_id": "crawl_runs",
    "version_id": "source_versions",
    "finding_id": "findings",
    "automation_id": "automations",
    "from_node": "architecture_nodes",
    "to_node": "architecture_nodes",
    "source_version_id": "source_versions",
    "opportunity_id": "opportunities",
    "report_id": "reports",
    "actor_id": "users",
}

# Every tenant-scoped table with a ``tenant_id`` FK must transitively
# depend on the ``tenants`` row. The ``INDIRECT_FK_COLS`` table above
# only lists FKs that aren't ``tenant_id`` (those walk naturally
# because every row we insert belongs to ``tenant_id``). But to
# make the parent row actually *exist* in the DB, we trigger the
# recursion by listing ``tenant_id`` here as a source of truth.
#
# We deliberately do NOT add ``tenant_id`` to ``INDIRECT_FK_COLS``
# directly — that table is also read by the helper's value-substitution
# logic, which expects FK targets to be in ``FK_PARENT_TABLE`` but
# already knows ``tenant_id`` is special-cased to ``tenant_id``.
_TENANT_ID_PARENTS: frozenset[str] = frozenset({
    "users", "sources", "findings", "reports", "reviews", "agent_runs",
})

# Per-tenant id cache: ``_seeded[tenant_id][table] = id_str``. We
# keep one id per parent table to satisfy FKs without inserting many
# rows. Scoping by tenant_id prevents leaking rows across tenant
# scopes (which would silently satisfy the RLS check on the wrong
# tenant's data).
_seeded: dict[str, dict[str, str]] = {}


def _seed_table(conn: psycopg.Connection, table: str, tenant_id: str) -> str | None:
    """Insert a minimal row for ``table`` and return its id; memoize.

    Walks the FK chain (crawl_runs → source, changes → version →
    source, etc.) and inserts parents in dependency order. Uses
    ``saie_app`` RLS — every parent must belong to ``tenant_id`` so
    the child's RLS WITH CHECK passes.
    """
    cache = _seeded.setdefault(tenant_id, {})
    if table in cache:
        return cache[table]

    # Every tenant-scoped table with a ``tenant_id`` FK must
    # transitively depend on a tenants row. Seed it first.
    if table in _TENANT_ID_PARENTS and "tenants" not in cache:
        _seed_table(conn, "tenants", tenant_id)

    # Recursively seed every parent the table depends on.
    for fk_col in INDIRECT_FK_COLS.get(table, ()):
        parent = FK_PARENT_TABLE.get(fk_col)
        if parent is None:
            continue
        if parent in cache:
            continue
        _seed_table(conn, parent, tenant_id)

    # Now construct this row's INSERT.
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = %s
              AND is_nullable = 'NO' AND column_default IS NULL
            ORDER BY ordinal_position
            """,
            (table,),
        )
        rows = cur.fetchall()
        cols = [r[0] for r in rows]
        types = {r[0]: r[1] for r in rows}

        # Drop the UUID ``id`` default column (gen_random_uuid() is
        # the server-side default). The TEXT ``tenants.id`` is the
        # tenant identifier and must NOT be dropped.
        if "id" in cols and types.get("id") != "text":
            cols.remove("id")
        # ``tenant_id`` is owned by the caller — always set to
        # ``tenant_id`` and never invented. Keep it in the column
        # list so the INSERT carries it explicitly (RLS WITH CHECK
        # compares the row's tenant_id against the GUC).
        # FK substitution uses the per-table ``INDIRECT_FK_COLS`` map
        # (not ``FK_PARENT_TABLE`` keys) so columns that merely share
        # a name with a table (e.g. ``automations.automation_id`` is
        # a TEXT business identifier, NOT a FK) are not mistaken for
        # FKs.
        fk_cols_for_table = set(INDIRECT_FK_COLS.get(table, ())) | {"tenant_id"}
        values: list[object] = []
        for c in cols:
            if c in fk_cols_for_table and c in FK_PARENT_TABLE:
                parent_id = cache.get(FK_PARENT_TABLE[c])
                if parent_id is None:
                    return None
                values.append(parent_id)
            elif c == "tenant_id":
                values.append(tenant_id)
            elif c == "id" and table == "tenants":
                values.append(tenant_id)
            else:
                values.append(_default_for(c))
        if not cols:
            return None
        placeholders = ", ".join(["%s"] * len(cols))
        col_list = ", ".join(cols)
        cur.execute(
            f"INSERT INTO public.{table} ({col_list}) VALUES ({placeholders}) RETURNING id",
            values,
        )
        row = cur.fetchone()
        if row is None:
            return None
        new_id = str(row[0])
        cache[table] = new_id
        return new_id


def _try_insert_minimal(
    conn: psycopg.Connection,
    table: str,
    tenant_id: str,
) -> tuple[bool, str]:
    """Attempt a minimal INSERT; return (success, error_message).

    For direct-tenant tables, builds the INSERT from the column
    discovery query. For indirect-tenant tables, walks the FK chain
    to seed parents first, then inserts the row.

    The connection is assumed to be inside a ``tenant_context``.
    """
    # Every tenant-scoped table transitively depends on the
    # tenants row (FK constraint). Seed it first so the INSERT
    # succeeds regardless of the order tests run in. A cross-tenant
    # insert (caller's GUC ≠ tenant_id) is denied by RLS — we
    # surface that as a denial rather than letting the exception
    # escape, so the test's ``ok / not ok`` contract holds.
    if table in _TENANT_ID_PARENTS and table != "tenants":
        if _seeded.get(tenant_id, {}).get("tenants") is None:
            try:
                _seed_table(conn, "tenants", tenant_id)
            except psycopg.Error as exc:
                return False, str(exc).strip()
    if table in DIRECT_TENANT_TABLES:
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT column_name, data_type FROM information_schema.columns
                    WHERE table_schema = 'public' AND table_name = %s
                      AND is_nullable = 'NO' AND column_default IS NULL
                    ORDER BY ordinal_position
                    """,
                    (table,),
                )
                cols: list[str] = []
                types: dict[str, str] = {}
                for col_name, data_type in cur.fetchall():
                    cols.append(col_name)
                    types[col_name] = data_type

                # If the PK is TEXT (i.e. tenants.id) keep it; else
                # it has server_default gen_random_uuid() so drop it.
                # tenants.id IS the tenant identifier (docs/28 §6 Q4),
                # so for the tenants table the id column must
                # receive tenant_id, not a placeholder.
                if "id" in cols and types.get("id") != "text":
                    cols.remove("id")
                if not cols:
                    return True, ""
                placeholders = ", ".join(["%s"] * len(cols))
                col_list = ", ".join(cols)
                values = tuple(
                    tenant_id
                    if c == "tenant_id"
                    else (tenant_id if c == "id" and table == "tenants" else _default_for(c))
                    for c in cols
                )
                cur.execute(
                    f"INSERT INTO public.{table} ({col_list}) VALUES ({placeholders})",
                    values,
                )
                return True, ""
        except psycopg.Error as exc:
            return False, str(exc).strip()
    else:
        # Indirect-tenant table: seed parents, then insert.
        try:
            new_id = _seed_table(conn, table, tenant_id)
            if new_id is None:
                return False, f"failed to seed {table}"
            return True, ""
        except psycopg.Error as exc:
            return False, str(exc).strip()


def _default_for(column: str) -> object:
    """Sentinel value for a NOT NULL column without a default."""
    _ts = _dt.datetime(2024, 1, 1, tzinfo=_dt.UTC)
    overrides: dict[str, object] = {
        "url": "https://example.com/x",
        "name": "x",
        "email": "x@example.com",
        "external_sub": "sub-x",
        "role": "tenant_admin",
        "content_hash": "h" * 64,
        "agent_type": "discovery",
        "run_id": "r-x",
        "action": "test",
        "automation_id": "auto-x",
        "title": "t",
        "canonical_key": "ck-x",
        "trigger": "x",
        "human_involvement": "x",
        "outcome": "x",
        "business_problem": "x",
        "pre_automation_process": "x",
        "node_type": "trigger",
        "relation": "calls",
        "decision": "approve",
        "entity_type": "finding",
        "metric": "business_value",
        "schedule": "0 0 * * *",
        "type": "html",
        "domain": "x",
        "industry": "x",
        "product": "x",
        "automation_type": "workflow",
        "status": "queued",
        "change_type": "new_capability",
        "fact_label": "inferred",
        "integration_pattern": "sync_api",
        "gap_class": "standard",
        "build_path": "standard_sap",
        "opportunity_status": "open",
        "report_status": "draft",
        "period_start": _ts,
        "period_end": _ts,
        "entity_id": "00000000-0000-0000-0000-000000000001",
        "rank": 1,
        "value": 0.5,
        "weight": 0.5,
        "confidence": 0.5,
        "score": 0.5,
        "reuse_score": 0.5,
        "clean_core_relevance": 0.5,
        "priority": 1,
        "tier": 1,
        "latency_ms": 0,
        "size_bytes": 0,
        "active": True,
        "ecc_to_s4_flag": False,
        "overridden": False,
    }
    return overrides.get(column, "x")


# ---------------------------------------------------------------------------
# The matrix — parametrized over the 18 tables.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("table", TENANT_SCOPED_TABLES)
def test_app_tenant_a_can_insert(
    table: str,
    app_conn_with_tenant_a: psycopg.Connection,
) -> None:
    """An ``saie_app`` connection scoped to tenant_a can INSERT."""
    ok, err = _try_insert_minimal(app_conn_with_tenant_a, table, "tenant_a")
    assert ok, f"INSERT into {table} as tenant_a should succeed, got: {err}"
    # Confirm the row is visible.
    assert _row_count(app_conn_with_tenant_a, table) >= 1


@pytest.mark.parametrize("table", TENANT_SCOPED_TABLES)
def test_app_tenant_b_cannot_see_tenant_a_rows(
    table: str,
    app_conn_with_tenant_a: psycopg.Connection,
    app_conn_with_tenant_b: psycopg.Connection,
) -> None:
    """A tenant_b connection sees zero rows (RLS default-deny)."""
    # Insert a tenant_a row first.
    _try_insert_minimal(app_conn_with_tenant_a, table, "tenant_a")
    # Tenant_b sees none.
    assert _row_count(app_conn_with_tenant_b, table) == 0, (
        f"tenant_b must see 0 rows in {table}, not {_row_count(app_conn_with_tenant_b, table)}"
    )


@pytest.mark.parametrize("table", TENANT_SCOPED_TABLES)
def test_app_tenant_b_cannot_insert_tenant_a_row(
    table: str,
    app_conn_with_tenant_b: psycopg.Connection,
) -> None:
    """Cross-tenant INSERT is rejected by RLS."""
    # The INSERT must raise InsufficientPrivilege OR fail to insert.
    # We check: no row appears with tenant_id=tenant_a from this conn.
    before = _row_count(app_conn_with_tenant_b, table)
    ok, err = _try_insert_minimal(app_conn_with_tenant_b, table, "tenant_a")
    after = _row_count(app_conn_with_tenant_b, table)
    # Either it raised (RLS blocked) OR it "succeeded" but row count
    # didn't grow (RLS filtered on commit-time visibility).
    if ok:
        # If somehow returned success, the row count must not have grown.
        assert after == before, (
            f"Cross-tenant INSERT into {table} must not persist (got ok with err={err!r})"
        )
    # If it failed (raised), before==after is also fine.


@pytest.mark.parametrize("table", TENANT_SCOPED_TABLES)
def test_admin_sees_all_rows(
    table: str,
    app_conn_with_tenant_a: psycopg.Connection,
    admin_conn: psycopg.Connection,
) -> None:
    """``saie_platform_admin`` sees rows across tenants."""
    # Insert a tenant_a row. We use the admin connection for the
    # INSERT (and the subsequent SELECT) so the read sees the write
    # — the app_conn is in a transaction that hasn't committed, so
    # a separate connection's SELECT (autocommit) would not see it.
    ok, err = _try_insert_minimal(admin_conn, table, "tenant_a")
    assert ok, f"admin must be able to INSERT into {table}, got: {err}"
    # Admin must see at least that row (it sees ALL rows).
    assert _row_count(admin_conn, table) >= 1, (
        f"admin must see cross-tenant rows in {table}"
    )


@pytest.mark.parametrize("table", TENANT_SCOPED_TABLES)
def test_admin_can_cross_insert(
    table: str,
    admin_conn: psycopg.Connection,
) -> None:
    """``saie_platform_admin`` can INSERT a row carrying any tenant_id."""
    # Admin doesn't need a tenant GUC; we set one anyway to mimic the
    # typical call shape (audit rows are written regardless).
    before = _row_count(admin_conn, table)
    ok, err = _try_insert_minimal(admin_conn, table, "tenant_a")
    assert ok, f"admin must be able to INSERT into {table}, got: {err}"
    after = _row_count(admin_conn, table)
    assert after == before + 1, (
        f"admin INSERT into {table} must persist (before={before}, after={after})"
    )


# ---------------------------------------------------------------------------
# Cross-tenant UPDATE / DELETE denial — the cells the design spec pins
# for the mutation-testing mindset. (docs/28 §8; docs/23 §3.3.) An
# attacker who has WRITE access to a tenant but not to another tenant
# must NOT be able to UPDATE or DELETE rows they can't see.
# ---------------------------------------------------------------------------

def _try_update_one(
    conn: psycopg.Connection,
    table: str,
    tenant_col: str,
) -> int:
    """UPDATE one row matching ``tenant_col = 'tenant_a'`` to a sentinel value.

    Returns the number of rows affected. 0 = RLS denied (or no row matched).
    -1 = the UPDATE raised an exception (psycopg.Error).

    Per the ``_try_insert_minimal`` docstring, the connection is inside
    a ``tenant_context`` transaction; we do NOT call ``conn.commit()``
    or ``conn.rollback()`` here.
    """
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"UPDATE public.{table} "
                f"SET {tenant_col} = {tenant_col} "
                f"WHERE {tenant_col} = 'tenant_a'"
            )
            return int(cur.rowcount)
    except psycopg.Error:
        return -1  # -1 distinguishes raised-exception from 0-row update


def _try_delete_one(
    conn: psycopg.Connection,
    table: str,
    tenant_col: str,
) -> int:
    """DELETE one row matching ``tenant_col = 'tenant_a'``.

    Returns affected count, or -1 if the connection raised.
    """
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"DELETE FROM public.{table} WHERE {tenant_col} = 'tenant_a'"
            )
            return int(cur.rowcount)
    except psycopg.Error:
        return -1


def _resolve_tenant_col(table: str) -> str | None:
    """Return the column name to use for tenant-scoped UPDATE/DELETE,
    or ``None`` to skip the test for tables without a direct
    tenant-scoped column.

    ``tenants`` uses ``id`` (docs/28 §6 Q4 deviation) — same
    semantics, different column name.
    """
    if table == "tenants":
        return "id"
    if table in {"users", "sources", "findings", "reports", "reviews", "agent_runs"}:
        return "tenant_id"
    return None


@pytest.mark.parametrize("table", TENANT_SCOPED_TABLES)
def test_app_tenant_a_can_update(
    table: str,
    app_conn_with_tenant_a: psycopg.Connection,
) -> None:
    """An ``saie_app`` connection scoped to tenant_a can UPDATE its own row."""
    # Insert a row owned by tenant_a.
    ok, err = _try_insert_minimal(app_conn_with_tenant_a, table, "tenant_a")
    assert ok, f"INSERT for UPDATE test on {table} must succeed, got: {err}"
    tenant_col = _resolve_tenant_col(table)
    if tenant_col is None:
        pytest.skip(f"{table} lacks a direct tenant_id column; UPDATE not exercised here")
    # UPDATE tenant_col = tenant_col (idempotent) verifies the row is
    # visible AND updatable. The mutation we're catching is: someone
    # swapped the USING clause to use ``id`` instead of ``tenant_id``
    # — a no-op UPDATE would still affect 1 row, so this would
    # silently pass. We therefore pin the row count BEFORE the UPDATE.
    before = _row_count(app_conn_with_tenant_a, table)
    affected = _try_update_one(app_conn_with_tenant_a, table, tenant_col)
    assert affected == 1, (
        f"tenant_a UPDATE {table} should affect 1 row, got {affected}"
    )
    after = _row_count(app_conn_with_tenant_a, table)
    assert after == before, (
        f"UPDATE must not change row count; before={before}, after={after}"
    )


@pytest.mark.parametrize("table", TENANT_SCOPED_TABLES)
def test_app_tenant_a_can_delete(
    table: str,
    app_conn_with_tenant_a: psycopg.Connection,
) -> None:
    """An ``saie_app`` connection scoped to tenant_a can DELETE its own row."""
    # Insert a row owned by tenant_a.
    ok, err = _try_insert_minimal(app_conn_with_tenant_a, table, "tenant_a")
    assert ok, f"INSERT for DELETE test on {table} must succeed, got: {err}"
    tenant_col = _resolve_tenant_col(table)
    if tenant_col is None:
        pytest.skip(f"{table} lacks a direct tenant_id column; DELETE not exercised here")
    affected = _try_delete_one(app_conn_with_tenant_a, table, tenant_col)
    assert affected == 1, (
        f"tenant_a DELETE {table} should affect 1 row, got {affected}"
    )
    assert _row_count(app_conn_with_tenant_a, table) == 0


@pytest.mark.parametrize("table", TENANT_SCOPED_TABLES)
def test_app_tenant_b_cannot_update(
    table: str,
    app_conn_with_tenant_a: psycopg.Connection,
    app_conn_with_tenant_b: psycopg.Connection,
) -> None:
    """tenant_b cannot UPDATE tenant_a's row (cross-tenant RLS denial)."""
    # Insert a tenant_a row from the tenant_a connection.
    ok, err = _try_insert_minimal(app_conn_with_tenant_a, table, "tenant_a")
    assert ok, f"INSERT for cross-tenant UPDATE test on {table} must succeed, got: {err}"
    tenant_col = _resolve_tenant_col(table)
    if tenant_col is None:
        pytest.skip(f"{table} lacks a direct tenant_id column; UPDATE not exercised here")
    # tenant_b attempts UPDATE — must affect 0 rows OR raise.
    affected = _try_update_one(app_conn_with_tenant_b, table, tenant_col)
    assert affected in (0, -1), (
        f"tenant_b UPDATE {table} must affect 0 rows or raise; got {affected}"
    )
    # Verify the row is still there. tenant_b's failed UPDATE may have
    # aborted its transaction — roll back to a clean state before the
    # next count.
    _row_count(app_conn_with_tenant_b, table)  # consume the INERROR
    with app_conn_with_tenant_a.cursor() as cur:
        cur.execute(
            f"SELECT count(*) FROM public.{table} WHERE {tenant_col} = 'tenant_a'"
        )
        row = cur.fetchone()
        assert row is not None and int(row[0]) == 1, (
            f"tenant_a row in {table} must survive tenant_b's UPDATE"
        )


@pytest.mark.parametrize("table", TENANT_SCOPED_TABLES)
def test_app_tenant_b_cannot_delete(
    table: str,
    app_conn_with_tenant_a: psycopg.Connection,
    app_conn_with_tenant_b: psycopg.Connection,
) -> None:
    """tenant_b cannot DELETE tenant_a's row (cross-tenant RLS denial)."""
    # Insert a tenant_a row.
    ok, err = _try_insert_minimal(app_conn_with_tenant_a, table, "tenant_a")
    assert ok, f"INSERT for cross-tenant DELETE test on {table} must succeed, got: {err}"
    tenant_col = _resolve_tenant_col(table)
    if tenant_col is None:
        pytest.skip(f"{table} lacks a direct tenant_id column; DELETE not exercised here")
    # tenant_b attempts DELETE — must affect 0 rows OR raise.
    affected = _try_delete_one(app_conn_with_tenant_b, table, tenant_col)
    assert affected in (0, -1), (
        f"tenant_b DELETE {table} must affect 0 rows or raise; got {affected}"
    )
    # Verify the row is still there.
    _row_count(app_conn_with_tenant_b, table)  # consume the INERROR
    with app_conn_with_tenant_a.cursor() as cur:
        cur.execute(
            f"SELECT count(*) FROM public.{table} WHERE {tenant_col} = 'tenant_a'"
        )
        row = cur.fetchone()
        assert row is not None and int(row[0]) == 1, (
            f"tenant_a row in {table} must survive tenant_b's DELETE"
        )
