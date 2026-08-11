"""RED test — Role enum and RBAC policy (FR-053, NFR-004).

Pins the canonical 7-role set documented in docs/18 §5 and the M02
acceptance criteria. Any drift here must be a deliberate, documented
change — silently renaming a role is a security incident.
"""

from __future__ import annotations

from typing import Any

import pytest

from app.auth.roles import ALL_ROLES, Role, role_set_from_claims


def test_canonical_seven_roles_match_documented_set() -> None:
    """The seven roles in M02's spec are present and frozen."""
    expected = {
        "platform_admin",
        "tenant_admin",
        "architect",
        "analyst",
        "reviewer",
        "executive",
        "read_only",
    }
    assert {r.value for r in Role} == expected
    assert set(r.value for r in ALL_ROLES) == expected


def test_role_values_are_lowercase_strings() -> None:
    """Roles are case-sensitive; ``Analyst`` is NOT the same as ``analyst``.

    Pinning this prevents a class of bug where an upstream Keycloak
    realm maps ``Analyst`` to a string that fails equality.
    """
    for role in Role:
        assert role.value == role.value.lower()
        assert " " not in role.value


def test_role_set_from_claims_extracts_realm_roles() -> None:
    """``realm_access.roles`` is the canonical source for roles (Keycloak)."""
    claims: dict[str, Any] = {"realm_access": {"roles": ["analyst", "reviewer", "no-such-role"]}}
    resolved = role_set_from_claims(claims)
    assert resolved == {Role.ANALYST, Role.REVIEWER}


def test_role_set_from_claims_tolerates_missing_realm_access() -> None:
    """An empty / malformed claim block yields an empty role set, not a crash."""
    assert role_set_from_claims({}) == set()
    assert role_set_from_claims({"realm_access": {}}) == set()
    assert role_set_from_claims({"realm_access": {"roles": []}}) == set()


def test_role_set_from_claims_rejects_garbage() -> None:
    """Non-string roles are ignored (defensive against upstream drift)."""
    claims: dict[str, Any] = {"realm_access": {"roles": ["analyst", None, 42, ""]}}
    resolved = role_set_from_claims(claims)
    assert resolved == {Role.ANALYST}


@pytest.mark.parametrize("role", list(Role))
def test_each_role_round_trips_through_claims(role: Role) -> None:
    """Every role survives the claim round-trip — required by the matrix test."""
    claims: dict[str, Any] = {"realm_access": {"roles": [role.value]}}
    assert role in role_set_from_claims(claims)
