# 25 — Issue Standards

**Product:** SAP Automation Intelligence Engine (SAIE)
**Document status:** Canonical — single source of truth for issue/epic structure on this project. All issues (bugs, features, epics) MUST follow this standard. The `issue-maintainer` agent is bound by this doc; do not duplicate its procedure here.
**Related docs:** [16_Requirement_Traceability_Matrix](./16_Requirement_Traceability_Matrix.md) · [22_Module_Roadmap](./22_Module_Roadmap.md) · [23_Development_Rules](./23_Development_Rules.md) · [19_Definition_of_Done](./19_Definition_of_Done.md) · [`../.claude/agents/issue-maintainer.md`](../.claude/agents/issue-maintainer.md)

---

## 1. Purpose

Issues are the *living task ledger* for SAIE — they are the unit that the `issue-maintainer` agent operates, the `architect` reads, the builder fulfills, the `qa-engineer` audits, and the conductor tracks to merge. Hygiene drifts to ad-hoc fast: three spellings of "high priority", missing reproduction steps, no area classification, epics tracked as loose markdown checkboxes with no progress bar. This doc makes the shape uniform **by construction**. The `.claude/agents/issue-maintainer.md` agent is bound by this standard and operates the tracker (GitHub Issues) on its terms.

## 2. Host & Tooling

- **Tracker:** GitHub Issues on `ClaudiousAI/AutomataIQ`.
- **CLI:** `gh` (authenticated, `gh auth status` green) — the canonical path. The `issue-maintainer` agent may use the GitHub REST/GraphQL API directly with `$GITHUB_TOKEN` only as a fallback when `gh` is unavailable; the API path is **not** a separate contract — labels, bodies, and structure are identical.
- **Source of truth for module sequence:** [`22_Module_Roadmap`](./22_Module_Roadmap.md). Every module becomes an epic; every vertical slice inside it becomes a sub-issue. RTM IDs are the link between this doc and the implementation.

## 3. Label Taxonomy (canonical)

Exactly one of each kind per issue, except `area:` (smallest correct set, never more than three). **Do not invent labels outside this taxonomy.** If a legacy label is encountered, map it to canonical via the alias table in §3.4.

### 3.1 `type:` — exactly one

| Label | Use for |
|---|---|
| `type: bug` | A defect, broken behavior, or a test that was green and is now red. Must carry Steps-to-Reproduce + Expected + Actual/Observed. |
| `type: feat` | A new feature, vertical slice, or module sub-issue. Must carry Acceptance Criteria + Definition of Done. |
| `type: epic` | A multi-PR initiative (typically one M-NN module from `22_Module_Roadmap`). Carries the epic-level body template; sub-issues are linked natively. |
| `type: chore` | Tooling, CI, dependency updates, or refactors with no behavior change. No new requirement, no ACs beyond "the chore is done." |
| `type: docs` | Documentation-only change. No code, no tests. |

### 3.2 `priority:` — at most one

| Label | Use for |
|---|---|
| `priority: critical` | Blocks release, production broken, or a security finding. Fix-now. |
| `priority: high` | Blocks the current module's exit gate (per `22_Module_Roadmap §6`) or a hard dependency for in-flight work. |
| `priority: medium` | Should land in the current module if capacity allows, but not a blocker. |
| `priority: low` | Nice-to-have, future work, or a polish item. |

### 3.3 `area:` — smallest correct set (max 3)

Derived from path inspection (see §4). Canonical areas:

| Label | Touches |
|---|---|
| `area: backend` | `backend/app/`, `backend/alembic/`, `backend/tests/`, `backend/notifications/`, `backend/pyproject.toml` |
| `area: web` | `web/`, `web/src/`, `web/package.json`, Vite/React assets |
| `area: infra` | `infra/`, `docker-compose*.yml`, `Dockerfile*`, Nginx config, GitHub Actions (`.github/workflows/`) |
| `area: ai` | LLM gateway, agent framework, prompt/model registry, anything under `docs/21` scope |
| `area: docs` | `docs/`, `*.md` at the repo root, ADRs |
| `area: data` | Postgres schema/migrations, RLS, Qdrant, Neo4j, MinIO, Redis, seed runners |
| `area: tests` | `e2e/`, integration test fixtures, golden sets, evals |
| `area: tooling` | `.claude/`, Makefile, CI scripts, dev-only helpers |
| `area: security` | Auth, RBAC, tenant isolation, secrets, audit, OWASP-related |

### 3.4 Status labels (orthogonal, applied as state changes)

`status: blocked` · `status: in-review` · `status: needs-info`. Drop these as state changes. **Do not** use `status: open` / `status: closed` — GitHub tracks that natively; do not duplicate.

### 3.5 Legacy → canonical alias map

