# 18 — Project Memory

**Product:** SAP Automation Intelligence Engine (SAIE)
**Document status:** Living — update on every significant decision or context change.
**Last updated:** 2026-08-11 (Frontend stack finalized — ADR-0015)

> This is the project's persistent working memory: context that is non-obvious from the code, current state, decisions, and conventions. Keep it current; treat it as the first place to look when resuming work.

---

## 1. One-Paragraph Context

SAIE is an **enterprise multi-agent intelligence platform** that continuously observes the SAP ecosystem (documentation, announcements, community, partner evidence), detects meaningful change, extracts **automation patterns**, reconstructs **technical architecture**, validates **opportunities**, scores buildability, and emits a weekly **Saturday intelligence report** plus a ranked build/replace backlog. The central question: *"What changed, what automation pattern does it reveal, where can it be applied, and what should we build or replace because of it?"*

## 2. Source of Truth

- **Master design:** `SAP_Automation_Intelligence_Master_Design.pdf` (17 pages, 10 capabilities, 6 pre-code documents).
- **Engineering blueprint:** `docs/01–23` — generated from the master design and current design phases; currently the definitive spec for implementation.
- **Repo:** `https://github.com/ClaudiousAI/AutomataIQ` (branch `main`).

## 3. Current State

- ✅ Repo initialized; README committed; remote set.
- ✅ Phase 1 (engineering documentation) **complete** — `docs/` contains all 19 deliverables.
- ✅ Phase 2 (operational Requirements Traceability Matrix) **complete** — `docs/16` carries the living RTM with stable unique IDs (`FR-001…FR-064`, `NFR-001…NFR-014`); CSV available at `docs/requirements_traceability_matrix.csv`; `CLAUDE.md` created at project root encoding the requirement-ID reference rule.
- ✅ Phase 3 (architecture-before-coding approval gate) **complete & approved** — all 12 concerns in `docs/20_Architecture_Review_Pack.md` approved by **Ganesh on 2026-08-10** with no conditions. Implementation may now begin per [15_Project_Roadmap](./15_Project_Roadmap.md).
- ✅ All 8 open decisions (OD-1…OD-8) **resolved** — initially AWS + EKS + Helm, Temporal, Keycloak, container hosting, Postgres FTS, Bedrock embeddings, OWASP ZAP. Recorded as **ADRs 0008–0013** (0008/0009/0011/0012 now superseded — see below).
- ✅ Phase 4 (AI Layer specification) **complete** — `docs/21_AI_Layer_Specification.md` defines all 11 agents plus the LLM Gateway by name, purpose, inputs, outputs, prompt template, tools, memory, retry policy, error handling, evaluation criteria, and success criteria.
- ✅ Phase 5 (lock cost-minimized stack) **complete** — **[ADR-0014](./17_Architecture_Decision_Records/0014-cost-minimized-open-source-stack.md)** locks an open-source, self-hosted stack: FastAPI · React (JavaScript) · PostgreSQL · Qdrant · Neo4j CE · MinIO · Redis · LangGraph · Celery · APScheduler · Docker + Nginx · GitHub Actions · Prometheus/Grafana/Loki · Keycloak · OpenAI (primary) + Gemini (fallback). Supersedes ADR-0008/0009/0011/0012; amends ADR-0004 (pgvector → Qdrant). **Stack is frozen unless a compelling reason is documented in a new ADR.**
- ✅ Phase 5.1 (frontend stack) **complete** — **[ADR-0015](./17_Architecture_Decision_Records/0015-react-javascript-frontend.md)** locks the frontend as **React + JavaScript (Vite SPA)** served as static assets behind Nginx (no SSR, no Node runtime in production), amending ADR-0001 (Web UI) and ADR-0014 (frontend row). Frontend architecture (`docs/11`) and AI layer (`docs/21`) are now **Finalized**.
- ✅ Phase 6 (module roadmap) **complete** — **[22_Module_Roadmap](./22_Module_Roadmap.md)** defines **16 buildable modules** (M01–M16), each with Scope, Dependencies, Acceptance criteria, Tests, and Definition of Done. Modules are implemented one at a time in dependency order; all 78 RTM requirements are covered (FR-059…064 deferred to Phase 15–16 extension modules).
- ✅ Phase 7 (development rules) **complete** — **[23_Development_Rules](./23_Development_Rules.md)** codifies the mandatory pre-coding gate (requirements, dependencies, architecture, impact) and post-coding gate (tests, docs, RTM, project memory), feature/module completion definitions, and enforcement. Checklist templates provided for PR use.
- ⏳ Next: **Wave 1 — M01 Project Foundation** (monorepo scaffold, CI skeleton, Docker Compose, OTel bootstrap) — the first code module; ready to build.

## 4. Key Decisions (recorded fully in `docs/17_Architecture_Decision_Records/`)

| ADR | Decision |
|---|---|
| 0001 | React (JavaScript) + FastAPI stack |
| 0002 | Orchestration framework for agents (typed contracts + artifacts) |
| 0003 | Model-agnostic LLM gateway (tiered, versioned, budgeted) |
| 0004 | PostgreSQL + Neo4j + MinIO + search *(amended by 0014: pgvector → Qdrant)* |
| 0005 | Event-driven, idempotent, replayable jobs |
| 0006 | Deterministic preprocessing before generative reasoning |
| 0007 | Evidence-first with confirmed/inferred/speculative labeling |
| 0008 | ~~AWS + EKS + Helm platform~~ — superseded by 0014 |
| 0009 | ~~Temporal as orchestration engine~~ — superseded by 0014 (→ LangGraph + Celery) |
| 0010 | Keycloak as identity provider |
| 0011 | ~~Next.js hosted as container in cluster~~ — superseded by 0014 (→ Docker) |
| 0012 | ~~Postgres FTS + Bedrock embeddings~~ — superseded by 0014 (→ Qdrant + OpenAI embeddings) |
| 0013 | OWASP ZAP for DAST |
| 0014 | **Locked cost-minimized open-source stack** (Accepted — the operative stack) |
| 0015 | **React (JavaScript) + Vite frontend** (Accepted — amends 0001 Web UI, 0014 frontend row) |

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

Work is done only when it satisfies [19_Definition_of_Done](./19_Definition_of_Done.md) — including traceability via [16_Requirement_Traceability_Matrix](./16_Requirement_Traceability_Matrix.md). AI-layer implementation must additionally satisfy [21_AI_Layer_Specification](./21_AI_Layer_Specification.md).

## 8. Open Questions / Future Work

- Saturday report recipient/notification channel details (Phase 11).
- Customer source-pack & public-API scope refinement (Phase 16).
- Phase 2 infra details (per ADR-0014, all self-hosted): secrets management (Docker secrets / SOPS), Keycloak realm + OIDC client setup, Qdrant HA if prod scale demands it, MinIO bucket policy.
