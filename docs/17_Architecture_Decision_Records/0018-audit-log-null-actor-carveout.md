# ADR-0018 — `audit_log` NULL-actor carve-out for `saie_app`

- **Status:** Accepted
- **Date:** 2026-08-13
- **Supersedes:** —
- **Amends:** [ADR-0014](./0014-cost-minimized-open-source-stack.md) (RLS posture), [`docs/28 §4`](../28_M03a_Design.md) and [`docs/28 §6 Q1`](../28_M03a_Design.md)

## Context

M03a ships RLS policies on every tenant-scoped table. The `saie_app`
role is the *default-deny* posture: a query whose `SET LOCAL
app.tenant_id` is unset or does not match the row's `tenant_id`
column sees zero rows; an INSERT/UPDATE/DELETE outside the tenant
context is rejected by `WITH CHECK`. This is the load-bearing
security surface for FR-057 and NFR-004.

`audit_log` is a tenant-scoped table, but its write pattern is
different from every other table in the schema. The two real writers
are:

1. The **request path** (M02 `AuthAuditLogger`, every M04+ endpoint):
   an authenticated user with a tenant claim → the audit row carries
   a non-NULL `actor_id` referencing `users.id` and the row's
   effective `tenant_id` matches the request's tenant. Default-deny
   applies normally.
2. **System-generated events**: job runs without an authenticated
   user (scheduled crawls, evidence-extraction pipelines, Saturday
   report composition, the Brevo email transport). The event is
   emitted on behalf of the platform, not a user; `actor_id` is
   NULL.

If the `saie_app` policy on `audit_log` were written with the same
boolean expression as every other tenant-scoped table — strictly
`app_tenant_matches(<tenant_col>)` — case (2) would be rejected,
because `NULL = anything` is NULL, and `WITH CHECK` evaluates NULL
as false. **Every system-generated audit row would fail to insert.**

