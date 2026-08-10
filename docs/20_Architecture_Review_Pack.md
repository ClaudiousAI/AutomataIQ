# 20 — Architecture Review Pack

**Product:** SAP Automation Intelligence Engine (SAIE)
**Document status:** ✅ **Approved** — 2026-08-10 by Ganesh
**Created:** 2026-08-10
**Approved:** 2026-08-10
**Detailed design docs:** `docs/04–13` (full specifications)

> **Purpose:** This document consolidates every architectural decision across the12 concerns listed in the implementation brief into a single review artifact. Once approved, implementation may begin. No code is written against any concern until its section here is signed off.

---

## Approval Gate

| Concern | Owner | Status | Notes |
|---|---|---|---|
| 1. Overall System Architecture | Ganesh | ✅ Approved | [04_System_Architecture](./04_System_Architecture.md) |
| 2. AI Architecture | Ganesh | ✅ Approved | [05_AI_Architecture](./05_AI_Architecture.md) |
| 3. Agent Architecture | Ganesh | ✅ Approved | [06_Agent_Architecture](./06_Agent_Architecture.md) |
| 4. Database Schema | Ganesh | ✅ Approved | [07_Database_Design](./07_Database_Design.md) |
| 5. APIs | Ganesh | ✅ Approved | [08_API_Design](./08_API_Design.md) |
| 6. Background Workers | Ganesh | ✅ Approved | [10_Backend_Architecture](./10_Backend_Architecture.md) |
| 7. Scheduler Design | Ganesh | ✅ Approved | Section 7 below (consolidated) |
| 8. Queue Architecture | Ganesh | ✅ Approved | Section 8 below (consolidated) |
| 9. Error Handling | Ganesh | ✅ Approved | Section 9 below (consolidated) |
| 10. Security | Ganesh | ✅ Approved | [13_Security_Architecture](./13_Security_Architecture.md) |
| 11. Deployment | Ganesh | ✅ Approved | [12_DevOps_Architecture](./12_DevOps_Architecture.md) |
| 12. Monitoring | Ganesh | ✅ Approved | [12_DevOps_Architecture](./12_DevOps_Architecture.md) |

**Rule: No implementation begins until the status column above reads ✅ Approved for every row.**

**Approval granted:** all 12 concerns approved by **Ganesh** on **2026-08-10** with no conditions. Implementation may begin per [15_Project_Roadmap](./15_Project_Roadmap.md), starting with Phase 2 (Platform Foundation). The 8 open decisions (OD-1…OD-8) in §Open Decisions below must be settled before Phase 2 coding begins.

---

## 1. Overall System Architecture

**Full design:** `docs/04_System_Architecture.md`

### Decision Summary

SAIE is a **layered, event-driven, multi-service** platform. The system has four logical layers:

```
Presentation (Next.js + TypeScript)
       ↕ HTTPS
API (FastAPI — typed REST)
       ↕ internal events
Agent Orchestration → LLM Gateway → Workers
       ↕
Data Layer (Postgres + pgvector + Neo4j + S3 + Queue + Search)
```

### Key Choices

| Concern | Decision | Rationale |
|---|---|---|
| UI framework | Next.js + TypeScript (App Router) | Mature, typed, SSR + client |
| API framework | Python FastAPI + Pydantic | Typed contracts, OpenAPI-generated, Python ecosystem |
| Worker language | Python async | Shared domain logic with API layer |
| LLM gateway | Model-agnostic, pluggable adapters | No provider lock-in (NFR-13) |
| State management | Server-side (Postgres) + minimal client state | Enterprise data, not SPA state |

### Architecture Decision Record
- **ADR-0001** — Next.js + FastAPI stack: `docs/17/0001-nextjs-fastapi-stack.md`

### Open Questions
- Concrete Next.js component library choice (shadcn/ui, Radix, internal) — deferred to Phase 10 UI build.
- Next.js hosting mode (Vercel, self-hosted Node, container) — deferred to Phase 2 environment setup.

---

## 2. AI Architecture

**Full design:** `docs/05_AI_Architecture.md`

### Decision Summary

