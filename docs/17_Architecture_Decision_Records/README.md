# 17 — Architecture Decision Records (ADR)

**Purpose:** Record significant architecture decisions, the context behind them, and their consequences — so future changes understand *why* the system is shaped as it is.

## Decision Log

| ADR | Title | Status |
|---|---|---|
| [0001](./0001-nextjs-fastapi-stack.md) | Next.js + FastAPI technology stack | Accepted |
| [0002](./0002-agent-orchestration-framework.md) | Use an orchestration framework for multi-agent execution | Accepted |
| [0003](./0003-model-agnostic-llm-gateway.md) | Model-agnostic LLM gateway | Accepted |
| [0004](./0004-postgres-pgvector-neo4j.md) | PostgreSQL + pgvector + Neo4j data stores | Accepted |
| [0005](./0005-event-driven-idempotent-jobs.md) | Event-driven, idempotent, replayable jobs | Accepted |
| [0006](./0006-deterministic-preprocessing-first.md) | Deterministic preprocessing before generative reasoning | Accepted |
| [0007](./0007-evidence-first-fact-labeling.md) | Evidence-first with confirmed/inferred fact labeling | Accepted |

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
