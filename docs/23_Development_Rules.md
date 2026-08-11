# 23 — Development Rules (Phase 7)

**Product:** SAP Automation Intelligence Engine (SAIE)
**Document status:** Living — versioned; changes require team agreement.
**Related docs:** [16_Requirement_Traceability_Matrix](./16_Requirement_Traceability_Matrix.md) · [19_Definition_of_Done](./19_Definition_of_Done.md) · [15_Project_Roadmap](./15_Project_Roadmap.md) · [22_Module_Roadmap](./22_Module_Roadmap.md) · [04_System_Architecture](./04_System_Architecture.md) · [21_AI_Layer_Specification](./21_AI_Layer_Specification.md) · [14_Testing_Strategy](./14_Testing_Strategy.md)

---

## 1. Purpose

This document codifies the **mandatory development workflow** for every module, feature, and bug fix in SAIE. It operationalizes the governance gate from [CLAUDE.md](../CLAUDE.md) and the traceability rules from the RTM. No code is written until the pre-coding checks pass; no feature is complete until the post-coding checks pass.

---

## 2. Pre-Coding Gate (Mandatory — Zero Tolerance)

**Before any implementation source file is created or modified, all four checks must pass.** If any check fails, the work stops until it is resolved. No exceptions.

### 2.1 Confirm Relevant Requirements

| Check | Mechanism | Evidence |
|-------|-----------|----------|
| The work scope maps to one or more **stable Requirement IDs** (`FR-NNN` or `NFR-NNN`) in [16_Requirement_Traceability_Matrix](./16_Requirement_Traceability_Matrix.md) | RTM lookup | List the Requirement ID(s) in the PR/issue description |
| Every Requirement ID is **active** (status ≠ `Deferred`) | RTM status column | Quote the RTM row |
| Acceptance criteria from the RTM (and [02_Functional_Requirements](./02_Functional_Requirements.md) / [03_NonFunctional_Requirements](./03_NonFunctional_Requirements.md)) are understood and achievable | Read the source doc | Acceptance criteria listed in the implementation plan |
| If new behavior has **no existing Requirement ID**, a new stable ID is added to the RTM **before** coding | Edit RTM + CSV | RTM commit hash referenced |

> **Rule:** No untraceable work. Every commit, PR, and test must reference at least one Requirement ID.

### 2.2 Confirm Dependencies

| Check | Mechanism | Evidence |
|-------|-----------|----------|
| All **upstream modules** (per [22_Module_Roadmap](./22_Module_Roadmap.md) §3 dependency graph) are **completed and merged** | Module Roadmap + Git status | List dependency module IDs (MXX) and their merge commits |
| All **infrastructure dependencies** (DB schema, vector collections, graph schema, storage buckets, queue topics) exist in the target environment | [07_Database_Design](./07_Database_Design.md) + `infra/` state | `alembic current`, Qdrant collections list, Neo4j schema, MinIO buckets |
| All **contract dependencies** (API contracts, event schemas, agent contracts) are published and versioned | [08_API_Design](./08_API_Design.md) + [21_AI_Layer_Specification](./21_AI_Layer_Specification.md) | Contract versions pinned in the implementation plan |
| All **tooling dependencies** (Python/TS versions, linters, type checkers, test runners) are available in CI | CI config + lockfiles | CI passes on a clean checkout |

> **Rule:** Build in dependency order (Waves 1→5 per [22_Module_Roadmap](./22_Module_Roadmap.md) §3). Never start a module whose dependencies are not green.

### 2.3 Review Architecture

| Check | Mechanism | Evidence |
|-------|-----------|----------|
| The implementation approach aligns with [04_System_Architecture](./04_System_Architecture.md) (container view, data flow, tech stack) | Architecture doc review | Written architecture decision note in the PR description |
| The approach aligns with [21_AI_Layer_Specification](./21_AI_Layer_Specification.md) for any agent/LLM work (typed contracts, artifact persistence, evidence labeling, retry policy, evaluation criteria) | AI Layer spec review | Agent/contract names from the spec referenced |
| The approach respects **locked stack decisions** from [ADR-0014](./17_Architecture_Decision_Records/0014-cost-minimized-open-source-stack.md) and superseded/amended ADRs | ADR check | No prohibited technology introduced (e.g., no Temporal, no Bedrock, no pgvector for embeddings) |
| Cross-cutting concerns are addressed: **tenant isolation**, **idempotency**, **observability**, **deterministic preprocessing before LLM calls**, **model-agnostic LLM gateway** | Checklist in PR | Each concern explicitly addressed or marked N/A with justification |