Every AI stage follows three principles: **evidence-first** (no unlinked claims), **deterministic preprocessing first** (cheap code runs before any model call), and **human-in-the-loop** for high-impact decisions.

### Key Choices

| Concern | Decision | Rationale |
|---|---|---|
| LLM gateway | Single model-agnostic facade | Provider swap is config, not code |
| Model routing | Tiered by task (cheap → capable) | Cost control (NFR-12); cheap classification, expensive reconstruction |
| Prompt versioning | Immutable versions; (model, prompt_version, model_version) stored per run | Reproducibility, regression gating (NFR-6) |
| Structured output | JSON Schema validation; invalid → retry or review | No silent hallucinated output accepted |
| Caching | Prompt-response + extraction-level; unchanged content skips model | Deterministic preprocessing gates cost (NFR-12) |
| Hallucination control | Confirmed/inferred/speculative labels; evidence links required; low confidence → review | Trust model: never present inference as fact |

### Architecture Decision Records
- **ADR-0003** — Model-agnostic LLM gateway: `docs/17/0003-model-agnostic-llm-gateway.md`
- **ADR-0006** — Deterministic preprocessing first: `docs/17/0006-deterministic-preprocessing-first.md`
- **ADR-0007** — Evidence-first with fact labeling: `docs/17/0007-evidence-first-fact-labeling.md`

### Open Questions
- Concrete LLM providers and which tiers map to which models — deferred to Phase 3 data foundation (when gateway is built).
- Embedding model for pgvector — deferred to Phase 3.

---

## 3. Agent Architecture

**Full design:** `docs/06_Agent_Architecture.md`

### Decision Summary

Agents are driven by an **orchestration framework** (not ad-hoc multi-agent loops). Every agent communicates through **typed contracts and persistent artifacts** — never direct chat. Three hard rules: no fact invention, no production deployment, no governance bypass.

### The11 Agents

| Agent | Input → Output |
|---|---|
| Discovery | Scheduler signal → candidate items |
| Evidence | Candidate items → evidence package |
| Change | Evidence package → change record |
| Automation | Change record → Automation Card |
| Architecture | Change + evidence → architecture graph |
| Opportunity | Architecture + card → opportunity assessment |
| Scoring | Opportunity → score + rationale |
| Knowledge | All entities → relationships, entity resolution |
| Report | Aggregated data → PDF / HTML / JSON |
| Review | Low-confidence / high-impact items → review queue |
| Governance | All actions → audit / policy enforcement |

### Pipeline Flow
```
Scheduler → Acquisition → Parse → Normalize → Hash/Diff → Relevance
→ Deduplicate → Automation Extraction → Architecture → Evidence
→ Opportunity → Scoring → Knowledge Graph → Report → Notification
```

### Key Choices

| Concern | Decision | Rationale |
|---|---|---|
| Orchestration | Workflow/durable-execution framework | Survives restarts, defines gates, auditable |
| Agent I/O | Typed JSON envelope with `input_refs` / `output_artifacts` | Schema-validated, replayable |
| Human-in-the-loop | Review gate on low confidence + high impact | Safety (PRD out-of-scope: "unreviewed claims") |
| Failure handling | Retry → fallback model → needs_review → DLQ | No silent drops; DLQ surfaces failures |

### Architecture Decision Record
- **ADR-0002** — Orchestration framework: `docs/17/0002-agent-orchestration-framework.md`

### Open Questions
- Concrete orchestration engine (Temporal, Prefect, Airflow, custom) — open for Phase 2 platform foundation decision. The contract is engine-agnostic.

---

## 4. Database Schema

**Full design:** `docs/07_Database_Design.md`

### Decision Summary

PostgreSQL is the **system of record** with row-level security for tenant isolation. pgvector provides in-database semantic embeddings. Neo4j holds the knowledge graph (cross-domain, multi-hop, lineage). S3-compatible storage holds snapshots and report blobs.

### The16 Tables (entity summary)

```
tenants → users
tenants → sources → crawl_runs → source_versions → changes → findings
findings → automations → architecture_nodes → architecture_edges
findings → evidence
automations → opportunities → scores
tenants → reports → report_items → findings
users → reviews, audit_log
agent_runs → audit_log
```

