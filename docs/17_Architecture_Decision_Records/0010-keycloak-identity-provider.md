# ADR-0010 — Keycloak as the Identity Provider

**Status:** Accepted
**Date:** 2026-08-10
**Related:** [ADR-0008](./0008-aws-cloud-platform.md) · [13_Security_Architecture](../13_Security_Architecture.md)
**Resolves:** OD-2 (identity / SSO provider)

## Context
NFR-4 requires SSO, RBAC, and tenant isolation. Roles are fixed: `platform_admin`, `tenant_admin`, `architect`, `analyst`, `reviewer`, `executive`, `read_only`. Candidates: cloud-native IdPs (Cognito on AWS, Entra ID on Azure) and hosted/self-hosted standards-based IdPs (Keycloak, Auth0).

## Decision
Adopt **Keycloak** as the identity provider, self-hosted on the platform's EKS cluster, regardless of the cloud pick.

- OIDC for browser SSO (frontend + API); OAuth2 client-credentials + signed tokens for service-to-service auth (S2S).
- RBAC roles are modeled as realm/tenant roles mapped to the fixed role set above.
- Tenant identity is carried in tokens (`tenant_id`) and enforced at every query boundary (FR-057).
- Optional federated login to external enterprise IdPs (Entra ID / Okta / SAML) is a Keycloak identity-broker configuration, not a code change.

## Consequences
### Positive
- Cloud-agnostic: the IdP does not lock the platform to a cloud vendor (NFR-13 spirit).
- Full control over tenant realms, role mapping, and audit; free/open-source.
- Identity brokering makes future enterprise SSO integration a config change.
### Negative / Trade-offs
- Adds another stateful service to operate (Keycloak + its database) — HA, backup, and patching responsibility.
- Security-critical component; must be patched and hardened as first-class infrastructure.
- Self-hosting trades away the zero-ops of a managed IdP (Cognito/Auth0).
### Neutral
- Deployed via its official Helm chart (consistent with ADR-0008).
- Session policies, MFA, and password policy configured per tenant realm at Phase 2/10.
