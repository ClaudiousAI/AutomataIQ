# ADR-0001 — React (JavaScript) + FastAPI Technology Stack

**Status:** Superseded by ADR-0014 for data stores; Web UI/API decisions amended
**Date:** 2026-08-11
**Related:** [04_System_Architecture](../04_System_Architecture.md) · [10_Backend_Architecture](../10_Backend_Architecture.md) · [11_Frontend_Architecture](../11_Frontend_Architecture.md) · [ADR-0014](./0014-cost-minimized-open-source-stack.md)

> **Note:** The technology-stack choices in this ADR (PostgreSQL+pgvector, Neo4j, S3-compatible storage, OpenSearch/PG-FTS) were superseded on 2026-08-10 by **[ADR-0014](./0014-cost-minimized-open-source-stack.md)** (self-hosted open-source stack with Qdrant for vectors). The **Web UI was amended on 2026-08-11 from Next.js + TypeScript to React (JavaScript) via ADR-0014**; only the API (Python FastAPI) decision from the original ADR-0001 remains valid.

## Context
SAIE needs a web workspace (React + JavaScript per the revised master design TRD for professional, fluid, ultra-smooth UX) and a typed service API (Python FastAPI). We must confirm this split as the foundation for all later work.

## Decision
Adopt the revised stack:
- **Web UI:** React + JavaScript (built via Vite, single-page application, no SSR).
- **API:** Python FastAPI with Pydantic-typed contracts.
- **Workers:** Python async (same language as API for shared domain code).
- **Datastores:** PostgreSQL (+pgvector), Neo4j, S3-compatible storage, queue/stream, OpenSearch/PG-FTS.
- **Orchestration:** workflow/orchestration framework (see ADR-0002).

## Consequences
### Positive
- Mature ecosystems on both sides; strong typing (Pydantic) at the API boundary; React provides ultra-smooth, fluid UX.
- One language (Python) across API, workers, LLM gateway, and crawl — shared core logic.
- OpenAPI generated from FastAPI powers a typed frontend client (can be generated to TypeScript types for the React app if desired).
### Negative / Trade-offs
- Two runtimes in the platform (Node + Python) → heavier ops than a single-stack option.
- Requires cross-language contract discipline to avoid drift.
- React SPA requires client-side routing and auth handling; no built-in SSR/SEO — acceptable for an authenticated workspace.
### Neutral
- Alternatives (Next.js, or a Python SSR framework) were considered; React SPA chosen for professional fluid UX per product direction.
