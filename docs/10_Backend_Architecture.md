# 10 — Backend Architecture

**Product:** SAP Automation Intelligence Engine (SAIE)
**Document status:** Finalized — implementation-ready backend architecture
**Related docs:** [04_System_Architecture](./04_System_Architecture.md) · [06_Agent_Architecture](./06_Agent_Architecture.md) · [07_Database_Design](./07_Database_Design.md) · [08_API_Design](./08_API_Design.md) · [12_DevOps_Architecture](./12_DevOps_Architecture.md) · [21_AI_Layer_Specification](./21_AI_Layer_Specification.md)
**ADR refs:** 0001 (FastAPI API), 0003 (LLM gateway), 0005 (idempotent jobs), 0006 (deterministic-first), 0007 (evidence-first), 0014 (locked stack: LangGraph + Celery + APScheduler + Redis Streams + Qdrant + MinIO)

---

## 1. Services

| Service | Runtime | Responsibility |
|---|---|---|
| `api` | FastAPI (Python) | Typed REST surface; auth; RBAC; validation |
| `orchestrator` | Python (LangGraph) | Drives multi-agent pipeline; state in Redis |
| `worker-crawl` | Python (Celery) | Acquisition (HTML/RSS/API/sitemap), parse/normalize, hash |
| `worker-enrich` | Python (Celery) | Diff, relevance, dedup, LLM extraction, architecture |
| `worker-report` | Python (Celery) | Saturday aggregation, render, export, notify |
| `llm-gateway` | Python | Model-agnostic facade (OpenAI/Gemini), prompts, caching, budgets |
| `scheduler` | APScheduler | Cron-equivalent trigger for crawl/report jobs |
| `migrate` | Alembic/CLI | Schema migrations, taxonomy seeds |

## 2. Module Layout (proposed)

```
backend/
  api/            # FastAPI app: routes, schemas (Pydantic), deps (auth, tenant, RBAC)
  agents/         # agent implementations (discovery, evidence, change, ...)
  core/           # domain logic: dedup, scoring, taxonomy, lineage
  crawl/          # connectors per source type + policy (robots/rate/auth)
  llm/            # gateway, adapters, prompt registry, budgets
  storage/        # Postgres (SQLAlchemy), vector, graph, blob, search adapters
  events/         # schema + producer/consumer helpers (Redis Streams)
  jobs/           # orchestration + worker entrypoints (idempotent)
  observability/  # OTel setup, metrics, logging, tracing helpers
  migrations/     # Alembic revisions + seed data
```

## 3. Key Behaviors

- **Typed contracts everywhere:** Pydantic schemas bound every service boundary; agents use the envelope in [06_Agent_Architecture](./06_Agent_Architecture.md).
- **Deterministic-first:** parse/normalize/hash/diff/dedup/entity-resolution run as pure functions before any LLM call ([05_AI_Architecture](./05_AI_Architecture.md) §1).
- **Idempotent, replayable jobs:** every job carries an idempotency key (`run_id`); re-runs produce no duplicates ([NFR-007](./16_Requirement_Traceability_Matrix.md)).
- **Queued, decoupled stages:** producers publish; workers consume; DLQ on repeated failure ([FR-055](./16_Requirement_Traceability_Matrix.md)).
- **Human-in-the-loop gates:** low-confidence / high-impact outputs pause the pipeline at the Review gate.
- **Tenant isolation:** every repository query scoped by `tenant_id`; row-level security as backstop ([13_Security_Architecture](./13_Security_Architecture.md)).

## 4. Scoring Engine (deterministic)

Composite = Σ(metric_value × weight) − complexity_penalty, clamped to [0,100]; weights per [FR-034](./16_Requirement_Traceability_Matrix.md). Stored as a score vector with rationale; reviewer override overwrites value + reason and recomputes composite ([FR-034](./16_Requirement_Traceability_Matrix.md)). Scores are **recommendations, not facts.**

## 5. Deduplication & Canonicalization

- `canonical_key` derived from normalized title + entity resolution.
- Candidate merge keeps the full evidence trail; merged finding re-links children.
- Target: ≥ 90% duplicate consolidation (PRD metric) — gated in evaluation.

## 6. Reporting Pipeline

1. Aggregate the six-day window (Saturday boundary).
2. Rank opportunities from stored score vectors.
3. Compose exec summary + Automation Cards + appendices.
4. Render PDF/HTML/JSON/CSV; publish to object storage; record `file_uri`.
5. Notify configured recipients; never publish incomplete ([NFR-002](./16_Requirement_Traceability_Matrix.md), edge case in App Flow).

## 7. Failure & Observability

- OTel traces per job; metrics: crawl latency/bytes, agent token cost, queue depth, DLQ size, eval quality ([NFR-005](./16_Requirement_Traceability_Matrix.md)).
- Cost budgets per source/agent/tenant with alerting ([NFR-012](./16_Requirement_Traceability_Matrix.md)).
- Runbooks attached to alert types ([FR-055](./16_Requirement_Traceability_Matrix.md)).

## 8. Testing Surface (see [14_Testing_Strategy](./14_Testing_Strategy.md))

- Contract tests per service boundary.
- Idempotency tests (re-run equivalence).
- Tenant-isolation tests (cross-tenant access denied).
- Golden-set evaluation harness for LLM-dependent stages.

## 9. Definition of Done for This Architecture

This backend architecture is finalized when:

- [x] Backend services, module layout, and key behaviors are specified.
- [x] Scoring, deduplication, reporting, and observability designs are explicit.
- [x] Requirement traceability uses current RTM IDs ([16_Requirement_Traceability_Matrix](./16_Requirement_Traceability_Matrix.md)).
- [x] Stack alignment with ADR-0014 is explicit (LangGraph + Celery + APScheduler + Redis Streams + Qdrant + MinIO).
- [x] Implementation is blocked from starting until AI, frontend, and backend architecture are all finalized.
