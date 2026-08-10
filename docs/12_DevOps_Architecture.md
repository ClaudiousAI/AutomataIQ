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

## 3. Container & Orchestration

- Containers per service ([10_Backend_Architecture](./10_Backend_Architecture.md) §1) built from multi-stage Dockerfiles (slim runtimes).
- Kubernetes (or managed containers) with namespaces: `app`, `workers`, `data`, `observability`.
- Autoscaling: workers scale on queue depth; API scales on request/CPU.
- Readiness/liveness probes; graceful shutdown for in-flight jobs (idempotency makes restarts safe).

## 4. Infrastructure as Code

- Terraform/OpenTofu (or cloud-native IaC) for network, clusters, managed stores (Postgres, object storage, queue, search).
- Helm (or Kustomize) for application manifests per environment.
- State remote + locking; environments fully reproducible.

## 5. Data Services (managed, prod)

| Service | Choice | Notes |
|---|---|---|
| PostgreSQL + pgvector | Managed RDS/Cloud SQL (or equiv.) | Backups, PITR, automated failover |
| Object storage | S3-compatible managed | Versioning + lifecycle retention for snapshots |
| Queue/stream | Managed Kafka / Redis | Retained topics; DLQ |
| Search | Managed OpenSearch or PG FTS | Managed shards |
| Neo4j | Managed or containerized | Graph data; export/backup strategy |

Dev uses containerized equivalents for parity.

## 6. Observability Stack

- **OpenTelemetry** SDK/exporters in all services; traces, metrics, logs correlated by `trace_id`.
- Backend: managed metrics/logs/traces (e.g., Prometheus + Loki + Tempo, or cloud equivalents) + Grafana dashboards.
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
