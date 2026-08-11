# 22 — Module Roadmap (Phase 6)

**Product:** SAP Automation Intelligence Engine (SAIE)
**Document status:** Baseline
**Related docs:** [04_System_Architecture](./04_System_Architecture.md) · [10_Backend_Architecture](./10_Backend_Architecture.md) · [12_DevOps_Architecture](./12_DevOps_Architecture.md) · [15_Project_Roadmap](./15_Project_Roadmap.md) · [16_Requirement_Traceability_Matrix](./16_Requirement_Traceability_Matrix.md) · [19_Definition_of_Done](./19_Definition_of_Done.md) · [21_AI_Layer_Specification](./21_AI_Layer_Specification.md)

---

## 1. Purpose & Build Strategy

This roadmap decomposes the product into **independently buildable modules**. It exists because the product must **never be built as a single big-bang request**. Each build session targets **one module** (or one vertical slice inside it) in dependency order, and a module exits only when its Definition of Done below passes.

**Operating rules:**
1. **One module at a time.** A session plans, builds, tests, and closes one module (or slice) before starting a dependent module.
2. **Dependencies first.** A module never starts before its declared dependencies are closed (see §3 graph).
3. **Requirement traceability is mandatory.** Every acceptance criterion, test, and commit in a module references FR-/NFR- IDs from [16_Requirement_Traceability_Matrix](./16_Requirement_Traceability_Matrix.md) (per [CLAUDE.md](../CLAUDE.md) and [19 §2.1](./19_Definition_of_Done.md)).
4. **Universal DoD applies to every module** ([19 §2](./19_Definition_of_Done.md)): requirement IDs, review, lint/typecheck, unit+contract tests, no new high-severity security findings, docs/18 + affected ADRs updated, NFRs satisfied.
5. **Each module maps to one or more roadmap phases** ([15](./15_Project_Roadmap.md)) and, where AI-capable, to agents in [21](./21_AI_Layer_Specification.md).

**Scope of this document:** the core product build, Phases 2–14. Phase 15–16 (Continuous Learning / productization, FR-059…064) are tracked as an **extension module** in §7 and detailed when Phase 15 approaches.

---

## 2. Module Inventory

Your requested 14 modules form the spine. Two additions are mandated by the RTM as distinct buildable units: **M11 Knowledge & Search** (FR-038…044, Phase 9 — a standalone deliverable with its own SLOs) and **M15 Governance** (FR-053…058, Phase 12 — a distinct policy/audit/review surface). M14 Monitoring is kept as your "Monitoring" module; Deployment is M16.

| # | Module | Roadmap phase(s) | Primary requirements |
|---|---|---|---|
| M01 | Project Foundation | 2 | NFR-005, NFR-006 |
| M02 | Authentication & Authorization | 2 | FR-053, FR-057, NFR-004 |
| M03 | Database & Storage | 3 | FR-001, FR-008, FR-019, FR-038, FR-043, NFR-004, NFR-007 |
| M04 | Core Backend | 2–3 | NFR-004, NFR-005, NFR-006, NFR-007 |
| M05 | AI Infrastructure (LLM Gateway) | 5 | FR-054, NFR-006, NFR-012, NFR-013 |
| M06 | Agent Framework | 5 | FR-054, FR-056, NFR-006, NFR-007 |
| M07 | Discovery Engine | 4 | FR-001…007, NFR-007, NFR-011 |
| M08 | Research Engine (Change + Automation + Architecture) | 5–7 | FR-008…010, 015…027, NFR-012, NFR-014 |
| M09 | Validation Engine (Evidence + Opportunity) | 5, 8 | FR-011…014, 028…033, FR-056, NFR-008 |
| M10 | Scoring Engine | 8 | FR-034…037, NFR-008 |
| M11 | Knowledge & Search | 9 | FR-038…044, NFR-001, NFR-009 |
| M12 | Reporting | 11 | FR-045…051, NFR-002, NFR-009 |
| M13 | Workspace / Dashboard (Frontend) | 10 | FR-052, FR-053, FR-055, NFR-008 |
| M14 | Monitoring & Observability | 12 | FR-055, FR-058, NFR-005, NFR-010, NFR-012 |
| M15 | Governance (Review + Policy + Audit) | 12 | FR-053…058, NFR-001, NFR-012 |
| M16 | Deployment & Environments | 2, 14 | NFR-003, NFR-009, NFR-010 |

---

## 3. Dependency Graph