### Key Choices

| Concern | Decision | Rationale |
|---|---|---|
| Primary store | PostgreSQL | Transactional integrity, row-level security, pgvector |
| Vector search | pgvector (in Postgres) | No second system for embeddings; consistency |
| Graph store | Neo4j | First-class multi-hop relationship queries |
| IDs | ULID / UUIDv7 | Global ordering; human-safe slugs for canonical keys |
| Soft delete | Governed entities only | Audit trail preserved |
| Migrations | Alembic (forward-only) | Version-controlled schema evolution |

### Architecture Decision Record
- **ADR-0004** — Postgres + pgvector + Neo4j: `docs/17/0004-postgres-pgvector-neo4j.md`

### Open Questions
- Neo4j hosting mode (managed vs self-hosted container) — Phase 3.
- OpenSearch vs Postgres FTS — deferred; Postgres FTS is the default; revisit if faceted-search SLOs aren't met.

---

## 5. APIs

**Full design:** `docs/08_API_Design.md`

### Decision Summary

REST over HTTPS, JSON, typed schemas via FastAPI + Pydantic, OpenAPI auto-generated. All endpoints are **tenant-scoped** (tenant derived from authenticated principal, never from the client).

### Key API Groups

| Group | Endpoints |
|---|---|
| Sources | CRUD, trigger crawl, health |
| Findings | List/filter, detail, canonical view |
| Automations | Cards, types, taxonomy |
| Architecture | Graph, diagrams, summaries |
| Opportunities | Backlog, detail, scores, override |
| Knowledge/Search | Semantic + facets, graph queries, recommendations |
| Reports | Generate, export, detail |
| Governance | Review queue, decisions, audit |
| Admin/Health | Users, sources, schedules, agents, models, queues, cost |

### Key Choices

| Concern | Decision | Rationale |
|---|---|---|
| Pagination | Cursor-based (opaque `next_cursor` + `limit`) | Stable for large/evolving datasets |
| Errors | RFC 7807 `problem+json` | Standard, machine-readable |
| Versioning | URL versioning (`/api/v1`) | Simple, explicit |
| Idempotency | Header-based (`Idempotency-Key`) on mutating job endpoints | Safe retries (NFR-7) |
| RBAC | Server-side enforced; 7 roles | Least privilege; client guards are UX only |
| Events | Versioned schemas; consumers tolerate forward | Decoupled, evolvable |

### Open Questions
- GraphQL or gRPC for internal agent→API communication (not user-facing) — default: REST; revisit if performance demands.

---

## 6. Background Workers

**Full design:** `docs/10_Backend_Architecture.md`

### Decision Summary

Workers are **independently scalable** Python async services, decoupled from the API via the queue/stream layer. Each worker type handles one stage of the pipeline.

### Worker Types

| Worker | Responsibility | Trigger |
|---|---|---|
| `worker-crawl` | Acquisition (HTML/RSS/API/doc), parse/normalize, hash | Scheduler (per-source schedule) |
| `worker-enrich` | Diff, relevance, dedup, LLM extraction, architecture | Queue (from crawl) |
| `worker-report` | Saturday aggregation, render, export, notify | Scheduler (Saturday boundary) |
| `llm-gateway` | Model-agnostic LLM facade (called by enrich) | Internal (sync/async) |

### Key Choices

| Concern | Decision | Rationale |
|---|---|---|
| Scaling model | Horizontal; scale on queue depth + CPU | Independent scaling per worker type |
| Job model | Idempotent, replayable, keyed by `run_id` | Recoverability (NFR-7) |
| Failure policy | Retry with backoff → fallback model → needs_review → DLQ | No silent failures |
| Worker-to-API boundary | Typed Pydantic contracts; no direct DB coupling between worker and API | Maintainability |

---

## 7. Scheduler Design

### Decision Summary

Scheduling is **per-source** (not a single global cron), with a **Saturday reporting boundary**.

### Components

