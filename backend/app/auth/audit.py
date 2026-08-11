"""Auth audit logger — the typed event stream M15 + M14 consume.

The interface is intentionally tiny so the production logger (a
PostgreSQL writer in M03) can drop in without changing callers.

Audit failures NEVER propagate (NFR-007). A broken audit must not
also break authentication — the request still succeeds or fails on
the auth decision alone, and the failure is logged via stdlib
``logging`` for ops to find.

Traceability: FR-054 (audit groundwork).
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Protocol, runtime_checkable

logger = logging.getLogger(__name__)


class AuthEventType(str, Enum):
    """Closed set of auth event types.

    Adding a value is an explicit, documented change — every consumer
    (dashboards, alert rules, governance reports) switches on this.
    """

    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILED = "login_failed"
    LOGOUT = "logout"
    TOKEN_REFRESH = "token_refresh"
    ROLE_DENIED = "role_denied"
    TENANT_DENIED = "tenant_denied"
    TOKEN_INVALID = "token_invalid"


@dataclass(frozen=True)
class AuthEvent:
    """A single auth event, serialised to the wire by ``to_dict``.

    ``outcome`` is a free-form short label (``"success"`` /
    ``"failure"`` / etc.) so downstream consumers can aggregate
    without parsing the event_type.
    """

    event_type: AuthEventType
    subject: str
    tenant_id: str
    ip: str
    user_agent: str
    outcome: str
    reason: str | None = None
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe dict with a stable field set."""
        data = asdict(self)
        data["event_type"] = self.event_type.value
        data["occurred_at"] = self.occurred_at.isoformat()
        return data


@runtime_checkable
class AuthAuditLogger(Protocol):
    """The audit interface every implementation satisfies.

    Marked ``@runtime_checkable`` so the ``isinstance(audit_logger,
    AuthAuditLogger)`` checks in ``deps.py`` and ``middleware.py`` work
    at runtime, not just to a type checker.
    """

    def log(self, event: AuthEvent) -> None:  # pragma: no cover - protocol
        ...


class InMemoryAuditLogger:
    """Process-local audit log.

    Suitable for unit tests, local dev, and any context where the
    audit volume is small. Production swaps in the PostgreSQL-backed
    implementation in M03.
    """

    def __init__(self) -> None:
        self._events: list[AuthEvent] = []

    def _append(self, event: AuthEvent) -> None:
        """Real append path — split out so monkeypatch-friendly tests work."""
        self._events.append(event)

    def log(self, event: AuthEvent) -> None:
        """Record the event. Swallows exceptions — NFR-007.

        The failure is logged via stdlib ``logging`` so ops can still
        see "audit broke" in their log aggregator.
        """
        try:
            self._append(event)
        except Exception as exc:  # noqa: BLE001 - audit must never crash
            logger.warning("Auth audit logger failed: %s", exc, exc_info=False)

    def events(self) -> list[AuthEvent]:
        """Return the recorded events (public read API for tests/dashboards).

        Returns a fresh list copy so callers cannot mutate internal state.
        """
        return list(self._events)

    # Backwards-compatible alias; ``events()`` is the canonical name.
    snapshot = events


#: DDL shipped in ``infra/db/init/01_auth.sql`` for M03 to take over.
#: Idempotent so running ``psql -f`` on an already-bootstrapped DB
#: is a no-op.
POSTGRES_AUTH_AUDIT_DDL = """
CREATE TABLE IF NOT EXISTS auth_events (
    id              BIGSERIAL PRIMARY KEY,
    event_type      TEXT NOT NULL,
    subject         TEXT NOT NULL,
    tenant_id       TEXT NOT NULL,
    ip              TEXT NOT NULL,
    user_agent      TEXT NOT NULL,
    outcome         TEXT NOT NULL,
    reason          TEXT,
    occurred_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS auth_events_subject_idx
    ON auth_events (subject, occurred_at DESC);

CREATE INDEX IF NOT EXISTS auth_events_tenant_idx
    ON auth_events (tenant_id, occurred_at DESC);
""".strip()
