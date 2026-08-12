"""Alembic env — wires the migration runtime to ``app.settings``.

The migrator URL is read from :class:`app.settings.Settings` so the
migrator role + BYPASSRLS only ever exist in process memory (env vars
or .env), never in the repo. The app URL is also resolved but only
used by offline migrations (sqlalchemy.url flag).

Traceability: NFR-004 (no secrets in repo), NFR-007 (idempotent
re-runs).
"""

from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.settings import get_settings

# Alembic Config object.
config = context.config

# Configure Python logging from alembic.ini when present.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Migration metadata. M03a ships no SQLAlchemy ORM models — every
# schema artifact is created via ``op.*`` primitives so the source
# of truth remains the migration file itself. ``target_metadata`` is
# required by the Alembic API; ``None`` is the documented value for
# DDL-only projects.
target_metadata = None


def _resolve_migrator_url() -> str:
    """Return the migrator URL (BYPASSRLS) from ``app.settings``.

    Falls back to the literal in alembic.ini ONLY if settings fails
    to resolve — which never happens in practice because ``Settings``
    has defaults. Kept as a separate function for testability.
    """
    return get_settings().migrator_database_url


def run_migrations_offline() -> None:
    """Emit SQL to stdout (no DB connection).

    Used by ``alembic upgrade head --sql`` for code review. The URL
    comes from settings (migrator role) so the SQL is faithful to
    what would run.
    """
    context.configure(
        url=_resolve_migrator_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations against a live Postgres connection (BYPASSRLS)."""
    cfg = config.get_section(config.config_ini_section, {})
    cfg["sqlalchemy.url"] = _resolve_migrator_url()

    connectable = engine_from_config(
        cfg,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