```
┌───────────────────────────────────────────────────┐
│                  Scheduler Service                 │
│  · reads source.schedule (cron per source)        │
│  · emits SourceCrawlRequest events                 │
│  · respects tier priority (Tier 1–6)               │
│  · Saturday 00:00 UTC closes the reporting window  │
│  · Saturday run aggregates the past 6 days          │
└───────────┬───────────────────────────────────────┘
            ▼ (events to queue)
    worker-crawl workers consume
```

### Key Behaviors

| Behavior | Design |
|---|---|
| Per-source schedule | Cron expression stored in `sources.schedule`; scheduler emits events on match |
| Saturday boundary | Saturday 00:00 UTC is the hard cutoff; `reporting_week` is the prior 6 days |
| Saturday report job | Separate scheduled event on Saturday morning; aggregates the closed window |
| Source health | If a source fails N consecutive crawls, scheduler marks it unhealthy and alerts |
| Pause/resume | `sources.active = false` stops the scheduler from emitting for that source |
| Catch-up | If the scheduler was down, missed runs are not replayed (each source has `last_crawl_at`; gap is reported, not silently backfilled) |

---

## 8. Queue Architecture

**Full design:** `docs/04_System_Architecture.md` (data flow), `docs/10_Backend_Architecture.md` (failure policy)

### Decision Summary

A **managed queue/stream** (Kafka, Redis Streams, or cloud equivalent) decouples all pipeline stages. Every message is a typed, versioned event.

### Queue Topology

| Topic/Stream | Producer | Consumer | Purpose |
|---|---|---|---|
| `source.crawl.request` | Scheduler | worker-crawl | Trigger crawl for a source |
| `source.version.created` | worker-crawl | worker-enrich | New version available for analysis |
| `change.classified` | worker-enrich | worker-enrich (next stage) | Change record ready for extraction |
| `finding.promoted` | worker-enrich | worker-enrich / Knowledge | Finding meets confidence threshold |
| `report.generate` | Scheduler (Saturday) | worker-report | Trigger Saturday report |
| `report.ready` | worker-report | Notification service | Report available |
| `review.queue` | worker-enrich / Review agent | Governance / Human | Items needing review |
| `dlq.*` (per-topic) | Workers (on repeated failure) | Operations / Alerting | Failed messages for investigation |

### Key Choices

| Concern | Decision | Rationale |
|---|---|---|
| Message format | JSON with `event`, `version`, `tenant_id`, payload | Typed contracts; versioned for forward-compat |
| Ordering | Per-source ordering guaranteed (partition by `source_id`) | Sequential processing of a source's versions |
| Retention | Configurable per topic; raw events retained for audit | Replay capability; lineage (NFR-7) |
| DLQ | Per-topic dead-letter queues; alert on new DLQ messages | Operational visibility (FR-C09-4) |
| Idempotency | Consumers check `run_id` to avoid reprocessing | Exactly-once semantics where needed |
| Backpressure | Workers scale on queue depth; DLQ prevents poison messages from blocking | Scalability (NFR-3) |

---

## 9. Error Handling

### Decision Summary

Errors are handled **per-stage** with a uniform policy. No stage silently swallows errors; no stage lets a bad output propagate downstream.

### Error Policy (applies to every worker stage)

```
Error occurs
  ↓
Retry (exponential backoff, max N retries)
  ↓ (if retries exhausted)
Fallback model (for LLM stages only; deterministic stages → skip)
  ↓ (if fallback fails or no fallback)
Route to Review Queue (needs_review status)
  ↓ (if not reviewable)
Dead-letter queue + alert
```

### Error Classes

| Error class | Response |
|---|---|
| Transient (network, rate limit, 5xx) | Retry with backoff; alert after N retries |
| Permanent (bad input, schema violation) | Log + quarantine; do not retry |
| LLM failure (timeout, invalid output) | Retry → fallback model → needs_review |
| Crawler failure (unavailable source) | Retry with backoff → mark source unhealthy → alert |
| Parser failure (changed page structure) | Quarantine parser result; alert; source marked unhealthy |
| Report failure | Retry → alert; **never publish incomplete report** |
| Schema validation failure (contract violation) | Consumer rejects message → DLQ |
| Tenant isolation violation | Deny + audit log + alert |

