# 04 — System Architecture

**Product:** SAP Automation Intelligence Engine (SAIE)
**Document status:** Baseline
**Related docs:** [05_AI_Architecture](./05_AI_Architecture.md) · [06_Agent_Architecture](./06_Agent_Architecture.md) · [10_Backend_Architecture](./10_Backend_Architecture.md) · [11_Frontend_Architecture](./11_Frontend_Architecture.md) · [12_DevOps_Architecture](./12_DevOps_Architecture.md)

---

## 1. Target-State Chain

```
Discover → Verify → Detect Change → Understand Automation → Reconstruct Architecture
→ Validate Opportunity → Score → Connect Knowledge → Report → Learn → Recommend What to Build
```

## 2. Logical Architecture (Layers)

```
┌──────────────────────────────────────────────────────────────────────┐
│                        Presentation Layer                             │
│        Next.js + TypeScript — Enterprise Intelligence Workspace        │
│  Dashboard · Discovery · Automation · Architecture · Opportunity ·     │
│  Knowledge · Reports · Governance · Administration                     │
└───────────────▲───────────────────────────────────────────────────────┘
                │ HTTPS / REST (typed API)
┌───────────────┴───────────────────────────────────────────────────────┐
│                         API Layer (FastAPI)                            │
│   Auth · Source mgmt · Findings · Automation · Architecture ·          │
│   Opportunity · Scoring · Search · Reports · Review · Admin            │
└───────────────▲───────────────────────────────────────────────────────┘
                │ internal event stream / commands
┌───────────────┴───────────────────────────────────────────────────────┐
│                        Agent Orchestration                             │
│    Orchestrator → typed agent contracts → workers                      │
│  Discovery | Evidence | Change | Automation | Architecture |           │
│  Opportunity | Scoring | Knowledge | Report | Review | Governance      │
└──────┬───────────────┬──────────────────────────────┬─────────────────┘
       │              │                               │
   Queue/Stream   LLM Gateway                  Deterministic services
  (Kafka/Redis)  (model-agnostic)            (parse, hash/diff, dedup,
       │                                        entity resolution, render)
       ▼
┌──────────────────────────────────────────────────────────────────────┐
│                         Data Layer                                     │
│  PostgreSQL (tx) · pgvector (semantic) · Neo4j (graph) ·              │
│  S3-compatible (snapshots/reports) · OpenSearch/PG-FTS (search)        │
└──────────────────────────────────────────────────────────────────────┘
```

## 3. Technology Stack (per TRD)

| Layer | Target technology | Purpose |
|---|---|---|
| Web UI | Next.js + TypeScript | Enterprise workspace |
| API | Python FastAPI | Typed service APIs |
| Agent orchestration | Workflow/orchestration framework | Controlled multi-agent execution |
| Workers | Python async workers | Crawl/enrich/report jobs |
| Database | PostgreSQL | Transactional metadata |
| Vector | pgvector / vector store | Semantic retrieval |
| Graph | Neo4j or graph model | Relationships |
| Object storage | S3-compatible | Snapshots / reports |
| Queue | Kafka / managed queue / Redis streams | Decoupled processing |
| Search | OpenSearch / PostgreSQL FTS | Search and facets |
| LLM | Enterprise model gateway | Extraction / reasoning |
| Observability | OpenTelemetry | Metrics / logs / traces |
| Deployment | Kubernetes / managed containers | Scalable services |
| Identity | OIDC/SAML-capable IdP | SSO / RBAC |

## 4. Container View

- **web** — Next.js app server (SSR + client), reverse-proxied.
- **api** — FastAPI service (typed REST), stateless, scales horizontally.
- **orchestrator** — drives the multi-agent pipeline ([06_Agent_Architecture](./06_Agent_Architecture.md)).
- **workers** — crawl, parse/normalize, hash/diff, LLM-enrich, report workers (independently scalable).
- **llm-gateway** — model-agnostic facade, versioned prompts, caching, budgets.
- **data stores** — Postgres (+pgvector), Neo4j, object storage, queue/stream, search.

## 5. Key Architectural Decisions (see [17_Architecture_Decision_Records](./17_Architecture_Decision_Records/README.md))

| Decision | Choice | Rationale |
|---|---|---|
| ADR-001 | Next.js + FastAPI | Mature, typed, large ecosystem for both layers |
| ADR-002 | Orchestration framework for agents | Controlled, auditable execution vs free-form multi-agent |
| ADR-003 | Model-agnostic LLM gateway | Avoids provider lock-in (NFR-13) |
| ADR-004 | Postgres + pgvector + Neo4j | Single tx DB; vector in-DB; graph for relationships |
| ADR-005 | Async event-driven, idempotent jobs | Decoupling, replay, recoverability (NFR-7) |
| ADR-006 | Deterministic preprocessing before LLM | Cost control + reliability (NFR-12, NFR-9) |

## 6. Data Flow — End to End

```
Scheduler ──▶ Acquisition ──▶ Parse/Normalize ──▶ Hash/Diff ──▶ Relevance
   ──▶ Deduplicate ──▶ Automation Extraction ──▶ Architecture ──▶ Evidence
   ──▶ Opportunity ──▶ Scoring ──▶ Knowledge Graph ──▶ Report ──▶ Notification
```

Each stage writes a persistent artifact before the next stage reads it; no stage invents facts not in its inputs ([06_Agent_Architecture](./06_Agent_Architecture.md) operating rule).

## 7. Deployment Topology (target)

- Kubernetes cluster (or managed containers) with separate namespaces for **app**, **workers**, **data**, and **observability**.
- Environments: `dev`, `staging`, `prod` with promotion gates ([12_DevOps_Architecture](./12_DevOps_Architecture.md)).
- Managed DB/object storage/queue in prod; containerized local equivalents in dev.

## 8. Cross-Cutting Concerns

- **Tenant isolation** at every query boundary (NFR-4).
- **Observability** via OpenTelemetry; cost per source/agent tracked (NFR-5, NFR-12).
- **Resilience** via queues, retries, DLQ, and runbooks (NFR-2).
- **Explanation** — scores and confidence always carry rationale (NFR-8).
