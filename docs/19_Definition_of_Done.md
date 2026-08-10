# 19 — Definition of Done

**Product:** SAP Automation Intelligence Engine (SAIE)
**Document status:** Living — versioned; changes require team agreement.
**Related docs:** [16_Requirement_Traceability_Matrix](./16_Requirement_Traceability_Matrix.md) · [15_Project_Roadmap](./15_Project_Roadmap.md) · [14_Testing_Strategy](./14_Testing_Strategy.md)

---

## 1. Purpose

DoD is the shared contract for "when is work actually finished." It applies to **phases, features, and bug fixes**. Nothing is *done* until every applicable check below passes — no exceptions without an explicit, audited waiver.

## 2. Universal Definition of Done (all work)

### 2.1 Requirements
- [ ] Work traces to one or more unique Requirement IDs in the [RTM](./16_Requirement_Traceability_Matrix.md), e.g. `FR-010`, `NFR-004` (no untraceable work).
- [ ] Every commit and PR title/body references the relevant Requirement ID(s).
- [ ] Tests introduced or changed by the work reference the Requirement ID(s) they verify.
- [ ] If the work introduces behavior with no existing Requirement ID, the RTM is updated first with a new stable ID.
- [ ] Acceptance criteria for the linked requirement(s) are met.
- [ ] Out-of-scope boundaries from the PRD were not crossed.

### 2.2 Code & Quality
- [ ] Code reviewed; review comments resolved.
- [ ] Lint + typecheck pass (TS strict, Python type-checked).
- [ ] Unit tests pass for new/changed logic.
- [ ] Contract tests pass at changed service boundaries.
- [ ] No new high-severity findings from security scan (SAST/dependency).
- [ ] No secrets, credentials, or internal addresses committed.
- [ ] `docs/18_Project_Memory.md` and any affected ADRs updated.

### 2.3 Non-Functional
- [ ] Relevant NFRs satisfied (traceable via RTM) — auditability, reliability, security, observability, etc.
- [ ] Tenant isolation verified where data access changed.
- [ ] Idempotency verified where a job/endpoint changed.
- [ ] Observability (metrics/logs/traces) covers the new path.

### 2.4 Documentation
- [ ] Docs updated for any behavior/API/schema/UI change (API contract, schema, UI patterns).
- [ ] No orphaned or stale docs left behind.

## 3. Feature-Level DoD (adds to §2)

- [ ] E2E journey passes for at least one primary journey touching the feature (Discover / Evaluate / Report).
- [ ] UI changes pass accessibility checks (keyboard, contrast, no color-only meaning).
- [ ] LLM-dependent behavior passes the golden-set eval gate for its capability.
- [ ] Scoring/confidence rationale present wherever scores or confidence are surfaced.

## 4. Phase-Level DoD (adds to §2 + §3)

- [ ] All phase done-criteria in [15_Project_Roadmap](./15_Project_Roadmap.md) are met and evidence captured.
- [ ] Evaluation quality gates clear (precision ≥ 85%, relevance ≥ 80%, dedup ≥ 90%, architecture usefulness ≥ 80%) where the phase touches those capabilities.
- [ ] Phase artifacts (data, config, runbooks) committed and documented.
- [ ] Deployment to the target environment verified.

## 5. Bug-Fix DoD (adds to §2)

- [ ] Regression test added that reproduces the bug and passes with the fix.
- [ ] The fix does not regress golden-set metrics where the bug touched an AI stage.
- [ ] Root cause documented in the fix/commit.

## 6. DoD for AI/LLM Work (specific additions)

- [ ] Every claim surfaced carries an evidence reference or an explicit **inferred/speculative** label.
- [ ] Output validated against its structured-output schema; failures route to retry/review, never silent acceptance.
- [ ] Prompt + model versions recorded on the run; changed prompts triggered a golden-set regression.
- [ ] Low-confidence outputs not auto-promoted; high-impact items routed to Review Queue.
- [ ] Prompt-injection safety verified for ingested content (content-as-data).

## 7. Definition of Not Done

Work is **not done** when any of these hold:
- Tests are failing or skipped without justification.
- A requirement is partially implemented with no RTM row for the remainder.
- Incomplete report could be published (report atomicity violated).
- Cross-tenant access is not provably denied for a changed path.
- Docs/ADRs contradict the shipped behavior.

## 8. Waivers

- Waivers to DoD are rare, explicit, audited (recorded in `audit_log`), time-boxed, and require the accountable owner's approval.
- Every waived item becomes a tracked follow-up task.

## 9. DoD for Documentation Itself

This very document set (Phase 1) is done because:
- [ ] All 19 deliverables exist and are internally consistent (IDs, phases, metric thresholds match across docs).
- [ ] Every requirement traces to a capability, phase, and verification type (RTM).
- [ ] ADRs record the key decisions; Project Memory captures non-obvious context.