When the `issue-maintainer` encounters a non-canonical label during read operations, map silently and apply the canonical form on the next write. Mappings: `enhancement` → `type: feat`; `question` → `type: docs` (and resolve in-thread, then close); `wontfix` → close with a comment; `duplicate` → close, reference the original.

## 4. Area-Classification Heuristic (path → area)

Inspect touched paths with `Grep` / `Glob` and apply the **most specific** match. When paths span multiple areas, list every applicable `area:` label — but never more than three. Examples:

| Touched path(s) | Labels |
|---|---|
| `backend/app/db/tenant.py` | `area: backend`, `area: data` |
| `infra/nginx.conf` | `area: infra` |
| `web/src/components/EvidenceBadge.jsx` | `area: web` |
| `docs/22_Module_Roadmap.md` | `area: docs` |
| `.github/workflows/ci.yml` | `area: infra`, `area: tooling` |
| `backend/app/agents/discovery.py` | `area: backend`, `area: ai` |

## 5. Title Convention

Conventional-commit-aligned form, lowercase, scoped:

- `bug(<area>): <one-line symptom>` — e.g. `bug(backend): RLS policy fails for soft-deleted rows on tenant join`
- `feat(<area>): <one-line capability>` — e.g. `feat(data): provision Redis Streams + DLQ consumer groups`
- `epic(<module>): <one-line outcome>` — e.g. `epic(M03b): storage-layer substrate (Redis/Qdrant/Neo4j/MinIO)`
- `chore(<area>): <one-line task>` — e.g. `chore(tooling): install wizard orchestrator on main`
- `docs(<area>): <one-line change>` — e.g. `docs(18): pin M03a CI gotcha`

The title is the only field visible in a long list; one line, lowercase, scoped, no trailing period. The PR title in `22_Module_Roadmap §6` uses the same form (with the conventional-commit prefix required by the PR-title CI gate); when an issue and a PR describe the same work, they share the title verbatim.

## 6. Body Templates

### 6.1 `type: bug` body

```markdown
## Summary
<one-paragraph statement of the defect>

## Environment
- Branch / SHA: <branch> @ <short SHA>
- App version / commit: <if applicable>
- OS / runtime: <if relevant>
- Linked Requirement ID(s): FR-NNN, NFR-NNN (per [16](../16_Requirement_Traceability_Matrix.md))

## Steps to Reproduce
1. <concrete, deterministic>
2. <next step>
3. <expected event vs. observed event>

## Expected
<what should happen>

## Actual / Observed
<what does happen — paste the exact error text, stack frame, or screenshot>

## Acceptance Criteria
- [ ] <criterion 1 — testable, atomic>
- [ ] <criterion 2>
- [ ] <criterion N>

## Definition of Done
- [ ] Fix merged
- [ ] Regression test added (per [19 §2](../19_Definition_of_Done.md))
- [ ] Affected suite green locally
- [ ] docs/18 + any affected ADR updated
- [ ] Linked Requirement ID(s) status reflects the fix
```

### 6.2 `type: feat` body

```markdown
## Summary
<one-paragraph statement of the capability>

## Linked Requirement ID(s)
FR-NNN, NFR-NNN (per [16](../16_Requirement_Traceability_Matrix.md))

## Module
M-NN (per [22_Module_Roadmap §5](../22_Module_Roadmap.md))

## Acceptance Criteria
- [ ] <criterion 1 — testable, atomic, references the RTM ID it verifies>
- [ ] <criterion 2>
- [ ] <criterion N>

## Out of Scope
- <explicit boundaries — what this issue does NOT cover>

## Tests Required
- <unit / contract / integration / eval / e2e / security / ops — per [14](../14_Testing_Strategy.md)>
- <test file paths and the requirement IDs they verify>

## Definition of Done
- [ ] All ACs above checked
- [ ] Linked Requirement ID(s) moved to **Done** in [16](../16_Requirement_Traceability_Matrix.md) when the closing PR merges
- [ ] Lint + typecheck + affected tests green
- [ ] docs/18 + affected ADRs updated
- [ ] Observability covers the new path (NFR-005)
- [ ] Tenant isolation verified where data access changed (FR-057)
- [ ] Idempotency verified where a job/endpoint changed (NFR-007)
```

### 6.3 `type: epic` body

```markdown
## Goal / Outcome
<one-paragraph outcome statement — what the world looks like when this epic is closed>

## Module
M-NN (per [22_Module_Roadmap §5](../22_Module_Roadmap.md))

## Linked Requirement ID(s)
FR-NNN, NFR-NNN (per [16](../16_Requirement_Traceability_Matrix.md))

## Scope (in)
- <bullet>

## Scope (out)
- <bullet>

## Epic-Level Acceptance Criteria
- [ ] <criterion 1 — what the module's exit gate requires>
- [ ] <criterion 2>

## Dependencies / Sequencing
- Depends on: <module(s), in `22_Module_Roadmap` order>
- Unblocks: <module(s)>

## Sub-Issues
<native sub-issue list — the `issue-maintainer` populates this with linked sub-issues; the parent renders the "X of Y" progress bar>

## Definition of Done (epic close)
- [ ] All epic-level ACs checked
- [ ] All sub-issues closed
- [ ] Module exit gate (per [22 §6](../22_Module_Roadmap.md)) green
- [ ] Linked Requirement ID(s) in [16](../16_Requirement_Traceability_Matrix.md) reflect completion
```