```
M01 Project Foundation
 ├── M02 Authentication ───────────────┐
 ├── M03 Database & Storage ───────────┤
 ├── M04 Core Backend ◄────────────────┤
 │    ├── M05 AI Infrastructure ──┐    │
 │    └── M06 Agent Framework ◄───┘    │
 │         ├── M07 Discovery Engine     │
 │         │    └── M08 Research Engine │
 │         │         └── M09 Validation │
 │         │              └── M10 Scoring│
 │         │                   └── M11 Knowledge & Search ──► M13 Dashboard
 │         │                        └── M12 Reporting ───────► M13
 │         └── M15 Governance ◄── (M02, M05, M06, M12, M14)
 │
 ├── M14 Monitoring (starts at M04, continuous)
 ├── M16 Deployment (starts at M01, continuous)
 └── M13 Dashboard (starts once M02+M04 land; consumes M07–M12 APIs)
```

**Build waves (what a team actually runs):**
- **Wave 1 — substrate:** M01 → M02, M03, M04 (M02 and M03 run in parallel after M01; M04 consumes both).
- **Wave 2 — AI substrate:** M05, M06 (after M04).
- **Wave 3 — engines, in pipeline order:** M07 → M08 → M09 → M10. M11 begins once M07–M09 outputs exist (graph/scaffold can start earlier).
- **Wave 4 — experience:** M12 (needs M10+M11), M13 (can start at M02+M04 using contract-first mocked APIs, in parallel with Wave 3).
- **Wave 5 — ops & governance:** M14 and M16 are continuous from Waves 1–2; M15 lands after M02, M05, M06 (policy/audit hooks) and before Phase 12 exit.

**Vertical-slice guidance inside modules** (never build a whole module as one session): e.g. M08 = slice 1 change detection (FR-008…010) → slice 2 automation extraction (FR-015…020) → slice 3 architecture reconstruction (FR-021…027). Each slice passes its own tests and DoD before the next.

---

## 4. RTM → Module Mapping

| RTM module (docs/16) | Roadmap module(s) |
|---|---|
| Discovery Engine | M07 |
| Change Detection | M08 |
| Evidence Engine | M09 |
| Automation Intelligence | M08 |
| Architecture Reconstruction | M08 |
| Opportunity Engine | M09 |
| Scoring Engine | M10 |
| Knowledge Graph | M11 |
| Search | M11 |
| Reporting | M12 |
| Workspace (UI) | M13 |
| Governance & Ops | M15 (ops/monitoring signals → M14) |
| Continuous Learning | Extension (§7) |
| Platform (NFR-001…013) | M01–M06, M14, M16 + cross-cutting checks in every module |

---

## 5. Module Specifications

Each module lists **Scope · Dependencies · Acceptance criteria · Tests · Definition of Done**. Tests reference the [14_Testing_Strategy](./14_Testing_Strategy.md) levels (unit / contract / integration / eval / E2E / security / ops). Every test file must reference its requirement ID(s) in its header (per [19 §2.1](./19_Definition_of_Done.md)).

---

### M01 — Project Foundation

- **Scope**
  - Monorepo layout: `web/`, `backend/`, `infra/`, `docs/`, `e2e/`.
  - Python env + lockfiles and linting/type-checking (Ruff/mypy); React + JavaScript (Vite) scaffold (ESLint + Prettier).
  - GitHub Actions CI skeleton: lint, typecheck, unit, dependency/SAST scan.
  - `docker compose up` skeleton: `web`, `api`, `nginx` containers responding on `/health`.
  - Config management (pydantic-settings / zod) + env overlays; `.env.example`; SOPS/Docker-secret convention documented (no secrets in repo).
  - OpenTelemetry SDK bootstrap (metrics/logs/traces wiring).
  - **Out of scope:** real services, real data stores, auth flows (later modules).
- **Dependencies:** none (starts the build).
- **Acceptance criteria**
  - A fresh clone passes `make lint`, `make typecheck`, `make test` (NFR-006).
  - CI runs on every PR and fails red on violation (NFR-006).
  - `docker compose up` starts web + api skeletons that respond on `/health` (NFR-005).
  - No secrets or internal addresses committed; `.env.example` documented (NFR-004).
- **Tests**
  - `tests/health`: skeleton endpoints respond (NFR-005).
  - CI pipeline test: lint/typecheck/unit run green (NFR-006).
  - Unit: env-overlay resolution (NFR-006).