> **Rule:** If the architecture review surfaces a conflict, a new ADR is required before coding proceeds.

### 2.4 Identify Impacted Modules

| Check | Mechanism | Evidence |
|-------|-----------|----------|
| All **modules touched** by the change are listed (from [22_Module_Roadmap](./22_Module_Roadmap.md) M01–M16) | Module Roadmap + code search | List of MXX IDs |
| For each impacted module: **Scope**, **Dependencies**, **Acceptance Criteria**, **Tests**, **DoD** from [22_Module_Roadmap](./22_Module_Roadmap.md) §5 are re-verified against the proposed change | Module spec review | Checklist per module in the PR description |
| **Blast radius** is assessed: downstream modules, shared contracts, shared data models, shared infrastructure | `query_graph` (callers/callees/imports) or manual trace | Impact radius summary in PR |

> **Rule:** A change that spans >3 modules requires a dedicated architecture review (adversarial) before coding.

---

## 3. Post-Coding Gate (Mandatory — Zero Tolerance)

**After implementation is complete, all checks must pass before the PR is merged.** Failing checks block merge.

### 3.1 Run Tests

| Check | Mechanism | Evidence |
|-------|-----------|----------|
| **Unit tests** pass for all new/changed logic | `pytest` / `vitest` | CI test report |
| **Contract tests** pass at every changed service boundary | Pact / OpenAPI contract tests | CI contract test report |
| **Integration tests** pass for cross-module flows | `pytest -m integration` / Playwright | CI integration test report |
| **Golden-set evaluation gates** clear for any AI/LLM capability touched | [14_Testing_Strategy](./14_Testing_Strategy.md) | Precision ≥ 85%, Relevance ≥ 80%, Dedup ≥ 90%, Architecture usefulness ≥ 80% |
| **E2E journey** passes for at least one primary journey (Discover / Evaluate / Report) | Playwright / Cypress | CI E2E report |
| **Security scans** (SAST, dependency, secrets) produce no new high-severity findings | GitHub Actions / Trivy / Gitleaks | CI security report |
| **Type checking** passes (TS strict, Python mypy) | `tsc --noEmit`, `mypy` | CI typecheck report |
| **Linting** passes (ESLint, Ruff) | `eslint`, `ruff` | CI lint report |

> **Rule:** No test is skipped without a documented, time-boxed waiver recorded in the audit log.

### 3.2 Update Documentation

| Check | Mechanism | Evidence |
|-------|-----------|----------|
| **API contracts** updated for any changed endpoint/schema/event | [08_API_Design](./08_API_Design.md) + OpenAPI files | Diff of contract files in PR |
| **Database schema** docs updated for any migration | [07_Database_Design](./07_Database_Design.md) + Alembic migrations | Migration files + doc diff |
| **Architecture docs** updated if container view, data flow, or tech stack changed | [04_System_Architecture](./04_System_Architecture.md) + ADRs | Doc diff or new ADR |
| **AI Layer spec** updated if agent contracts, prompts, tools, or evaluation criteria changed | [21_AI_Layer_Specification](./21_AI_Layer_Specification.md) | Doc diff |
| **Module Roadmap** updated if module scope/acceptance/tests/DoD changed | [22_Module_Roadmap](./22_Module_Roadmap.md) | Doc diff |
| **UI/UX docs** updated for any user-facing change | [09_UI_UX_Design](./09_UI_UX_Design.md) / [11_Frontend_Architecture](./11_Frontend_Architecture.md) | Doc diff |
| **Security docs** updated for any auth/tenant/isolation/secrets change | [13_Security_Architecture](./13_Security_Architecture.md) | Doc diff |
| **No orphaned/stale docs** — every doc change has a corresponding code change or is explicitly a doc-only improvement | Doc search | Grep for references |