### Key Design Choices

| Concern | Decision | Rationale |
|---|---|---|
| DLQ visibility | Alert on new DLQ message; DLQ is not silently drained | Operational safety |
| Report atomicity | Report is complete or not published (atomic) | Never publish partial intelligence |
| Conflicting sources | Retain claims, reduce confidence (not silent merge) | Honest evidence model |
| Duplicate findings | Merge under canonical key, preserve evidence trail | ≥ 90% dedup (PRD metric) |

---

## 10. Security

**Full design:** `docs/13_Security_Architecture.md`

### Decision Summary

Defense in depth: SSO (OIDC/SAML), RBAC (7 roles), tenant isolation at every query boundary, encrypted secrets, full audit, and crawler policy compliance as a security boundary.

### Security Architecture Summary

| Layer | Control |
|---|---|
| Identity | OIDC/SAML IdP; session tokens |
| Authorization | RBAC: platform_admin, tenant_admin, architect, analyst, reviewer, executive, read_only |
| Tenant isolation | `tenant_id` scoping on every query; Postgres row-level security as backstop |
| Secrets | KMS-backed secret manager; never in code, DB, or logs |
| Audit | Immutable `audit_log` for all governed actions |
| Source compliance | Crawler policy module: robots.txt, terms, rate limits, auth boundaries |
| Data protection | Versioned snapshots; retention policy; content never used for training |
| Supply chain | SBOM, dependency scanning, SAST in CI |
| Prompt injection | Ingested content is data, not instructions; extraction contracts isolate data from control |

### Open Questions
- Concrete IdP choice (Auth0, Keycloak, cloud-native) — Phase 2 platform foundation.
- DAST tool choice — Phase 14 production hardening.

---

## 11. Deployment

**Full design:** `docs/12_DevOps_Architecture.md`

### Decision Summary

Kubernetes (or managed containers) with separate namespaces. Three environments: `dev`, `staging`, `prod`. Infrastructure as code. Promotion gated by CI + eval quality gates.

### Deployment Topology

```
┌──────────────────────────────────────────────┐
│  Kubernetes Cluster (or managed containers)  │
│                                              │
│  namespace: app                              │
│    web (Next.js)  ·  api (FastAPI)           │
│    orchestrator   ·  llm-gateway             │
│                                              │
│  namespace: workers                          │
│    worker-crawl  ·  worker-enrich            │
│    worker-report                             │
│                                              │
│  namespace: data                             │
│    (managed Postgres, Neo4j, S3, queue,      │
│     search — not in-cluster for prod)        │
│                                              │
│  namespace: observability                    │
│    metrics · logs · traces (OTel stack)      │
└──────────────────────────────────────────────┘
```

### Pipeline (promotion gates)

```
PR → CI (lint/tests/build/scan) → staging deploy → eval gates → prod deploy
```

- Web/API: blue-green or canary deployment
- Workers: rolling deploy with drain (graceful shutdown, idempotent jobs make this safe)
- Data stores: managed services (prod); containerized (dev/staging)

### Open Questions
- Concrete cloud provider and managed services — Phase 2.
- Helm vs Kustomize — Phase 2.

---

## 12. Monitoring

**Full design:** `docs/12_DevOps_Architecture.md` (observability stack), `docs/05_AI_Architecture.md` (cost controls)

### Decision Summary

OpenTelemetry for all services. Metrics, logs, and traces correlated by `trace_id`. Dashboards cover five operational concerns. Alerts with runbooks.

### Dashboards

| Dashboard | What it shows | Alert triggers |
|---|---|---|
| Source Health | Per-source: last crawl, status, error count, latency | Source unhealthy (N consecutive failures) |
| Agent Health | Per-agent: runs, success/fail, retry count, latency | High failure rate; unusual latency |
| Queue & DLQ | Queue depth, DLQ size, consumer lag | DLQ message appears; queue depth exceeds threshold |
| LLM Cost | Per-source, per-agent, per-tenant cost; budget utilization | Budget threshold breach; cost spike |
| Eval Quality | Golden-set metrics (precision, recall, dedup, usefulness) | Metric drops below PRD threshold |

