"""Postgres session-var contract — the single source of truth.

This module owns every name, read, and write of the Postgres
session-variable that scopes the RLS policies shipped in M03a:

- ``TENANT_SESSION_VAR`` — the GUC name (``"app.tenant_id"``). The
  lint rule pinned in docs/23 §3.5 forbids any other module from
  referencing this string literal.
- ``current_tenant_id(conn)`` — NULL-safe reader; returns ``None``
  when the GUC has not been set in the current transaction.
- ``tenant_context(conn, tenant_id, role)`` — ``ContextManager``
  that wraps a transaction and issues ``SET LOCAL`` so the GUC is
  visible to RLS policies. ``SET LOCAL`` is transaction-scoped, so
  the GUC is cleared on ``COMMIT`` / ``ROLLBACK`` / connection close
  — exactly the recoverability story NFR-007 requires.
- ``is_cross_tenant_role(role)`` — ``True`` iff ``role`` is
  :class:`Role.PLATFORM_ADMIN`.

Failure modes (NFR-007):

- ``SET LOCAL`` outside a transaction raises
  ``psycopg.errors.InvalidTransactionState``. ``tenant_context``
  MUST wrap in an explicit ``BEGIN`` (we use ``autocommit=False``).
- ``SET LOCAL`` nested in an already-open transaction is a no-op
  the second time; we raise to fail loud rather than silently
  re-scoping an unrelated caller's transaction.
- If ``SET LOCAL`` raises (network blip, deadlock, etc.) the
  context manager rolls back and re-raises. The caller (M02's
  :class:`AuthAuditLogger`) writes an audit row.

Traceability: FR-057, NFR-004, NFR-007.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import TYPE_CHECKING

import psycopg
from psycopg import sql

if TYPE_CHECKING:
    from app.auth.roles import Role


#: The Postgres session-variable name every RLS policy reads. This is
#: the ONLY place in ``backend/app/`` that is allowed to spell this
#: literal. ``git grep -n '"app.tenant_id"' backend/app/`` must return
#: exactly one match — here.
TENANT_SESSION_VAR: str = "app.tenant_id"


def _query_tenant_setting(conn: psycopg.Connection[tuple[object, object]]) -> str | None:
    """Return the current value of :data:`TENANT_SESSION_VAR` or ``None``.

    The ``true`` second argument to ``current_setting`` makes the call
    NULL-safe: it returns ``NULL`` (which ``psycopg`` maps to ``None``)
    when the GUC has not been set in this session / transaction.

    The identifier is interpolated through :class:`psycopg.sql.SQL`
    so the GUC name can never be tainted by an attacker-controlled
    string. The value is NEVER interpolated — only the name.
    """
    query = sql.SQL("SELECT current_setting({name}, true)").format(
        name=sql.Literal(TENANT_SESSION_VAR),
    )
    with conn.cursor() as cur:
        cur.execute(query)
        row = cur.fetchone()
    # ``fetchone`` of a SELECT is always a 1-tuple; the column may be
    # NULL when the GUC has never been touched. After a ``SET LOCAL``
    # is cleared by COMMIT/ROLLBACK, the GUC falls back to its
    # default — Postgres returns the empty string ``''`` for
    # undeclared custom GUCs, NOT NULL. We treat empty string as
    # semantically "unset" so callers see a single ``None`` value
    # whether the GUC was never set or was set-then-cleared in a
    # previous transaction.
    if row is None or row[0] is None:
        return None
    value = str(row[0])
    return None if value == "" else value


def current_tenant_id(conn: psycopg.Connection[tuple[object, object]]) -> str | None:
    """Return the tenant id of the current transaction, or ``None``.

    NULL-safe: when no ``tenant_context`` has been entered on this
    connection (or the connection has no open transaction), this
    returns ``None`` rather than raising — so a misconfigured
    connection that forgot to scope itself returns zero rows from
    RLS-protected tables (the default-deny posture) without crashing
    the request.
    """
    return _query_tenant_setting(conn)


@contextmanager
def tenant_context(
    conn: psycopg.Connection[tuple[object, object]],
    tenant_id: str,
    role: Role,
) -> Iterator[psycopg.Connection[tuple[object, object]]]:
    """Scope the connection to ``tenant_id`` for the duration of the block.

    On enter, opens an explicit transaction and issues
    ``SET LOCAL app.tenant_id = '<tenant_id>'``. On exit, commits
    (success) or rolls back (exception). ``SET LOCAL`` is
    transaction-scoped — the GUC is cleared the moment the
    transaction ends, which is exactly the recoverability story
    NFR-007 requires.

    Args:
        conn: An open ``psycopg.Connection``. The connection's
            ``autocommit`` is forced off for the duration.
        tenant_id: The tenant id to scope to. Stored verbatim as a
            string in the GUC — no parsing, no validation (the M02
            ``TenantContext`` layer already validated it).
        role: The caller's role. Stored for cross-tenant callers
            (``platform_admin``) so the audit row can attribute
            bypass decisions. NOT stored in any GUC.

    Yields:
        The same connection, inside the open transaction.

    Raises:
        psycopg.errors.InvalidTransactionState: If the caller already
            has an open transaction on ``conn`` — we refuse to nest
            because re-scoping an unrelated caller's transaction
            silently leaks the GUC into their work.
        psycopg.Error: Any other Postgres error during ``BEGIN`` /
            ``SET LOCAL`` propagates after a rollback.
    """
    if not tenant_id:
        raise ValueError("tenant_id must be a non-empty string")

    if conn.info.transaction_status != psycopg.pq.TransactionStatus.IDLE:
        # ``0`` in libpq is IDLE (no transaction open). Anything else
        # (ACTIVE=1, INTRANS=2, INERROR=3) means the caller is
        # already in a transaction; refuse to nest rather than leak
        # the SET LOCAL into their work.
        raise psycopg.errors.InvalidTransactionState(
            "tenant_context() cannot nest inside an open transaction; "
            "open a fresh connection or commit the outer transaction first",
        )

    # ``SET LOCAL`` only works inside a transaction. Force autocommit
    # off and open one explicitly so the GUC is visible to the
    # policies and cleared on exit.
    was_autocommit = conn.autocommit
    conn.autocommit = False
    try:
        with conn.transaction():
            # ``SET LOCAL`` requires a LITERAL value — Postgres does
            # not accept parameter binding for SET statements, so the
            # tenant id is interpolated through :class:`psycopg.sql.Literal`
            # (which quotes the string safely) rather than passed as
            # a bind parameter. The GUC name is still an Identifier.
            conn.execute(
                sql.SQL("SET LOCAL {name} = {value}").format(
                    name=sql.Identifier(TENANT_SESSION_VAR),
                    value=sql.Literal(tenant_id),
                ),
            )
            yield conn
    finally:
        # Restore the caller's autocommit so we never silently
        # change a connection-pool-wide invariant.
        conn.autocommit = was_autocommit
        # role is intentionally unused at the protocol level; it
        # exists so callers (audit, telemetry) can attribute the
        # bypass without reaching back into the auth layer.
        del role


def is_cross_tenant_role(role: Role) -> bool:
    """Return ``True`` iff ``role`` may bypass tenant scoping.

    The single source of truth for "this role crosses tenants" — M04
    uses it to decide whether to attach to a connection as
    ``saie_platform_admin`` instead of ``saie_app``.
    """
    from app.auth.roles import Role as _Role

    return role is _Role.PLATFORM_ADMIN
