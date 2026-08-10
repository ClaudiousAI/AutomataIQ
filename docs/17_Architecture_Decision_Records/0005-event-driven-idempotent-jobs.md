# ADR-0005 — Event-Driven, Idempotent, Replayable Jobs

**Status:** Accepted
**Date:** 2026-08-10
**Related:** [10_Backend_Architecture](../10_Backend_Architecture.md) · NFR-2 · NFR-7

## Context
The pipeline (crawl → diff → classify → extract → reconstruct → score → report) runs on schedules and triggers, must recover from failures, must not publish incomplete reports, and must control cost by processing only meaningful changes.

## Decision
- Decouple stages via a **queue/stream layer** (Kafka/managed queue/Redis streams) with versioned event schemas.
- Every job carries an **idempotency key** (`run_id`); re-runs produce identical, non-duplicated results.
- Jobs are **replayable** from persisted state (workflow/durable execution, ADR-0002).
- **Change gating** (hash/diff) precedes expensive semantic work; unchanged content never reaches the LLM.
- DLQ + alerting on repeated failures; report generation is atomic (complete or not published).

## Consequences
### Positive
- Worker pools scale independently (NFR-3).
- Failures retry cleanly; recoverability without data loss (NFR-7).
- Cost control via gating (NFR-12).
### Negative / Trade-offs
- Event-schema versioning discipline is mandatory (contracts in [08_API_Design](../08_API_Design.md)).
- Distributed systems debugging complexity (mitigated by OTel correlation).
### Neutral
- Aligns with the master design's "asynchronous event-driven processing" and "idempotent, replayable jobs" principles.