- **Definition of Done**
  - All 5 acceptance criteria pass; CI green; Docker skeletons build; contribution/run conventions documented (`backend/CONTRIBUTING.md`, `web/README.md`); docs/18 updated.

---

### M02 — Authentication & Authorization

- **Scope**
  - Keycloak self-hosted (Docker, per [ADR-0014](./17_Architecture_Decision_Records/0014-cost-minimized-open-source-stack.md)); realm + `web`/`api` clients provisioned.
  - OIDC authorization-code flow for web; token introspection for API; refresh + logout.
  - RBAC roles seeded: `platform_admin`, `tenant_admin`, `architect`, `analyst`, `reviewer`, `executive`, `read_only` (FR-053).
  - API auth middleware: verify token, resolve roles, propagate `tenant_id` (FR-057).
  - Row-level-security helper scaffolding consumed by M03.
  - Login/logout/failed-auth audit events (feeds FR-054).
  - **Out of scope:** user self-registration, fine-grained permission matrices beyond the 7-role model.
- **Dependencies:** M01.
- **Acceptance criteria**
  - Login via Keycloak yields a session; token carries roles + tenant (NFR-004).
  - All 7 roles enforced on a representative endpoint set (FR-053).
  - Cross-tenant access with a valid token denied at the API boundary (FR-057).
  - Client secret / realm keys never committed; injected via env/secrets (NFR-004).
  - Every auth event writes an audit row (FR-054 groundwork).
- **Tests**
  - Security: RBAC escalation matrix (7 roles × forbidden endpoints) (FR-053).
  - Security: cross-tenant token rejected (FR-057).
  - Contract: token→claims→role resolution schema (NFR-004).
  - Integration: Keycloak → web → api happy path + refresh (NFR-004).
- **Definition of Done**
  - All acceptance criteria pass; RLS helpers ready for M03; RBAC matrix documented; adversarial auth suite green.

---

### M03 — Database & Storage

- **Scope**
  - PostgreSQL: full schema ([07_Database_Design](./07_Database_Design.md)) via Alembic migrations; FTS + trigram indexes; RLS policies + tenant-scoped functions; taxonomy seeds (FR-019).
  - Redis: cache namespace + Streams topics + consumer groups + DLQ.
  - Qdrant: collection + payload fields + HNSW config (FR-043).
  - Neo4j: constraints + seed (FR-038, FR-041).
  - MinIO: buckets + versioning/lifecycle/retention policies (FR-008, NFR-011).
  - Migration + seed runner, idempotent and re-runnable (NFR-007).
  - **Out of scope:** business logic, connectors, search/query engine (M07/M11).
- **Dependencies:** M01.
- **Acceptance criteria**
  - `alembic upgrade head` from a clean DB is idempotent and yields the docs/07 schema (NFR-006).
  - RLS: cross-tenant SELECT/INSERT denied in SQL-level tests (FR-057, NFR-004).
  - Redis Streams topics + DLQ consumer groups provisioned (NFR-007).
  - Qdrant collection and Neo4j constraints created by bootstrap (FR-043, FR-038).
  - MinIO buckets with lifecycle created; retention enforced (FR-008, NFR-011).
  - Seed re-runs produce no duplicates (NFR-007).
- **Tests**
  - Integration: migrations up/down across clean + prior version (NFR-006).
  - Security: RLS tenant matrix in SQL (FR-057, NFR-004).
  - Integration: stream publish / consume / DLQ round-trip (NFR-007).
  - Contract: taxonomy seed schema (FR-019).
- **Definition of Done**
  - Schema migrated on dev + staging; RLS tests green; bootstrap reproducible in a container; storage layout documented under `infra/`.

---

### M04 — Core Backend

- **Scope**
  - FastAPI app factory, lifespan, typed exception handlers (error-envelope contract).
  - Pydantic schemas bound at every service boundary (typed contracts, NFR-006).
  - Tenant-scoped repository layer (RLS-aware queries).
  - Storage adapters behind interfaces: Postgres, Qdrant, Neo4j, MinIO, Postgres FTS, Redis (portability per ADR-0014 / NFR-013).
  - Event bus: typed versioned event schemas; Redis Streams producer/consumer helpers + DLQ handling.
  - OTel middleware: request tracing, metrics, log correlation by `trace_id`.
  - Health/readiness endpoints; API versioning strategy.
  - **Out of scope:** business engines (M07+), auth internals (M02), UI.