### 6.4 `type: chore` body

```markdown
## Summary
<one-paragraph statement of the chore>

## Linked Requirement ID(s)
<RTM IDs only if the chore closes a tracked requirement; otherwise "N/A — tooling/refactor, no behavior change">

## Acceptance Criteria
- [ ] <criterion — typically one or two: the chore is done; CI is green>

## Definition of Done
- [ ] ACs checked
- [ ] CI green
- [ ] docs/18 + affected ADRs updated if the chore changes process or contract
```

### 6.5 `type: docs` body

```markdown
## Summary
<one-paragraph statement of the docs change>

## Linked Requirement ID(s)
N/A (unless the docs change closes a documentation gap that blocks a requirement's DoD)

## Acceptance Criteria
- [ ] The stated change is present in the named doc(s)
- [ ] No new orphan docs (every new file is referenced from a table of contents or an index)
- [ ] Stale/orphaned docs archived (per [18 §6 hygiene](../18_Project_Memory.md))

## Definition of Done
- [ ] ACs checked
- [ ] `docs/18` reflects the change
```

## 7. Sub-Issue Linking (epics)

For an epic (`type: epic`), link each sub-issue **natively** using GitHub's sub-issue mechanism so the parent renders the live "X of Y" progress bar and closing a sub-issue auto-increments the counter. The `issue-maintainer` uses `gh issue create --parent <epic-number>` (or the API equivalent) and reports the bar state in its return contract.

**Fallback** (only if the native API is unavailable for a given host): maintain a markdown task list of `#NN` references in the epic body, but mark the epic `state: needs-info` and surface the limitation to the conductor — the fallback is **not** silent. The project policy is native linking.

## 8. Acceptance-Criteria Checkbox Ledger (load-bearing)

The `- [ ]` boxes in a body are the **live completion ledger**. Discipline:

1. **Flip at merge-time, per criterion** — the moment a PR closes, the `issue-maintainer` reads the body, flips every AC that the merged PR satisfies `- [ ]` → `- [x]`, writes the body back in the **same** merge-ingest step. **Not** batched to close-time.
2. **An epic is closeable only when** every AC box in the epic body is checked **AND** every sub-issue is closed. The `issue-maintainer` verifies before closing the epic.
3. **A stale ledger forces re-audit** — an epic showing `0 of N` while its work shipped across several merged PRs will trigger an expensive file-by-file re-audit by the next agent. This is the failure mode the ledger prevents.

## 9. Duplicate-Check Discipline

Before filing **any** issue:

1. Search open issues with `gh issue list --search "<key terms>" --state all` (or the API equivalent).
2. Search closed issues — a fixed-then-regressed match is higher signal than a fresh file.
3. If a match exists, comment on it (or reopen) rather than duplicate-file. The `issue-maintainer` reports the duplicate it deferred to in its return contract.

## 10. Closing Discipline

- **Close on AC completion, not on PR merge alone.** A PR may merge before all ACs are satisfied (e.g., the PR satisfies 3 of 5 ACs and another PR will satisfy the rest). The `issue-maintainer` keeps the issue open until **every** AC box is checked, even if the implementing PR is already merged.
- **Drop status labels on close** — `status: blocked`, `status: in-review`, `status: needs-info` are removed when the issue closes. Do not leave them hanging.
- **Reference the closing PR** in a closing comment (`Closes via #PR-NN.`) for audit trail.

## 11. Return Contract (recap)

The `issue-maintainer` returns a terse report on every operation:

- Issue / epic number(s) created or closed.
- Labels applied (canonical names only).
- Sub-issue links established (with the "X of Y" the parent now shows).
- Any duplicate found and deferred to.
- Any classification judgment call (e.g., a path that touched three areas — explain why the smallest set was chosen).
- Any follow-up issue filed for a code fix the agent found but did not write.

The `issue-maintainer` **does not** write repo files. It operates the tracker.

## 12. Change Control

This doc is canonical. Changes to the label taxonomy, body templates, or area-classification rules require:

1. A PR titled `docs(25): <change summary>` that updates this file.
2. A migration note in `docs/18` §6 if any change affects the `issue-maintainer` agent's behavior in flight.
3. A `type: chore` issue for the rename / re-label pass on any existing issues touched by the change.

No silent edits — uniformity is the property we are protecting.
