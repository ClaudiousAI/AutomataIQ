# ADR-0014 — Locked Cost-Minimized Open-Source Technology Stack

**Status:** Accepted
**Date:** 2026-08-10
**Supersedes:** ADR-0008 (AWS cloud), ADR-0009 (Temporal orchestration), ADR-0011 (container hosting), ADR-0012 (Bedrock embeddings)
**Amends:** ADR-0004 (pgvector replaced by Qdrant)
**Related:** [04_System_Architecture](../04_System_Architecture.md) · [10_Backend_Architecture](../10_Backend_Architecture.md) · [15_Project_Roadmap](../15_Project_Roadmap.md)

## Context

The prior stack locked cloud-managed services (AWS EKS, RDS, Bedrock, ECR) to minimize operational complexity. The overriding goal is now to **minimize ongoing licensing and cloud costs** while retaining a production-capable, enterprise-grade stack. This ADR locks the technology stack once so the team builds against a stable foundation, and supersedes the four ADRs that made cloud-vendor-specific choices.

## Decision

Lock the following open-source stack. No technology is changed unless a compelling technical reason is documented and approved as a new ADR.

### Application

| Layer | Technology | Rationale |
|---|---|---|
| Frontend | **React (JavaScript)** | Professional, fluid, ultra-smooth UX; single-runtime, no SSR overhead; component-driven with modern hooks; built via Vite. |
| API | **Python FastAPI** + Pydantic | Unchanged from ADR-0001; typed contracts, OpenAPI. |
| Background jobs | **Celery** + Redis backend | Mature, Python-native, well-understood, free. Replaces ad-hoc async workers. |
| Scheduler | **APScheduler** | Lightweight, Python-native, no external dependency. Replaces cron or managed scheduler. |
| AI orchestration | **LangGraph** | Graph-based agent workflow; replaces Temporal (ADR-0009). Lower ops overhead; state is in Redis. |

### Data stores

| Store | Technology | Rationale |
|---|---|---|
| Transactional database | **PostgreSQL** (system of record) | Unchanged from ADR-0004. |
| Vector database | **Qdrant** (self-hosted) | Replaces pgvector (ADR-0004, ADR-0012). Better recall/performance at scale; runs as a single Docker container. |
| Knowledge graph | **Neo4j Community Edition** | Free edition of ADR-0004 choice; sufficient for the entity-relationship model. |
| Object storage | **MinIO** | S3-compatible, self-hosted, no cloud dependency. Stores snapshots, reports, artifacts. |
| Cache + Queue | **Redis** (cache + Redis Streams) | Single technology for caching and message queuing (replaces Kafka). Replaces managed queue from ADR-0012. |

### Search

| Store | Technology | Rationale |
|---|---|---|
| Full-text + faceted search | **PostgreSQL FTS** | Unchanged from ADR-0012; runs inside the existing Postgres instance. |

### Observability

| Signal | Technology | Rationale |
|---|---|---|
| Metrics | **Prometheus** | Pull-based metrics; pairs with Grafana. Replaces managed Prometheus. |
| Dashboards | **Grafana** | Dashboards for agent health, source health, queue depth, LLM cost, eval quality. |
| Logging | **Loki** | Log aggregation; lightweight, no full-text indexing cost. |
| Traces | **OpenTelemetry** (SDK) → Prometheus/Grafana | OTel instrumentation stays; backends are now self-hosted. |

### Infrastructure

| Layer | Technology | Rationale |
|---|---|---|
| Containers | **Docker** + Docker Compose | Local dev and single-node deployment. Replaces EKS (ADR-0008). |
| Reverse proxy | **Nginx** | Routes frontend, API; terminates TLS in production. |
| CI/CD | **GitHub Actions** | Builds, tests, pushes images; deploys via SSH/docker-compose on target host. |

### LLM Providers

| Provider | Role | Rationale |
|---|---|---|
| **OpenAI** | Primary model (GPT-4o / GPT-4o-mini) | Best quality/cost ratio for structured extraction and reasoning. |
| **Gemini** (Google) | Fallback / fallback-tier model | Second provider for model-agnostic gateway (ADR-0003). Resilience against single-provider outage. |

Both are routed through the **LLM Gateway** (ADR-0003): no agent calls a provider directly. Prompt and response caching (ADR-0006) eliminates redundant calls.

### Identity (retained)

| Layer | Technology | Rationale |
|---|---|---|
| Identity provider | **Keycloak** (self-hosted) | Unchanged from ADR-0010. OIDC/SAML; runs as a Docker container. |

---

## What Changed vs Prior ADRs

| Prior ADR | Before | After |
|---|---|---|
| ADR-0008 | AWS (EKS, RDS, S3, Bedrock) | Self-hosted Docker + MinIO + OpenAI/Gemini |
| ADR-0009 | Temporal (orchestration) | LangGraph (AI orchestration) + Celery (jobs) |
| ADR-0011 | Container in EKS | Docker Compose (dev) / Docker (prod) |
| ADR-0012 | Postgres FTS + Bedrock embeddings | Postgres FTS + Qdrant + OpenAI embeddings |
| ADR-0004 | pgvector (in-Postgres vectors) | Qdrant (separate vector DB) |

**ADR-0001** (React (JavaScript) + FastAPI; Web UI portion amended by [ADR-0015](./0015-react-javascript-frontend.md)), **ADR-0002** (typed contracts + artifacts), **ADR-0003** (model-agnostic gateway), **ADR-0005** (idempotent jobs), **ADR-0006** (deterministic-first), **ADR-0007** (evidence-first), **ADR-0010** (Keycloak), **ADR-0013** (ZAP) — all **unchanged and still Accepted**.

## Consequences
### Positive
- **Near-zero infrastructure licensing cost.** All data stores, orchestration, observability, and tools are open-source and self-hosted.
- **Simpler local dev.** `docker compose up` brings up the full stack (Postgres, Redis, Qdrant, Neo4j, MinIO, Keycloak, Nginx) without cloud credentials.
- **Portable.** No cloud-specific code; deployment target is any Docker-capable host.
- **Model-agnostic.** OpenAI primary + Gemini fallback via the LLM Gateway (ADR-0003); swapping providers is configuration.
- **Lower ops ceiling.** No Kubernetes cluster to manage; Docker is operationally simpler for the current team size.
### Negative / Trade-offs
- **LLM API cost remains.** OpenAI/Gemini are usage-priced; mitigated by prompt caching, tiered routing, and deterministic gating (ADR-0006), but not zero.
- **Manual scaling.** Docker-based deployment scales vertically or by manual horizontal scaling, not autoscaling; acceptable at current load projections.
- **No vector-DB replication.** Qdrant single-node has no built-in HA; acceptable for dev/staging; prod HA requires manual Qdrant cluster or snapshot restore.
- **Neo4j Community limits.** No clustering; acceptable for the current graph size.
### Neutral
- All versioned contracts (typed I/O, prompt versions, golden sets) are unchanged; only the underlying technology changed.
- The AI Layer Specification (docs/21) is technology-agnostic in its agent contracts and prompt templates; no agent prompt changes are needed.
