# ADR-0009 — Temporal as the Agent Orchestration Engine

**Status:** Accepted
**Date:** 2026-08-10
**Related:** [ADR-0002](./0002-agent-orchestration-framework.md) · [ADR-0005](./0005-event-driven-idempotent-jobs.md) · [06_Agent_Architecture](../06_Agent_Architecture.md) · [10_Backend_Architecture](../10_Backend_Architecture.md)
**Resolves:** ADR-0002 deferral, OD-1 (orchestration engine)

## Context
ADR-0002 committed to a workflow/orchestration framework but deferred the concrete engine. Requirements: durable execution (NFR-7 recoverability), idempotent replayable jobs (ADR-0005), retries/backoff, human-in-the-loop review gates, and full run auditability (`agent_runs`). Candidates: Temporal, Prefect, Airflow, AWS Step Functions.

## Decision
Adopt **Temporal** as the orchestration engine.

- Each agent pipeline stage is a Temporal workflow/activity: Discovery → Evidence → Change → Automation → Architecture → Opportunity → Scoring → Knowledge → Report → Review → Governance.
- Workflow state and `run_id` idempotency keys give exactly-once semantics and crash-safe replay.
- Human review gates are Temporal waits (sleep-until-signal) on the Review Queue.
- Retries, timeouts, and backoff are declared per activity; failures route to retry, DLQ, or review per ADR-0005.

## Consequences
### Positive
- Durable execution: a workflow survives worker restarts and resumes from the last completed activity — directly satisfies NFR-7.
- Built-in idempotency/replay aligns with ADR-0005's replayable-job requirement.
- Per-activity visibility (Temporal Web UI) supports source-health and agent-health dashboards (FR-055).
- Engine-independent agent contract (typed I/O + persistent artifacts) from ADR-0002 is preserved — the pipeline is not coupled to Temporal internals.
### Negative / Trade-offs
- Adds a stateful service (Temporal cluster) to operate on EKS; needs its own HA, storage (ES/Postgres), and scaling.
- Temporal's TypeScript/Python SDKs have a learning curve and type-level constraints.
- Self-hosting Temporal (vs Temporal Cloud) is an operational cost; evaluated at Phase 2.
### Neutral
- Temporal's event-history growth must be monitored and archived; history limits configured per workflow.
