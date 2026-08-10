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
  (Redis Streams) (OpenAI primary /            (parse, hash/diff, dedup,
       │           Gemini fallback)             entity resolution, render)
       ▼
┌──────────────────────────────────────────────────────────────────────┐
│                         Data Layer                                     │
│  PostgreSQL (tx) · Qdrant (semantic) · Neo4j CE (graph) ·             │
│  MinIO (snapshots/reports) · Postgres FTS (search) · Redis (cache)     │
└──────────────────────────────────────────────────────────────────────┘
```

## 3. Technology Stack (per [ADR-0014](./17_Architecture_Decision_Records/0014-cost-minimized-open-source-stack.md))

| Layer | Target technology | Purpose |
|---|---|---|
| Web UI | Next.js + TypeScript | Enterprise workspace |
| API | Python FastAPI | Typed service APIs |
| Agent orchestration | LangGraph | Graph-based AI agent pipeline |
| Background jobs | Celery + Redis | Crawl/enrich/report jobs |
| Scheduler | APScheduler | Cron-equivalent scheduling |
| Database | PostgreSQL | Transactional metadata + full-text/faceted search |
| Vector | Qdrant (self-hosted) | Semantic retrieval |
| Graph | Neo4j Community | Relationships / knowledge graph |
| Object storage | MinIO | Snapshots / reports (S3-compatible) |
| Cache + Queue | Redis | Cache + Redis Streams |
| Search | PostgreSQL FTS | Search and facets |
| LLM | OpenAI (primary) / Gemini (fallback) via gateway | Extraction / reasoning |
| Observability | OTel → Prometheus + Grafana + Loki | Metrics / logs / traces |
| Deployment | Docker + Nginx + GitHub Actions | Containers, TLS, CI/CD |
| Identity | Keycloak (self-hosted) | OIDC / SSO / RBAC |

## 4. Container View

- **web** — Next.js app server (SSR + client), reverse-proxied behind Nginx.
- **api** — FastAPI service (typed REST), stateless, scales horizontally.
- **celery-workers** — crawl, parse/normalize, hash/diff, LLM-enrich, report workers ([06_Agent_Architecture](./06_Agent_Architecture.md)).
- **langgraph-orchestrator** — drives the multi-agent pipeline, state in Redis.
- **llm-gateway** — model-agnostic facade (OpenAI primary / Gemini fallback), versioned prompts, caching, budgets.
- **data stores** — Postgres, Qdrant, Neo4j CE, MinIO, Redis (cache + streams).
- **observability** — Prometheus, Grafana, Loki (OTel-instrumented apps).
- **identity** — Keycloak (self-hosted OIDC).

## 5. Key Architectural Decisions (see [17_Architecture_Decision_Records](./17_Architecture_Decision_Records/README.md))

| Decision | Choice | Rationale |
|---|---|---|
| ADR-001 | Next.js + FastAPI | Mature, typed, large ecosystem for both layers |
| ADR-002 | Orchestration framework for agents | Controlled, auditable execution vs free-form multi-agent |
| ADR-003 | Model-agnostic LLM gateway | Avoids provider lock-in (NFR-13) |
| ADR-004 | Postgres + Neo4j + MinIO (amended: Qdrant for vectors) | Single tx DB; vector store; graph for relationships |
| ADR-005 | Async event-driven, idempotent jobs | Decoupling, replay, recoverability (NFR-7) |
| ADR-006 | Deterministic preprocessing before LLM | Cost control + reliability (NFR-12, NFR-9) |
| ADR-014 | Cost-minimized open-source stack (locked) | Near-zero licensing cost; Docker + self-hosted stores; OpenAI/Gemini via gateway |

## 6. Data Flow — End to End

```
Scheduler ──▶ Acquisition ──▶ Parse/Normalize ──▶ Hash/Diff ──▶ Relevance
   ──▶ Deduplicate ──▶ Automation Extraction ──▶ Architecture ──▶ Evidence
   ──▶ Opportunity ──▶ Scoring ──▶ Knowledge Graph ──▶ Report ──▶ Notification
```

Each stage writes a persistent artifact before the next stage reads it; no stage invents facts not in its inputs ([06_Agent_Architecture](./06_Agent_Architecture.md) operating rule).

## 7. Deployment Topology (target)

- Docker Compose for local dev and single-node deployment (all services as containers).
- Production on any Docker-capable host behind **Nginx** (TLS termination), provisioned via **GitHub Actions** CI/CD.
- Environments: `dev`, `staging`, `prod` with promotion gates ([12_DevOps_Architecture](./12_DevOps_Architecture.md)).
- Scaling is vertical or manual horizontal; data stores run single-node (Qdrant/Neo4j CE HA requires manual clustering — see [ADR-0014](./17_Architecture_Decision_Records/0014-cost-minimized-open-source-stack.md)).

## 8. Cross-Cutting Concerns

- **Tenant isolation** at every query boundary (NFR-4).
- **Observability** via OpenTelemetry; cost per source/agent tracked (NFR-5, NFR-12).
- **Resilience** via queues, retries, DLQ, and runbooks (NFR-2).
- **Explanation** — scores and confidence always carry rationale (NFR-8).
