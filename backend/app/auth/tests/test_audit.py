"""RED test — Auth audit logger (FR-054 groundwork).

Pins:

- Every login / logout / failed-auth event is recorded.
- Audit failures NEVER crash the request (NFR-007).
- The log is durable enough for later modules to consume (typed).
"""

from __future__ import annotations

from app.auth.audit import (
    AuthAuditLogger,
    AuthEvent,
    AuthEventType,
    InMemoryAuditLogger,
)


def test_in_memory_logger_records_each_event():
    """Every ``log()`` call is captured in order."""
    logger = InMemoryAuditLogger()
    logger.log(
        AuthEvent(
            event_type=AuthEventType.LOGIN_SUCCESS,
            subject="u-1",
            tenant_id="t-a",
            ip="1.2.3.4",
            user_agent="ua",
            outcome="success",
        )
    )
    logger.log(
        AuthEvent(
            event_type=AuthEventType.LOGOUT,
            subject="u-1",
            tenant_id="t-a",
            ip="1.2.3.4",
            user_agent="ua",
            outcome="success",
        )
    )
    events = logger.snapshot()
    assert [e.event_type for e in events] == [
        AuthEventType.LOGIN_SUCCESS,
        AuthEventType.LOGOUT,
    ]


def test_audit_failure_does_not_propagate(monkeypatch):
    """A broken logger must NEVER break the auth path (NFR-007)."""
    logger = InMemoryAuditLogger()

    def boom(_event: AuthEvent) -> None:
        raise RuntimeError("disk full")

    monkeypatch.setattr(logger, "_append", boom)
    # No exception escapes.
    logger.log(
        AuthEvent(
            event_type=AuthEventType.LOGIN_FAILED,
            subject="u-1",
            tenant_id="t-a",
            ip="1.2.3.4",
            user_agent="ua",
            outcome="failure",
            reason="invalid_token",
        )
    )


def test_audit_event_serializes_with_stable_field_set():
    """Typed wire format — UI / dashboards downstream depend on this."""
    event = AuthEvent(
        event_type=AuthEventType.LOGIN_SUCCESS,
        subject="u-1",
        tenant_id="t-a",
        ip="1.2.3.4",
        user_agent="ua",
        outcome="success",
    )
    payload = event.to_dict()
    for key in (
        "event_type",
        "subject",
        "tenant_id",
        "ip",
        "user_agent",
        "occurred_at",
        "outcome",
    ):
        assert key in payload


def test_protocol_satisfied_by_in_memory_logger():
    """``InMemoryAuditLogger`` satisfies the protocol contract."""
    logger: AuthAuditLogger = InMemoryAuditLogger()
    # If the assignment type-checks, the protocol is satisfied.
    assert hasattr(logger, "log")


def test_event_types_are_a_closed_enum():
    """The event-type set is closed; new types are an explicit code change."""
    expected = {
        "login_success",
        "login_failed",
        "logout",
        "token_refresh",
        "role_denied",
        "tenant_denied",
        "token_invalid",
    }
    assert {t.value for t in AuthEventType} == expected