- **Dependencies:** M01, M02, M03.
- **Acceptance criteria**
  - Invalid input at any boundary returns typed 422; every boundary Pydantic-validated (NFR-006).
  - Repos accept tenant context; no cross-tenant rows returned (FR-057).
  - Swapping a storage adapter requires no caller changes (NFR-013).
  - Events carry versioned schemas; unknown/malformed versions route to DLQ (NFR-006, NFR-007).
  - OTel spans/metrics/logs emitted on every API call (NFR-005).
- **Tests**
  - Contract: every REST endpoint request/response schema (NFR-006).
  - Integration: repository tenant scoping (FR-057).
  - Contract: event-schema version validation (NFR-006, NFR-007).
  - Integration: poison message → DLQ (NFR-007).
- **Definition of Done**
  - API contract snapshot + adapter tests green; OTel spans visible in local Grafana; M07+ builds consume M04 without touching its internals.

---

### M05 — AI Infrastructure (LLM Gateway)

- **Scope**
  - LLM Gateway (ADR-0003): OpenAI primary + Gemini fallback; provider adapters behind one interface.
  - Tier router: task tier (T0–T3) → model + budget (NFR-012).
  - Prompt registry: versioned `p_*_v1` templates, content-managed (never hardcoded in agents) — seeded from [21 §4](./21_AI_Layer_Specification.md).
  - Model registry: `model`, `model_version`, `prompt_version` recorded per run (FR-054).
  - Prompt-response + extraction cache, deterministic keys (NFR-012).
  - JSON Schema validator: invalid/partial output → retry → `needs_review` (never silent) ([21 §5](./21_AI_Layer_Specification.md)).
  - Token/cost accountant per source/agent/tenant + budget breaker (NFR-012).
  - Embeddings service (OpenAI) for M11.
  - **Out of scope:** agents (M06+), crawling (M07).
- **Dependencies:** M04.
- **Acceptance criteria**
  - Same prompt resolves to the configured model per tier; OpenAI failure fails over to Gemini (NFR-013).
  - Identical cached requests return a cache hit; cost not double-counted (NFR-012).
  - Every call records `(model, model_version, prompt_version, usage, cost)` (FR-054, NFR-006).
  - Schema-invalid output → retry → `needs_review`; no silent acceptance ([21 §5](./21_AI_Layer_Specification.md)).
  - Per-tenant budget breach → tier downgrade + alert (NFR-012).
- **Tests**
  - Unit: tier router + budget math (NFR-012).
  - Integration: provider failover (OpenAI down → Gemini) (NFR-013).
  - Contract: gateway request/response envelope + schema validation (FR-054).
  - Eval: structured-output fixture suite passes schema validation (NFR-006).
- **Definition of Done**
  - Gateway green against a mock provider (real keys optional); cost ledger persisted; prompt registry seeded with docs/21 §4 v1 templates.

---

### M06 — Agent Framework

- **Scope**
  - LangGraph orchestration scaffold: graph state, node/edge definitions, per-agent sandbox ([21 §2](./21_AI_Layer_Specification.md)).
  - Typed agent envelope: artifact in → artifact out, schema-validated (ADR-0002).
  - Artifact store: write artifacts to MinIO + metadata in Postgres, versioned.
  - Idempotency: `run_id` keys; re-runs produce no duplicates (NFR-007).
  - Per-agent retry/backoff/error policy ([21 §4](./21_AI_Layer_Specification.md) retry fields).
  - Human-in-the-loop: `needs_review` pause via LangGraph interruption + Review Queue integration (FR-056).
  - `agent_runs` audit + run state machine (FR-054).
  - Governance pre/post execution hooks (feeds M15).
  - **Out of scope:** specific agents (M07–M10), LLM calls (M05).
- **Dependencies:** M04, M05.
- **Acceptance criteria**
  - A graph runs an agent chain end-to-end with artifact persistence (NFR-006).
  - Re-running a `run_id` produces identical artifacts, no duplicates (NFR-007).
  - Worker crash mid-run → resume from the last completed node (NFR-007).
  - A `needs_review` artifact pauses the graph until a review signal (FR-056).
  - Every run recorded in `agent_runs` with model/prompt versions (FR-054).
- **Tests**
  - Unit: state-machine transitions + idempotency-key handling (NFR-007).
  - Integration: crash-replay (kill worker → resume) (NFR-007).
  - Contract: agent envelope schema (ADR-0002, NFR-006).
  - Integration: review-gate pause/resume (FR-056).
- **Definition of Done**
  - Reference "no-op" agent graph green; artifact store round-trip; audit rows written; review gate demonstrated.