> **Rule:** Docs are updated **in the same PR** as the code change. No follow-up doc tickets.

### 3.3 Update Traceability Matrix

| Check | Mechanism | Evidence |
|-------|-----------|----------|
| **RTM status** updated to `In Progress` → `Done` for each Requirement ID the work completes | Edit `docs/16_Requirement_Traceability_Matrix.md` + `docs/requirements_traceability_matrix.csv` | RTM diff in PR |
| **New Requirement IDs** added (if any) with stable IDs, never reused | Edit RTM + CSV | RTM diff |
| **Tests reference** the Requirement ID(s) they verify (in test names, docstrings, or metadata) | Test code review | Grep for `FR-` / `NFR-` in test files |
| **Commit messages** and **PR title/body** reference the Requirement ID(s) | Git history | `git log --oneline` shows IDs |

> **Rule:** The RTM is the source of truth for traceability. It is updated atomically with the work it traces.

### 3.4 Update Project Memory

| Check | Mechanism | Evidence |
|-------|-----------|----------|
| **`docs/18_Project_Memory.md`** updated with: new decisions, gotchas, conventions, non-obvious context from this work | Edit project memory | Project Memory diff in PR |
| **ADRs** created for any new architectural decision (superseding none, amending if needed) | New file in `docs/17_Architecture_Decision_Records/` + README update | ADR file + README diff |
| **Module status** in [22_Module_Roadmap](./22_Module_Roadmap.md) updated if a module reaches `Done` | Module Roadmap edit | Doc diff |
| **Phase status** in [15_Project_Roadmap](./15_Project_Roadmap.md) and [18_Project_Memory](./18_Project_Memory.md) updated if a phase completes | Roadmap + Memory edit | Doc diff |

> **Rule:** Project Memory is the onboarding document for future contributors. If you learned something non-obvious, write it down.

---

## 4. Feature Completion Definition

A feature is **complete** if and only if **all** of the following are true:

