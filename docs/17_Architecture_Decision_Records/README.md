# 17 — Architecture Decision Records (ADR)

**Purpose:** Record significant architecture decisions, the context behind them, and their consequences — so future changes understand *why* the system is shaped as it is.

## Decision Log

| ADR | Title | Status |
|---|---|---|
| [0001](./0001-nextjs-fastapi-stack.md) | React (JavaScript) + FastAPI technology stack | **Superseded by [0014](./0014-cost-minimized-open-source-stack.md) for data stores; Web UI amended to React JS; API decision remains** |
| [0002](./0002-agent-orchestration-framework.md) | Use an orchestration framework for multi-agent execution | Accepted |
| [0003](./0003-model-agnostic-llm-gateway.md) | Model-agnostic LLM gateway | Accepted |
| [0004](./0004-postgres-pgvector-neo4j.md) | PostgreSQL + pgvector + Neo4j data stores | Amended by [0014](./0014-cost-minimized-open-source-stack.md) |
| [0005](./0005-event-driven-idempotent-jobs.md) | Event-driven, idempotent, replayable jobs | Accepted |
| [0006](./0006-deterministic-preprocessing-first.md) | Deterministic preprocessing before generative reasoning | Accepted |
| [0007](./0007-evidence-first-fact-labeling.md) | Evidence-first with confirmed/inferred fact labeling | Accepted |
| [0008](./0008-aws-cloud-platform.md) | Cloud platform: AWS + EKS + Helm | Superseded by [0014](./0014-cost-minimized-open-source-stack.md) |
| [0009](./0009-temporal-orchestration-engine.md) | Temporal as the agent orchestration engine | Superseded by [0014](./0014-cost-minimized-open-source-stack.md) |
| [0010](./0010-keycloak-identity-provider.md) | Keycloak as the identity provider | Accepted — deployment details amended by [0014](./0014-cost-minimized-open-source-stack.md) |
| [0011](./0011-frontend-container-hosting.md) | Frontend hosting: container in the cluster | Superseded by [0014](./0014-cost-minimized-open-source-stack.md) |
| [0012](./0012-search-embeddings-postgres-bedrock.md) | Search & embeddings: Postgres FTS + Bedrock embeddings | Superseded by [0014](./0014-cost-minimized-open-source-stack.md) |
| [0013](./0013-dast-owasp-zap.md) | DAST: OWASP ZAP | Accepted |
| [0014](./0014-cost-minimized-open-source-stack.md) | Locked cost-minimized open-source technology stack | Accepted |
| [0015](./0015-react-javascript-frontend.md) | React (JavaScript) + Vite frontend architecture | Accepted — amends [0001](./0001-nextjs-fastapi-stack.md) (Web UI) and [0014](./0014-cost-minimized-open-source-stack.md) (frontend row) |
| [0016](./0016-jwt-only-auth-path.md) | JWT-only auth path with Keycloak-issued RS256 tokens | Accepted — amends [0010](./0010-keycloak-identity-provider.md) and [0014](./0014-cost-minimized-open-source-stack.md) |
| [0017](./0017-sap-official-sites-source-registry.md) | `SAP Official Sites.txt` as the canonical Discovery Engine source registry | Accepted — pins the M07/M09 source seed at repo root |

## ADR Template

Use the following template for new decisions (statuses: Proposed → Accepted | Superseded | Deprecated).

```markdown
# ADR-XXXX — Title

**Status:** Proposed | Accepted | Superseded | Deprecated
**Date:** YYYY-MM-DD
**Related:** [ADR-00XX](./00XX-...)

## Context
[What is the problem, constraint, or tension being decided?]

## Decision
[What was decided? Be specific.]

## Consequences
### Positive
- ...
### Negative / Trade-offs
- ...
### Neutral
- ...
```