---

### M07 — Discovery Engine

- **Scope**
  - Source registry CRUD + tiering (Tier 1–6) + active status + schedule (FR-001, FR-004).
  - Connectors: HTML, RSS/API, structured docs, sitemap (FR-002).
  - Crawl policy: robots.txt, terms, rate limits, auth boundaries (FR-007, NFR-011).
  - APScheduler jobs + Celery crawl workers; replayable `crawl_runs` (FR-003, NFR-007).
  - Provenance capture: URL, `retrieved_at`, version hash, content (FR-005).
  - Change gating: content-hash skip of unchanged content (FR-006).
  - Source-health metrics (feed M14).
  - **Out of scope:** diff/classification (M08), evidence (M09).
- **Dependencies:** M03, M04, M06.
- **Acceptance criteria**
  - Each connector type crawls to a normalized snapshot + provenance row (FR-001, FR-002, FR-005).
  - Scheduler triggers configured sources within the Saturday six-day boundary (FR-003).
  - Robots/rate/auth policies enforced; violations blocked + logged (FR-007, NFR-011).
  - Re-running a `crawl_run` is idempotent (NFR-007).
  - Unchanged content skipped by the hash gate (FR-006).
- **Tests**
  - Unit: tiering, policy decision (robots/rate), hash-gate (FR-004, FR-006, FR-007).
  - Integration: each connector end-to-end on fixtures (FR-002).
  - Integration: replay idempotency (NFR-007).
  - Security: SSRF / robots / terms bypass attempts blocked (FR-007, NFR-011).
- **Definition of Done**
  - All 4 connector types green on synthetic fixtures; policy suite green; `crawl_runs` replayable; source health surfaced.

---

### M08 — Research Engine (Change + Automation + Architecture)

- **Scope**
  - Versioned snapshots + lexical/semantic diff (FR-008, FR-009).
  - Change classification (closed enum) via deterministic pre-filter + T1 model (FR-010).
  - Automation pattern extraction → full Automation Card fields (FR-015).
  - Automation-type classification + domain/industry taxonomy mapping (FR-016, FR-019).
  - Business problem / pre-automation capture (FR-017); stated vs inferred benefits separation (FR-018).
  - Canonical automation IDs with temporal lineage (FR-020).
  - Architecture flow extraction + technology ID + confirmed/inferred component separation (FR-021…023).
  - Integration-pattern ID, human-in-the-loop capture, validation flags (FR-025…027).
  - Deterministic-first gating: only changed content reaches the LLM (NFR-012).
  - **Out of scope:** evidence confidence/dedup (M09), scoring (M10).
- **Dependencies:** M05, M06, M07.
- **Acceptance criteria**
  - Diff produces lexical + semantic deltas (FR-009).
  - Change classification precision ≥ 85% on the golden set (FR-010, NFR-014).
  - Automation Cards populate all fields; type/domain/industry mapping validated (FR-015…019).
  - Stated vs inferred benefits never conflated (FR-018).
  - Architecture extraction separates confirmed/inferred + emits validation flags (FR-023, FR-027).
  - Only changed content invokes the LLM (NFR-012).
- **Tests**
  - Eval: golden-set precision/recall — change classification (FR-010, NFR-014).
  - Eval: golden-set — automation extraction (FR-015…018, NFR-014).
  - Eval: golden-set — architecture reconstruction (FR-021…024, NFR-014).
  - Contract: card + architecture schemas (FR-015, FR-021, NFR-006).
  - Integration: deterministic gating (unchanged content → no LLM call) (NFR-012).
- **Definition of Done**
  - All three eval gates clear (precision ≥ 85%, relevance ≥ 80%, architecture usefulness ≥ 80%); card/architecture schemas stable; gating verified.

---

### M09 — Validation Engine (Evidence + Opportunity)

- **Scope**
  - Evidence confidence scoring (authority, recency, corroboration, specificity) (FR-011).
  - Canonical finding merge / dedup ≥ 90% (FR-012).
  - Fact labeling confirmed/inferred/speculative on every promoted fact (FR-013).
  - Evidence trail per priority finding (source version + locator) (FR-014).
  - Opportunity gap classification + customer pain/manual-effort mapping (FR-028, FR-029).
  - ECC-to-S/4 + clean-core implications (FR-030).
  - Build-path classification + reuse/dependency assessment (FR-031, FR-032).
  - Human validation checklist per opportunity (FR-033).
  - **Out of scope:** scoring (M10), graph population (M11).
