# 13 — Security Architecture

**Product:** SAP Automation Intelligence Engine (SAIE)
**Document status:** Baseline
**Related docs:** [07_Database_Design](./07_Database_Design.md) · [08_API_Design](./08_API_Design.md) · [03_NonFunctional_Requirements](./03_NonFunctional_Requirements.md)

---

## 1. Security Objectives

- **SSO** via OIDC/SAML-capable identity provider.
- **Least privilege** across roles, services, and data paths.
- **Tenant isolation** at every query boundary.
- **Full auditability** of governed actions.
- **Secrets** encrypted and stored outside application data.
- **Source/legal compliance** (robots.txt, terms, rate limits, retention) as a security boundary.

## 2. Identity & Access

- IdP: OIDC/SAML; sessions via IdP-issued tokens; RBAC claims.
- Roles: `platform_admin`, `tenant_admin`, `architect`, `analyst`, `reviewer`, `executive`, `read_only`.
- Enforcement: **server-side** at the API (never trust the client); route guards in the UI are UX only.
- Service-to-service: mTLS or short-lived workload tokens; no shared static secrets.

## 3. Tenant Isolation

- Every data access path scoped by `tenant_id` derived from the authenticated principal.
- Defense in depth: application-layer scoping **and** Postgres row-level security as backstop.
- Cross-tenant access attempt → denied + audited (tested in [14_Testing_Strategy](./14_Testing_Strategy.md)).
- Object storage/queue/search keys include tenant; tenant boundaries tested end-to-end.

## 4. Data Protection

| Data class | Controls |
|---|---|
| Secrets / credentials | Encrypted in secret manager; never in DB/logs/images |
| Source content snapshots | Retention + licensing policy; versioned blobs |
| LLM prompts & outputs | Not used for training (contractual); prompts versioned; tenant isolated |
| Evidence & provenance | Immutable append; audit-protected |
| Reports | Access-scoped by tenant + RBAC; export audit logged |

## 5. Audit

- Governed actions audited: admin, review decisions, score overrides, source/schedule changes, model/prompt/taxonomy changes, exports.
- `audit_log` records actor, action, entity, timestamp, details; immutable append with access control ([FR-C09-3]).
- Audit trail supports the traceability guarantee ([NFR-1]).

## 6. Application Security

- Input validation at every boundary (Pydantic schemas, strict types).
- NoSQL/SQL injection defenses: parameterized queries, ORM bindings.
- SSRF controls on the **crawl path** — outbound requests restricted to allow-listed source domains; no internal-address access; DNS pinning where supported ([FR-C01-7]).
- Rate limiting on public endpoints; abuse controls on search.
- Supply chain: locked deps, SBOM, scanner in CI ([12_DevOps_Architecture](./12_DevOps_Architecture.md)).

## 7. Legal & Source-Compliance Security

- Crawler policy module enforces robots.txt, terms, auth boundaries, rate limits ([FR-C01-7]).
- Paywalled/authenticated content is never bypassed; flagged sources quarantined on policy breach.
- Content retention follows licensing; deletion honored.

## 8. Secrets & Configuration

- Secret manager (KMS-backed) for all credentials; rotation policy.
- Runtime config via environment/secret injection; no secrets in source control.
- `.env`/config templates committed with placeholders only.

## 9. Security Testing

- SAST + dependency scanning in CI; DAST on staging; threat-model review before Phase 14.
- Dedicated adversarial tests: tenant bypass, RBAC escalation, SSRF, prompt-injection on ingestion content.
- Prompt-injection defense: treat ingested source content as **data**, never as instructions; extraction contracts separate data from control.

## 10. Incident Response

- Alerting on security-relevant events (audit anomalies, isolation violations, policy breaches).
- Runbooks for: suspected tenant breach, secret rotation, crawler policy breach, supply-chain finding.
