# 10 — Backend Architecture

**Product:** SAP Automation Intelligence Engine (SAIE)
**Document status:** Baseline
**Related docs:** [04_System_Architecture](./04_System_Architecture.md) · [06_Agent_Architecture](./06_Agent_Architecture.md) · [07_Database_Design](./07_Database_Design.md) · [08_API_Design](./08_API_Design.md)

---

## 1. Services

| Service | Runtime | Responsibility |
|---|---|---|
| `api` | FastAPI (Python) | Typed REST surface; auth; RBAC; validation |
| `orchestrator` | Python | Drives multi-agent pipeline via workflow framework |
| `worker-crawl` | Python async | Acquisition (HTML/RSS/API/sitemap), parse/normalize, hash |
| `worker-enrich` | Python async | Diff, relevance, dedup, LLM extraction, architecture |
| `worker-report` | Python async | Saturday aggregation, render, export, notify |
| `llm-gateway` | Python | Model-agnostic facade, prompts, caching, budgets |
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
  events/         # schema + producer/consumer helpers (Kafka/Redis)
  jobs/           # orchestration + worker entrypoints (idempotent)
  observability/  # OTel setup, metrics, logging, tracing helpers
  migrations/     # Alembic revisions + seed data
```

## 3. Key Behaviors

- **Typed contracts everywhere:** Pydantic schemas bound every service boundary; agents use the envelope in [06_Agent_Architecture](./06_Agent_Architecture.md).
- **Deterministic-first:** parse/normalize/hash/diff/dedup/entity-resolution run as pure functions before any LLM call ([05_AI_Architecture](./05_AI_Architecture.md) §1).
- **Idempotent, replayable jobs:** every job carries an idempotency key (`run_id`); re-runs produce no duplicates ([NFR-7]).
- **Queued, decoupled stages:** producers publish; workers consume; DLQ on repeated failure ([FR-C09-4]).
- **Human-in-the-loop gates:** low-confidence / high-impact outputs pause the pipeline at the Review gate.
- **Tenant isolation:** every repository query scoped by `tenant_id`; row-level security as backstop ([13_Security_Architecture](./13_Security_Architecture.md)).

## 4. Scoring Engine (deterministic)

Composite = Σ(metric_value × weight) − complexity_penalty, clamped to [0,100]; weights per PRD/C06. Stored as a score vector with rationale; reviewer override overwrites value + reason and recomputes composite ([FR-C06-*]). Scores are **recommendations, not facts.**

## 5. Deduplication & Canonicalization

- `canonical_key` derived from normalized title + entity resolution.
- Candidate merge keeps the full evidence trail; merged finding re-links children.
- Target: ≥ 90% duplicate consolidation (PRD metric) — gated in evaluation.

## 6. Reporting Pipeline

1. Aggregate the six-day window (Saturday boundary).
2. Rank opportunities from stored score vectors.
3. Compose exec summary + Automation Cards + appendices.
4. Render PDF/HTML/JSON/CSV; publish to object storage; record `file_uri`.
5. Notify configured recipients; never publish incomplete ([FR-C08-6], edge case in App Flow).

## 7. Failure & Observability

- OTel traces per job; metrics: crawl latency/bytes, agent token cost, queue depth, DLQ size, eval quality.
- Cost budgets per source/agent/tenant with alerting ([NFR-12]).
- Runbooks attached to alert types ([FR-C09-7]).

## 8. Testing Surface (see [14_Testing_Strategy](./14_Testing_Strategy.md))

- Contract tests per service boundary.
- Idempotency tests (re-run equivalence).
- Tenant-isolation tests (cross-tenant access denied).
- Golden-set evaluation harness for LLM-dependent stages.