- **Dependencies:** M05, M06, M08.
- **Acceptance criteria**
  - Dedup achieves ≥ 90% duplicate consolidation on the golden set (FR-012, NFR-014).
  - Every promoted fact carries a fact label + evidence reference (FR-013, FR-014).
  - Confidence reflects authority/recency/corroboration (FR-011).
  - Gap and build-path classifications validated on the golden set (FR-028, FR-031).
  - Clean-core / ECC-to-S/4 flags present where implied (FR-030).
  - Low-confidence items route to review, never auto-promoted (FR-056, NFR-008).
- **Tests**
  - Eval: dedup consolidation rate (FR-012, NFR-014).
  - Eval: gap + build-path classification (FR-028, FR-031, NFR-014).
  - Contract: fact-label + evidence-link schema (FR-013, FR-014).
  - Integration: review routing for low confidence (FR-056).
  - Mutation-style: dedup merge edge cases ([14 §8](./14_Testing_Strategy.md)).
- **Definition of Done**
  - Dedup gate ≥ 90%; fact-label contract green; opportunity checklist produced; review routing demonstrated.

---

### M10 — Scoring Engine

- **Scope**
  - Weighted composite: BV 20%, AP 15%, TF 15%, Reusability 15%, Demand 10%, Differentiation 10%, Clean-Core 10%, minus complexity penalty up to −15% (FR-034).
  - Score vector + per-metric rationale stored and exposed (FR-035, NFR-008).
  - Reviewer override with prior/new value + actor + reason + audit trail (FR-036).
  - Deterministic ranking with stable tie-break (FR-037).
  - **Out of scope:** opportunity content (M09), report composition (M12).
- **Dependencies:** M09 (validated opportunities), M04 (API exposure).
- **Acceptance criteria**
  - Composite matches the formula exactly for fixture vectors (FR-034).
  - Score vector + rationale returned by the API (FR-035, NFR-008).
  - Override recorded with actor/reason; audit trail intact (FR-036).
  - Ranking deterministic across re-runs (FR-037).
- **Tests**
  - Unit: formula + penalty clamping + tie-break (FR-034, FR-037).
  - Contract: score-vector API schema (FR-035).
  - Mutation: override/audit invariants (FR-036).
- **Definition of Done**
  - Formula tests green; API exposes scores + rationale; override audit verified.

---

### M11 — Knowledge & Search

- **Scope**
  - Neo4j population: sources → findings → automations → products → processes → industries → technologies → APIs → events → architectures → opportunities (FR-038).
  - Evidence + confidence on nodes and edges (FR-041).
  - End-to-end lineage query: source → extraction → validation → score → report (FR-042, NFR-001).
  - Time-window queries (last 30/90/180 days) + cross-domain queries (FR-039, FR-040).
  - Hybrid search: Postgres FTS facets + Qdrant vector (FR-043).
  - Related-pattern + reusable-architecture recommendations (FR-044).
  - **Out of scope:** extraction (M08/M09), scoring (M10).
- **Dependencies:** M07–M10 outputs, M03 stores, M04 adapters.
- **Acceptance criteria**
  - Graph populated with lineage; every edge carries evidence + confidence (FR-038, FR-041).
  - Time-window and cross-domain query examples pass on fixture data (FR-039, FR-040).
  - Lineage query returns the full source→report chain (FR-042, NFR-001).
  - Hybrid search returns combined results; facets filter correctly (FR-043).
  - p95: search < 3 s, graph < 2 s on the reference set (NFR-009).
  - Recommendations return related patterns/architectures (FR-044).
- **Tests**
  - Integration: graph population + lineage queries (FR-038, FR-042).
  - Integration: temporal + cross-domain queries (FR-039, FR-040).
  - Performance: p95 search/graph benchmarks (NFR-009).
  - Eval: recommendation relevance ≥ 80% (FR-044, NFR-014).
- **Definition of Done**
  - SLOs met on the reference set; lineage E2E test green; recommendations pass the eval gate.

---

### M12 — Reporting

- **Scope**
  - Six-day (Saturday boundary) aggregation (FR-045).
  - Detailed Automation Cards with architecture + evidence (FR-046).
  - "Why it matters" narrative, evidence-grounded (FR-047).
  - Domain/industry/technology heat maps (FR-048).
  - ECC-to-S/4 + clean-core flags in the executive section (FR-049).
  - PDF / HTML / JSON / CSV exports (FR-050).
  - Configurable recipients, filters, scoring weights, schedule per tenant (FR-051).
  - Atomic publish: incomplete report never published (NFR-002).
  - **Out of scope:** notification transport beyond the configured sender (wired in M16).
