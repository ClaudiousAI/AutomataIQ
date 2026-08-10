# 12 — DevOps Architecture

**Product:** SAP Automation Intelligence Engine (SAIE)
**Document status:** Baseline
**Related docs:** [03_NonFunctional_Requirements](./03_NonFunctional_Requirements.md) · [04_System_Architecture](./04_System_Architecture.md) · [15_Project_Roadmap](./15_Project_Roadmap.md)

---

## 1. Environments

| Env | Purpose | Data |
|---|---|---|
| `dev` | Local/feature development | Synthetic sources + small golden set |
| `staging` | Integration, eval gates, review | Mirrored source pack (subset) |
| `prod` | Live ingestion + Saturday reports | Production data, isolated per tenant |

Promotion `dev → staging → prod` is gated by CI checks + eval quality gates ([14_Testing_Strategy](./14_Testing_Strategy.md)).

## 2. Repository & CI/CD

- Monorepo: `web/`, `backend/`, `docs/`, `infra/`, `e2e/`.
- CI (on PR): lint, typecheck, unit + contract + idempotency tests, Docker build, security scan (SAST + dependency scan).
- CD: build image → push registry → deploy per environment; infrastructure as code.
- Env-specific config via environment/secret injection; no secrets in images or repo.

## 3. Container & Orchestration (per [ADR-0014](./17_Architecture_Decision_Records/0014-cost-minimized-open-source-stack.md))

- Containers per service ([10_Backend_Architecture](./10_Backend_Architecture.md) §1) built from multi-stage Dockerfiles (slim runtimes).
- Docker Compose for local dev and single-node deployment; production on any Docker-capable host behind Nginx (TLS termination).
- Scaling is vertical or manual horizontal; workers scale by starting additional replicas; no autoscaling (accepted trade-off in ADR-0014).
- Readiness/liveness probes; graceful shutdown for in-flight jobs (idempotency makes restarts safe).

## 4. Infrastructure as Code

- `infra/` holds Docker Compose definitions, Nginx config, env overlays, and bootstrap scripts per environment.
- GitHub Actions builds images, runs tests, and deploys via SSH/docker-compose to each environment.
- Secrets injected via environment/Docker secrets (SOPS for repo-encrypted secrets); no secrets in images or repo.

## 5. Data Services (self-hosted, prod)

| Service | Choice | Notes |
|---|---|---|
| PostgreSQL | Docker container | Backups via pg_dump/cron; PITR via WAL archiving |
| Vector | Qdrant (single node) | Snapshot/backup; manual cluster if prod scale demands |
| Object storage | MinIO | Versioning + lifecycle retention for snapshots |
| Cache + queue | Redis | Cache + Redis Streams; DLQ group |
| Search | PostgreSQL FTS | In-process; no separate store |
| Neo4j | Neo4j Community Edition | Graph data; export/backup strategy |

All data stores self-hosted; no managed cloud equivalents (see [ADR-0014](./17_Architecture_Decision_Records/0014-cost-minimized-open-source-stack.md)).

## 6. Observability Stack

- **OpenTelemetry** SDK/exporters in all services; traces, metrics, logs correlated by `trace_id`.
- Backends (self-hosted, per [ADR-0014](./17_Architecture_Decision_Records/0014-cost-minimized-open-source-stack.md)): **Prometheus** (metrics) + **Grafana** (dashboards) + **Loki** (logs); OTel traces flow to Prometheus/Grafana.
- Dashboards: source health, agent health, queue depth, DLQ, LLM cost, job latency, eval quality ([NFR-5], [NFR-12]).
- Alerts with runbook links ([FR-C09-7]).

## 7. Backup, Retention & DR

- Postgres: automated backups + PITR; restore drills scheduled.
- Object storage: bucket versioning; snapshot/report lifecycle (source-content retention policy).
- DR: RPO/RTO targets per environment (staging/prod defined in roadmap Phase 14); runbooks documented.
- Replayable ingestion means a data loss window is recoverable by re-crawl under policy.

## 8. Release Process (Phase 2 foundation, matured in Phase 14)

```
PR → CI (lint/tests/build/scan) → staging deploy → eval gates → 
     prod deploy (blue-green or canary for web/api) → 
     workers roll with drain → observability post-check
```

- Change-controlled: governed actions (models, prompts, scoring weights) require review + audit ([FR-C09-3]).
- Runbooks for: crawl outage, LLM cost spike, report failure, DB failover, DLQ drain.