### Observability Contract

| Signal | Standard |
|---|---|
| Metrics | OTel SDK → Prometheus (or cloud equivalent) |
| Logs | Structured JSON; correlation via `trace_id` |
| Traces | OTel spans per job stage; propagated through queue |
| Alerts | Pager/Slack/integration; every alert type linked to a runbook |
| Runbooks | Stored in `docs/` or ops wiki; linked in alert configuration |

---

## Cross-Cutting: End-to-End Data Flow

```
Scheduler ──▶ Acquisition ──▶ Parse/Normalize ──▶ Hash ──▶ Diff
   ──▶ Relevance ──▶ Deduplicate ──▶ Automation Extraction
   ──▶ Architecture ──▶ Evidence ──▶ Opportunity ──▶ Scoring
   ──▶ Knowledge Graph ──▶ Report ──▶ Notification
```

Each stage writes a **durable artifact** before the next reads it. The orchestrator drives the flow; agents communicate through the queue. The system is **eventually consistent** per finding (as agents complete their stage) and **consistently atomic** per report (Saturday report is all-or-nothing).

---

## Open Decisions — All Resolved (OD-1…OD-8)

**Status: ✅ all 8 resolved by Ganesh on 2026-08-10, recorded as ADRs 0008–0013.**

| # | Decision | Decision | Phase target | ADR |
|---|---|---|---|---|
| OD-1 | Orchestration engine | **Temporal** | 2 | [0009](./17_Architecture_Decision_Records/0009-temporal-orchestration-engine.md) |
| OD-2 | Identity / SSO provider | **Keycloak** (cloud-agnostic, on EKS) | 2 | [0010](./17_Architecture_Decision_Records/0010-keycloak-identity-provider.md) |
| OD-3 | Cloud provider + managed services | **AWS** | 2 | [0008](./17_Architecture_Decision_Records/0008-aws-cloud-platform.md) |
| OD-4 | K8s manifests | **Helm** | 2 | [0008](./17_Architecture_Decision_Records/0008-aws-cloud-platform.md) |
| OD-5 | Faceted search | **Postgres FTS** (escape hatch: OpenSearch) | 3 | [0012](./17_Architecture_Decision_Records/0012-search-embeddings-postgres-bedrock.md) |
| OD-6 | Embedding model for pgvector | **Bedrock-hosted** (Titan / Cohere) | 3 | [0012](./17_Architecture_Decision_Records/0012-search-embeddings-postgres-bedrock.md) |
| OD-7 | Next.js hosting model | **Container in EKS** | 2 | [0011](./17_Architecture_Decision_Records/0011-frontend-container-hosting.md) |
| OD-8 | DAST tool | **OWASP ZAP** | 14 | [0013](./17_Architecture_Decision_Records/0013-dast-owasp-zap.md) |

---

## Approval

Once all12 concerns are approved, update the summary table at the top of this document to ✅ **Approved** and record the approver, date, and any conditions. Then implementation may begin — starting with Phase 2 (Platform Foundation) per `docs/15_Project_Roadmap.md`.

| Concern | Approver | Date | Conditions |
|---|---|---|---|
| 1. Overall System Architecture | Ganesh | 2026-08-10 | None |
| 2. AI Architecture | Ganesh | 2026-08-10 | None |
| 3. Agent Architecture | Ganesh | 2026-08-10 | None |
| 4. Database Schema | Ganesh | 2026-08-10 | None |
| 5. APIs | Ganesh | 2026-08-10 | None |
| 6. Background Workers | Ganesh | 2026-08-10 | None |
| 7. Scheduler Design | Ganesh | 2026-08-10 | None |
| 8. Queue Architecture | Ganesh | 2026-08-10 | None |
| 9. Error Handling | Ganesh | 2026-08-10 | None |
| 10. Security | Ganesh | 2026-08-10 | None |
| 11. Deployment | Ganesh | 2026-08-10 | None |
| 12. Monitoring | Ganesh | 2026-08-10 | None |