- **Dependencies:** M10 (scores), M11 (data), M03 (MinIO).
- **Acceptance criteria**
  - All sections present in every published report (FR-045, NFR-002).
  - Zero fabricated claims in narrative golden evals (FR-047, NFR-014).
  - All four exports parse and match fixtures (FR-050).
  - Report completes in < 30 min on the reference set (NFR-009).
  - Recipients/filters/weights respected per tenant (FR-051).
  - Failure → retry + alert; no partial publish (NFR-002).
- **Tests**
  - E2E: full Saturday report journey (FR-045, NFR-002).
  - Eval: narrative groundedness (FR-047, NFR-014).
  - Integration: export round-trip (FR-050).
  - Ops: atomicity — kill exporter → no partial report (NFR-002).
- **Definition of Done**
  - Report journey E2E green; exports verified; atomicity proven; < 30 min budget met.

---

### M13 — Workspace / Dashboard (Frontend)

- **Scope**
  - React + JavaScript (Vite SPA) app with 9 workspaces: Dashboard, Discovery, Automation, Architecture, Opportunity, Evidence, Reports, Governance, Administration (FR-052).
  - Data tables, EvidenceBadge, ScoreBadge, ArchitectureDiagram components ([11_Frontend_Architecture](./11_Frontend_Architecture.md)).
  - Health views (source/agent/queue/cost) (FR-055).
  - Accessibility (keyboard, contrast AA, no color-only meaning) + responsive ([19 §3](./19_Definition_of_Done.md)).
  - Auth integration (M02); RBAC-aware UI gating (FR-053).
  - **Out of scope:** server-side engines (M07–M12); design tokens beyond the existing system.
- **Dependencies:** M02 (auth), M04 (API), M07–M12 data APIs.
- **Acceptance criteria**
  - All 9 workspaces functional against the real API (FR-052).
  - Evidence/confidence never color-only; badges carry text labels (NFR-008).
  - Keyboard-navigable, contrast AA (docs/19 §3).
  - Health dashboards render live metrics (FR-055).
  - UI actions gated by role (FR-053).
- **Tests**
  - Unit: component behavior (DataTable, EvidenceBadge, ScoreBadge) (FR-052).
  - E2E: Discover / Evaluate / Report journeys with mocked + real API ([14 §5](./14_Testing_Strategy.md)).
  - Accessibility: axe + keyboard pass (docs/19 §3).
  - Component/viz regressions for heat maps and diagrams.
- **Definition of Done**
  - All 9 workspaces E2E green; accessibility pass; health dashboards live.

---

### M14 — Monitoring & Observability

- **Scope**
  - Prometheus scrape config + Grafana dashboards: source health, agent health, queue depth, DLQ, LLM cost, eval quality, job latency (FR-055, NFR-005).
  - Loki log aggregation correlated by `trace_id` (NFR-005).
  - Alerts + runbooks (FR-058).
  - Cost dashboards / budgets (NFR-012).
  - **Out of scope:** business UI (M13); deployment of stacks (M16).
- **Dependencies:** M04 instrumentation; metrics from M07–M10; M03 stores.
- **Acceptance criteria**
  - All services emit OTel → Prometheus/Loki, visible in Grafana (NFR-005).
  - Dashboards cover the 8 FR-055 signals (FR-055).
  - Alerts fire and runbooks are linked (FR-058).
  - Cost per source/agent/tenant tracked (NFR-012).
- **Tests**
  - Ops: metric emission for every service (NFR-005).
  - Ops: alert rule fires on an injected failure (FR-058).
  - Ops: budget breach triggers alert + tier downgrade (NFR-012).
- **Definition of Done**
  - Dashboards live; alert drill passed; cost ledger visible.

---

### M15 — Governance (Review + Policy + Audit)

- **Scope**
  - Review Queue: low-confidence + high-impact routing, reviewer decisions, feedback capture (FR-056; FR-059 groundwork).
  - Policy Decision Point: source/model allow-deny + per-tenant budget check ([21 §4.11](./21_AI_Layer_Specification.md)) — T0 deterministic, fail-closed.
  - Audit log for governed actions; prompt/model version registry + promotion workflow (FR-054).
  - Alert + runbook dispatch (FR-058).
  - Tenant isolation + least-privilege enforcement at every boundary (FR-057).
  - **Out of scope:** productization APIs (FR-063), continuous-learning loops (FR-059…064 → §7).