1. ✅ **Pre-coding gate** (Section 2) passed and documented in the PR
2. ✅ **Implementation** merged to `main`
3. ✅ **Post-coding gate** (Section 3) passed — all tests green, docs updated, RTM updated, Project Memory updated
4. ✅ **DoD satisfied** — Universal [§2](./19_Definition_of_Done.md#2-universal-definition-of-done-all-work) + Feature [§3](./19_Definition_of_Done.md#3-feature-level-dod-adds-to-2) + AI [§6](./19_Definition_of_Done.md#6-dod-for-ai-llm-work-specific-additions) where applicable
5. ✅ **No open waivers** — any waiver has an expiry date and a follow-up task

---

## 5. Module Completion Definition

A module (M01–M16 per [22_Module_Roadmap](./22_Module_Roadmap.md)) is **complete** if and only if:

1. ✅ All **features** in the module's scope are complete (per Section 4)
2. ✅ **Module Exit Gate** ([22_Module_Roadmap](./22_Module_Roadmap.md) §6) checklist passes:
   - All acceptance criteria met
   - All tests pass (unit, contract, integration, eval, E2E)
   - Golden-set gates clear where applicable
   - Docs updated (API, DB, Architecture, AI Layer, Module Roadmap, UI/UX, Security)
   - RTM updated for all traced requirements
   - Project Memory updated
   - No high-severity security findings
   - Deployed to target environment and verified
3. ✅ **Phase done criteria** ([15_Project_Roadmap](./15_Project_Roadmap.md)) for the module's phase are met
4. ✅ **Phase DoD** ([19_Definition_of_Done](./19_Definition_of_Done.md) §4) passes

---

## 6. Emergency Bypass (Extremely Rare)

| Condition | Process |
|-----------|---------|
| Production incident requiring hotfix | 1. Create incident issue with `hotfix` label<br>2. Minimal fix with regression test<br>3. Post-incident: full pre/post gates within 48h<br>4. Waiver recorded in audit log with expiry |
| Security patch (CVE) | Same as hotfix; security scan gate cannot be waived |

> **Rule:** Bypasses are **never** used for feature work, tech debt, or schedule pressure. Every bypass creates a tracked follow-up task.

---

## 7. Checklist Templates

### 7.1 Pre-Coding Checklist (paste into PR description)

```markdown
## Pre-Coding Gate

### 2.1 Requirements
- [ ] Requirement ID(s): FR-XXX, NFR-YYY
- [ ] RTM status active
- [ ] Acceptance criteria understood
- [ ] New ID added to RTM (if needed): FR-NEW / NFR-NEW

### 2.2 Dependencies
- [ ] Upstream modules done: MXX (commit: abc123)
- [ ] Infra dependencies exist: DB migration applied, Qdrant collection created, etc.
- [ ] Contract versions pinned: API vX.Y, Event vA.B, Agent contract vC.D
- [ ] Tooling available in CI

### 2.3 Architecture
- [ ] Aligns with System Architecture (container view, data flow, stack)
- [ ] Aligns with AI Layer Spec (if agent/LLM work)
- [ ] Respects locked stack (ADR-0014 + superseded/amended ADRs)
- [ ] Cross-cutting concerns: tenant isolation / idempotency / observability / deterministic-first / model-agnostic gateway

### 2.4 Impacted Modules
- [ ] Modules touched: MXX, MYY
- [ ] Module specs re-verified
- [ ] Blast radius assessed
```

### 7.2 Post-Coding Checklist (paste into PR description)

```markdown
## Post-Coding Gate

### 3.1 Tests
- [ ] Unit tests pass
- [ ] Contract tests pass
- [ ] Integration tests pass
- [ ] Golden-set eval gates clear (if AI work)
- [ ] E2E journey passes
- [ ] Security scans clean
- [ ] Type checking passes
- [ ] Linting passes

### 3.2 Documentation
- [ ] API contracts updated
- [ ] Database schema docs updated
- [ ] Architecture docs updated (or new ADR)
- [ ] AI Layer spec updated (if AI work)
- [ ] Module Roadmap updated
- [ ] UI/UX docs updated
- [ ] Security docs updated
- [ ] No orphaned docs

### 3.3 Traceability
- [ ] RTM status updated to Done
- [ ] New IDs added to RTM + CSV
- [ ] Tests reference Requirement IDs
- [ ] Commits/PR reference Requirement IDs

### 3.4 Project Memory
- [ ] Project Memory updated
- [ ] ADRs created/updated
- [ ] Module status updated
- [ ] Phase status updated
```

---

## 8. Enforcement

- **CI/CD pipelines** enforce: lint, typecheck, unit, contract, integration, security scans, golden-set eval (where configured).
- **PR merge protection** requires: all checks green, code review approval, DoD checklist completed in PR description.
- **Architecture review** (adversarial) required for: cross-module changes >3 modules, new ADRs, stack deviations.
- **Governance agent** (M15) audits RTM completeness and DoD compliance on a schedule.

---

## 9. Requirements Traceability

| Requirement ID | Title | This Doc Section |
|----------------|-------|------------------|
| NFR-001 | Auditability | §2.1, §3.3, §8 |
| NFR-004 | Security (tenant isolation, RBAC) | §2.3, §3.2 |
| NFR-005 | Observability | §2.3, §3.1 |
| NFR-006 | Maintainability (typed contracts, versioned prompts) | §2.3, §3.2 |
| NFR-007 | Recoverability (idempotent, replayable) | §2.3 |
| NFR-012 | Cost control (deterministic gating) | §2.3 |
| NFR-013 | Model lock-in resistance (model-agnostic gateway) | §2.3 |
| NFR-014 | Quality gates (golden-set eval) | §3.1 |
| FR-055 | Source health, agent health, retries, DLQ, cost budgets monitoring | §2.2, §5 |
| FR-056 | Human review routing (low-confidence + high-impact → Review Queue) | §2.3, §3.1, §8 |

---

## 10. Version History

| Version | Date | Author | Change |
|---------|------|--------|--------|
| 1.0 | 2026-08-10 | Ganesh | Initial creation — Phase 7 governance deliverable |