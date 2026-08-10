# 18 — Project Memory

**Product:** SAP Automation Intelligence Engine (SAIE)
**Document status:** Living — update on every significant decision or context change.
**Last updated:** 2026-08-10

> This is the project's persistent working memory: context that is non-obvious from the code, current state, decisions, and conventions. Keep it current; treat it as the first place to look when resuming work.

---

## 1. One-Paragraph Context

SAIE is an **enterprise multi-agent intelligence platform** that continuously observes the SAP ecosystem (documentation, announcements, community, partner evidence), detects meaningful change, extracts **automation patterns**, reconstructs **technical architecture**, validates **opportunities**, scores buildability, and emits a weekly **Saturday intelligence report** plus a ranked build/replace backlog. The central question: *"What changed, what automation pattern does it reveal, where can it be applied, and what should we build or replace because of it?"*

## 2. Source of Truth

- **Master design:** `SAP_Automation_Intelligence_Master_Design.pdf` (17 pages, 10 capabilities, 6 pre-code documents).
- **Engineering blueprint:** `docs/01–19` — generated from the master design and currently the definitive spec for implementation.
- **Repo:** `https://github.com/ClaudiousAI/AutomataIQ` (branch `main`).

## 3. Current State

- ✅ Repo initialized; README committed; remote set.
- ✅ Phase 1 (engineering documentation) **complete** — `docs/` contains all 19 deliverables.
- ✅ Phase 2 (operational Requirements Traceability Matrix) **complete** — `docs/16` carries the living RTM with stable unique IDs (`FR-001…FR-064`, `NFR-001…NFR-014`); CSV available at `docs/requirements_traceability_matrix.csv`; `CLAUDE.md` created at project root encoding the requirement-ID reference rule.
- ✅ Phase 3 (architecture-before-coding approval gate) **complete & approved** — all 12 concerns in `docs/20_Architecture_Review_Pack.md` approved by **Ganesh on 2026-08-10** with no conditions. Implementation may now begin per [15_Project_Roadmap](./15_Project_Roadmap.md).
- ⏳ Next: Settle open decisions OD-1…OD-8, then Phase 2 platform foundation — repo scaffolding, CI/CD, environments.

## 4. Key Decisions (recorded fully in `docs/17_Architecture_Decision_Records/`)

| ADR | Decision |
|---|---|
| 0001 | Next.js + FastAPI stack |
| 0002 | Orchestration framework for agents (typed contracts + artifacts) |
| 0003 | Model-agnostic LLM gateway (tiered, versioned, budgeted) |
| 0004 | PostgreSQL + pgvector + Neo4j + S3 + search |
| 0005 | Event-driven, idempotent, replayable jobs |
| 0006 | Deterministic preprocessing before generative reasoning |
| 0007 | Evidence-first with confirmed/inferred/speculative labeling |

## 5. Conventions & Non-Obvious Facts

- **Saturday is the reporting boundary**; a "week" is the six days since the previous Saturday. Reports are titled *"SAP Automation Intelligence — Week ## / YYYY"*.
- **Scoring weights:** Business value 20%, Automation potential 15%, Technical feasibility 15%, Reusability 15%, Demand 10%, Differentiation 10%, Clean-core relevance 10%, minus complexity penalty up to −15%. Scores are **recommendations, not facts**; reviewer override with reason is always allowed.
- **Evidence badges:** Confirmed / Corroborated / Inferred / Speculative — never color-only in the UI.
- **Agents never invent facts, never deploy production changes, never bypass governance.** They communicate via typed contracts + persistent artifacts.
- **Low-confidence / high-impact items route to the Review Queue; low-confidence is never auto-promoted.** Incomplete reports are never published (retry + alert).
- **Deterministic-first pipeline:** cheap hash/diff gates expensive semantic analysis.
- **Tenant isolation at every query boundary**; roles: `platform_admin`, `tenant_admin`, `architect`, `analyst`, `reviewer`, `executive`, `read_only`.

## 6. Known Gotchas

- **Git:** the machine's home directory (`C:\Users\DELL`) is itself a git repo pointing at `ClaudiousAI/AIStuff.git` — unrelated to this project. Run git from inside `AutomataIQ\` (it has its own `.git`). Do not run git commands that resolve to the home repo by mistake.
- **PDF tooling:** this machine lacks `pdftoppm`/poppler; `pypdf` (pip) was installed to extract the master design text. Reinstall note: `pip install pypdf`.
- **MCP:** `code-review-graph` is enabled (see `CLAUDE.md`); graph auto-updates on file changes.

## 7. Definition of Done Pointer

Work is done only when it satisfies [19_Definition_of_Done](./19_Definition_of_Done.md) — including traceability via [16_Requirement_Traceability_Matrix](./16_Requirement_Traceability_Matrix.md).

## 8. Open Questions / Future Work

- Concrete orchestration engine choice (ADR-0002 deferral).
- Concrete vector/search vendor (Postgres FTS vs OpenSearch) at Phase 3.
- Saturday report recipient/notification channel details (Phase 11).
- Customer source-pack & public-API scope refinement (Phase 16).