- **Dependencies:** M02 (RBAC), M05 (registry), M06 (hooks), M12 (reports), M14 (alerts).
- **Acceptance criteria**
  - Zero policy bypass across the golden adversarial suite (FR-053, FR-057, NFR-004).
  - 100% of denied actions produce an audit entry (FR-054).
  - Review items route by confidence × impact rules (FR-056).
  - Prompt/model promotion requires the eval gate (FR-054, NFR-014).
  - Budget/model-policy violations caught + alerted (NFR-012).
- **Tests**
  - Security: adversarial policy-bypass suite (FR-053, FR-057).
  - Contract: audit-log completeness (FR-054).
  - Integration: review-routing rules (FR-056).
  - Ops: budget breach → downgrade + alert (NFR-012).
- **Definition of Done**
  - Adversarial suite green; audit completeness verified; Review Queue live with the T0 governance policy backstop.

---

### M16 — Deployment & Environments

- **Scope**
  - Docker Compose for dev; production Docker deployment behind Nginx (TLS).
  - GitHub Actions CI/CD: build → push → deploy via SSH/docker-compose per environment (docs/12 §4).
  - `dev` / `staging` / `prod` overlays + secrets (SOPS / Docker secrets) (NFR-004).
  - Data-store backup/restore (pg_dump, MinIO, Qdrant snapshot, Neo4j) + DR drill (NFR-010).
  - Scaling knobs: worker replicas, vertical sizing (NFR-003).
  - Availability/uptime verification (NFR-010).
  - **Out of scope:** managed cloud — stack is self-hosted per [ADR-0014](./17_Architecture_Decision_Records/0014-cost-minimized-open-source-stack.md).
- **Dependencies:** M01; then M07–M15 as they land.
- **Acceptance criteria**
  - CI/CD deploys all services to dev/staging/prod (NFR-010).
  - Restart during the report window is safe; ingestion resilient via queues (NFR-010, NFR-007).
  - Backup/restore drill passes (NFR-010).
  - Worker scaling by replica verified (NFR-003).
- **Tests**
  - Ops: deploy pipeline green in all three environments (NFR-010).
  - Ops: restore-from-backup drill (NFR-010).
  - Performance: prod smoke within NFR-009 budget.
- **Definition of Done**
  - All environments deployed by CI; DR drill passed; runbooks documented.

---

## 6. Module Exit Gate (checklist applied to every module)

Before a module is declared done, in addition to its own DoD and [19 §2](./19_Definition_of_Done.md):

- [ ] All acceptance criteria met with evidence (test output linked in the PR).
- [ ] Every FR-/NFR- ID in the module's scope is at **In Progress → Done** in the [RTM](./16_Requirement_Traceability_Matrix.md).
- [ ] Test files carry the requirement IDs they verify (headers).
- [ ] New/changed API, schema, or UI behavior documented; no stale/orphaned docs.
- [ ] Observability (metrics/logs/traces) covers the new path.
- [ ] Tenant isolation verified where data access changed.
- [ ] Idempotency verified where a job/endpoint changed.
- [ ] docs/18 Project Memory and affected ADRs updated.

---

## 7. Extension Modules (Phase 15–16 — tracked, not yet detailed)

Detailed when Phase 15 approaches; listed here so the RTM stays fully covered.

| Module | Requirements | Depends on | Notes |
|---|---|---|---|
| **Continuous Learning** | FR-059 (reviewer feedback), FR-060 (benchmarks/golden sets), FR-061 (taxonomy evolution), NFR-014 (quality gates) | M15 (review feedback), M13 (UI), M05 (registry) | Feedback loop feeding golden sets; calibration with acceptance-rate trend. |
| **Customer Packs & Public API** | FR-062 (customer source packs + private spaces), FR-063 (opportunity/architecture retrieval APIs), FR-064 (recommendation layer) | M07, M11, M04 | Multi-tenant onboarding; versioned public API surface. |

---

## 8. Requirements Coverage

All 78 IDs (FR-001…064, NFR-001…014) in the [RTM](./16_Requirement_Traceability_Matrix.md) are assigned to a module above, except FR-059…064 which are tracked in §7 as Phase 15–16 extension modules. The cross-cutting NFRs (NFR-001, 003, 009, 010) are owned by specific modules (M11, M16, M11/M12/M16, M14/M16) and enforced as module-level checks in every build.
