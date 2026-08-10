# ADR-0001 — Next.js + FastAPI Technology Stack

**Status:** Accepted
**Date:** 2026-08-10
**Related:** [04_System_Architecture](../04_System_Architecture.md) · [10_Backend_Architecture](../10_Backend_Architecture.md) · [11_Frontend_Architecture](../11_Frontend_Architecture.md)

## Context
SAIE needs a web workspace (Next.js + TypeScript per the master design's TRD) and a typed service API (Python FastAPI). We must confirm this split as the foundation for all later work.

## Decision
Adopt the master-design TRD stack:
- **Web UI:** Next.js + TypeScript (App Router).
- **API:** Python FastAPI with Pydantic-typed contracts.
- **Workers:** Python async (same language as API for shared domain code).
- **Datastores:** PostgreSQL (+pgvector), Neo4j, S3-compatible storage, queue/stream, OpenSearch/PG-FTS.
- **Orchestration:** workflow/orchestration framework (see ADR-0002).

## Consequences
### Positive
- Mature ecosystems on both sides; strong typing (TS + Pydantic) at the two boundaries.
- One language (Python) across API, workers, LLM gateway, and crawl — shared core logic.
- OpenAPI generated from FastAPI powers a typed frontend client.
### Negative / Trade-offs
- Two runtimes in the platform (Node + Python) → heavier ops than a single-stack option.
- Requires cross-language contract discipline to avoid drift.
### Neutral
- Alternatives (Next.js-only API routes, or a Python SSR framework) were out of scope; the TRD specified this split.
