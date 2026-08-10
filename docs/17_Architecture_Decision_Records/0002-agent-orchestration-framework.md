# ADR-0002 — Use an Orchestration Framework for Multi-Agent Execution

**Status:** Accepted
**Date:** 2026-08-10
**Related:** [06_Agent_Architecture](../06_Agent_Architecture.md)

## Context
The platform is a multi-agent pipeline (Discovery → Evidence → Change → Automation → Architecture → Opportunity → Scoring → Knowledge → Report → Review → Governance). Agents must run in controlled, auditable, replayable order with retries and human-in-the-loop gates — not free-form autonomous loops.

## Decision
Drive agent execution with an explicit **workflow/orchestration framework** (e.g., Temporal-style durable workflows, or a comparable orchestration engine) rather than ad-hoc agent-to-agent calling.

- Agents communicate through **typed contracts and persistent artifacts** (object storage + Postgres metadata), never direct chat.
- Orchestrator defines steps, retries, backoff, rollback, and review gates.
- Every run records `run_id` (idempotency key), model, prompt version, status, cost, latency.

## Consequences
### Positive
- Durable execution: workflows survive worker restarts (replay), supporting NFR-7 recoverability.
- Explicit human-in-the-loop gates for low-confidence/high-impact items.
- Full audit of agent runs (`agent_runs` table).
### Negative / Trade-offs
- Adds a stateful orchestration component to operate (deployment + scaling).
- More ceremony than a plain queue fan-out; justified by governance requirements.
### Neutral
- Concrete engine choice deferred to implementation; the contract (typed I/O + artifacts) is engine-independent.
