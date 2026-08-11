"""Role-based access control — the seven roles defined in M02.

This enum is the single source of truth for roles. The set is closed;
adding a role is an explicit, documented change (not a "while I'm
here" refactor) because every RBAC test in the suite enumerates
``Role`` members.

Traceability: FR-053.
"""

from __future__ import annotations

from collections.abc import Mapping
from enum import Enum
from typing import Any


class Role(str, Enum):
    """The seven RBAC roles mandated by M02's acceptance criteria."""

    PLATFORM_ADMIN = "platform_admin"
    TENANT_ADMIN = "tenant_admin"
    ARCHITECT = "architect"
    ANALYST = "analyst"
    REVIEWER = "reviewer"
    EXECUTIVE = "executive"
    READ_ONLY = "read_only"


#: Iterating this guarantees tests stay in sync with the enum.
ALL_ROLES: tuple[Role, ...] = tuple(Role)


def role_set_from_claims(claims: Mapping[str, Any]) -> set[Role]:
    """Resolve the set of :class:`Role` values from a JWT claims payload.

    Keycloak's canonical path is ``realm_access.roles`` (a list of
    strings). Unknown strings, non-strings, and missing blocks are
    silently ignored — defence against upstream drift in the realm
    configuration.

    Args:
        claims: The raw claims payload (already JSON-decoded).

    Returns:
        The subset of known roles present in the claim.
    """
    realm_access = claims.get("realm_access")
    if not isinstance(realm_access, dict):
        return set()

    raw_roles = realm_access.get("roles", [])
    if not isinstance(raw_roles, list):
        return set()

    known = {role.value: role for role in Role}
    resolved: set[Role] = set()
    for entry in raw_roles:
        if isinstance(entry, str) and entry in known:
            resolved.add(known[entry])
    return resolved
