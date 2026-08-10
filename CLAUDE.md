# CLAUDE.md — SAP Automation Intelligence Engine (SAIE)

## Product Context

SAIE is a **multi-agent enterprise intelligence platform** that continuously monitors the SAP ecosystem, detects meaningful change, extracts automation patterns, reconstructs technical architecture, validates opportunities, and produces a recurring Saturday intelligence report with a ranked build/replace backlog.

**Central question:** *"What changed, what automation pattern does it reveal, where can it be applied, and what should we build or replace because of it?"*

---

## Architecture Approval Gate (Phase 3 — Mandatory Rule)

**Do not create implementation source files until `docs/20_Architecture_Review_Pack.md` is approved across all 12 concerns:** system architecture, AI architecture, agent architecture, database schema, APIs, background workers, scheduler design, queue architecture, error handling, security, deployment, and monitoring.

If implementation is requested before approval, first direct the user to approve or revise `docs/20_Architecture_Review_Pack.md`.

## Requirements Traceability (Phase 2 — Mandatory Rule)

**Every code change, commit, and PR must reference one or more unique Requirement IDs from the RTM (`docs/16_Requirement_Traceability_Matrix.md`).**

| Artifact | Rule |
|---|---|
| **PR / merge request title** | Must include Requirement ID(s), e.g. `FR-010, FR-013` |
| **Commit messages** | Every commit must include at least one Requirement ID |
| **Test files** | Must reference the Requirement ID(s) they verify |
| **New behavior without existing ID** | Add a new stable ID to `docs/16` *before* coding, not after |

- IDs are stable and never reused. If a requirement is retired, its ID is marked `Deferred`.
- Status (`Not Started → In Progress → Done`) is updated in the RTM when DoD is met.

---

## Key Documentation

| Doc | Purpose |
|---|---|
| `docs/01_Product_Requirements.md` | PRD — vision, users, success metrics |
| `docs/02_Functional_Requirements.md` | All FRs with acceptance criteria |
| `docs/03_NonFunctional_Requirements.md` | NFRs (security, reliability, auditability, etc.) |
| `docs/04_System_Architecture.md` | Tech stack, container view, data flow |
| `docs/06_Agent_Architecture.md` | Agent operating model and pipeline |
| `docs/07_Database_Design.md` | 16-table schema, relationships, indexes |
| `docs/08_API_Design.md` | REST contracts, event schemas, RBAC |
| `docs/15_Project_Roadmap.md` | 16-phase plan with done criteria |
| `docs/16_Requirement_Traceability_Matrix.md` | Living RTM with FR-NNN / NFR-NNN IDs |
| `docs/requirements_traceability_matrix.csv` | Machine-readable RTM (for tooling/reporting) |
| `docs/18_Project_Memory.md` | Non-obvious context and current state |
| `docs/19_Definition_of_Done.md` | DoD for all work |

---

## Architecture in a Nutshell

- **Stack (locked by [ADR-0014](./docs/17_Architecture_Decision_Records/0014-cost-minimized-open-source-stack.md)):** Next.js + TypeScript (UI) · Python FastAPI (API) · Celery + APScheduler (jobs/scheduler) · LangGraph (agent orchestration) · PostgreSQL (tx + FTS) · Qdrant (vectors) · Neo4j Community (graph) · MinIO (objects) · Redis (cache + streams) · Prometheus/Grafana/Loki (observability) · Docker + Nginx (deployment) · Keycloak (identity) · OpenAI primary / Gemini fallback (LLMs)
- **Agents:** Discovery → Evidence → Change → Automation → Architecture → Opportunity → Scoring → Knowledge → Report → Review → Governance (typed contracts + persistent artifacts; agents never invent facts, never deploy, never bypass governance)
- **Fact model:** every claim is labeled **confirmed / inferred / speculative** with evidence links; low confidence is never auto-promoted
- **Saturday boundary:** reporting week is the six days since previous Saturday
- **Scoring:** weighted composite (BV 20%, AP 15%, TF 15%, Reusability 15%, Demand 10%, Differentiation 10%, Clean-Core 10%) minus complexity penalty up to −15%; scores are recommendations with rationale; reviewer override always allowed

---

## Key Conventions

- **Tenant isolation at every query boundary**; RBAC: platform_admin, tenant_admin, architect, analyst, reviewer, executive, read_only
- **Idempotent, replayable jobs** — re-runs produce no duplicates
- **Deterministic preprocessing before any LLM call** — hash/diff gates expensive semantic analysis
- **LLM gateway is model-agnostic** — no provider-specific code outside the gateway
- **Versioned prompts, models, classifiers** — every run records (model, prompt_version, model_version)
- **OpenTelemetry for observability**; cost per source/agent tracked; alerts + runbooks

---

## Code Style

- TypeScript: strict mode, ESLint + Prettier, App Router
- Python: type-checked, Pydantic schemas at service boundaries, async workers
- IDs: ULID/UUIDv7 for global ordering; human-safe slugs for canonical keys