This is a real carve-out from the strict `saie_app` "no INSERT
outside a tenant context" posture. `saie_platform_admin` already has
a permissive `(true)` policy per §6 Q1 Option 1 (audit at the
application layer is M15's job). The question is what `saie_app`
should do.

The audit (`docs/29 §3.3`) flagged this as a load-bearing decision
for M15 (Governance); without a trace, future maintainers will not
understand why `audit_log` is partially permissive on `saie_app`.

## Decision

The `saie_app` policy on `audit_log` is **partially permissive for
NULL-actor rows only**. The implementation is the
`(actor_id IS NULL OR EXISTS(...))` formulation already shipped in
`0001_initial_schema.py`:

- **When `actor_id IS NOT NULL`** the row behaves exactly like
  every other tenant-scoped table: `EXISTS (SELECT 1 FROM users u
  WHERE u.id = audit_log.actor_id AND app_tenant_matches(u.tenant_id))`
  must hold. This binds the audit row to a real user in the request's
  tenant — the FR-054 evidence trail.
- **When `actor_id IS NULL`** the row bypasses the tenant-EXISTS
  check (the `OR actor_id IS NULL` short-circuits). It still
  requires `app.tenant_id` to be set (otherwise the row is not
  attributable to *any* tenant, which is rejected by the rest of the
  policy chain). System-generated events therefore insert under a
  real tenant context with NULL `actor_id`, and the policy passes.

`saie_platform_admin` continues to use the permissive `(true)` Q1
Option 1 policy unchanged.

The carve-out is **scoped**, not blanket:

- It applies **only** to `audit_log`.
- It applies **only** to the `saie_app` role.
- It permits INSERT for NULL-actor rows when `app.tenant_id` is set;
  it does **not** permit INSERT for rows that omit the tenant
  context entirely.
- READ access is unaffected: `saie_app` still sees only audit rows
  whose `actor_id`'s user belongs to the active tenant.

## Consequences

### Positive

- **System events are auditable.** Scheduled crawls, evidence
  extraction, Saturday report composition, Brevo notifications all
  land in `audit_log` with a NULL `actor_id` and a real `tenant_id`.
  M15's application-layer auditor can distinguish "user did X"
  (`actor_id` present) from "the platform did X on behalf of
  tenant Y" (`actor_id` NULL).
- **Default-deny posture is preserved elsewhere.** Every other
  tenant-scoped table keeps the strict `saie_app` policy. The
  carve-out is one boolean expression in one policy, not a global
  weakening.
- **Audit trail is complete.** The alternative — dropping
  system-event audit rows — would create a coverage gap exactly in
  the actions (cron, pipeline) that the M15 reviewer needs to see
  most.

### Negative / Trade-offs

- **`saie_app` is no longer uniformly strict on `audit_log`.** A
  future maintainer reading the policies must understand the carve-
  out. This ADR exists to make that reasoning durable; the
  `docs/28 §15` cross-link makes it discoverable from the design
  doc as well.
- **NULL `actor_id` is a semantic overload.** It now means both
  "system-generated event for this tenant" *and* "actor deleted
  after audit row was written" (if M04 ever deletes users). M15
  should resolve the overload by adding a `source` discriminator
  column (`'user' | 'system' | 'import'`) when the application-
  layer auditor lands. This ADR does not preempt that work.
- **Forensic query gotcha.** "All actions by user X" must
  `JOIN` `audit_log.actor_id = users.id` and the query must also
  surface rows where `actor_id IS NULL AND tenant_id = :tenant`
  separately. Future UI/reporting surfaces need to handle the
  distinction. M12's `report_items` rendering will need a
  "platform action" card variant.

### Neutral

- **No code change today.** The carve-out is already implemented in
  the merged migration; this ADR only documents the rationale.
- **`saie_migrator` unaffected.** It has `BYPASSRLS`; the policy
  never evaluates for it.
- **Cross-tenant `saie_platform_admin` reads unaffected.** The
  permissive `(true)` policy on `saie_platform_admin` is unchanged.

## Alternatives considered

- **Reject all NULL-actor INSERTs on `saie_app`.** This is the
  default-deny-everywhere posture. Rejected: system-generated events
  become unauditable. Coverage gap is unacceptable for NFR-001
  (auditability) and would force every cron job to spawn an
  `actor_id = NULL` workaround somewhere else.
- **Use a separate `system_audit_log` table** with no RLS. Rejected:
  splits the audit story across two schemas; M15's auditor must
  UNION them; tooling (reports, reviews, exports) doubles in surface
  area. The two-table cost outweighs the carve-out's risk.
- **Grant `BYPASSRLS` to `saie_app` for `audit_log` only.** Postgres
  does not support per-table `BYPASSRLS`; it is a role attribute.
  This alternative is not implementable.
- **Insert system events as `saie_platform_admin`.** Rejected: the
  app-layer writers run as `saie_app` (the default); switching
  connection roles per-call adds round-trips and complicates
  connection pooling. The carve-out is the simplest surface that
  keeps `saie_app` as the writer.

## Operational notes

- **Discoverability.** This ADR is linked from `docs/28 §6 Q1` and
  `docs/28 §15 item 1` so a maintainer reading the design doc sees
  the rationale without needing to grep ADRs.
- **Future M15 work.** The application-layer auditor should add a
  `source` discriminator column to `audit_log` (see Negative
  §"NULL `actor_id` is a semantic overload") and update this ADR
  with an addendum when it lands.
- **Test coverage.** The RLS matrix test (`test_rls_matrix.py`)
  already exercises the NULL-actor carve-out: it inserts an audit
  row with `actor_id = NULL` from `saie_app + tenant_a` and asserts
  success; cross-tenant NULL-actor inserts are rejected. No test
  change is required.

## Traceability

- **FR-054** Audit logs + prompt/model versioning + evidence traceability
- **FR-057** Tenant isolation at every query boundary + least privilege enforcement
- **NFR-001** Auditability — every report finding traceable to evidence
- **NFR-004** Security — SSO, RBAC, tenant isolation, encrypted secrets