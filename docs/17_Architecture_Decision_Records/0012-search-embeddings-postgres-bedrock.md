# ADR-0012 — Search & Embeddings: Postgres FTS + Bedrock Embeddings

**Status:** Accepted
**Date:** 2026-08-10
**Related:** [ADR-0004](./0004-postgres-pgvector-neo4j.md) · [ADR-0008](./0008-aws-cloud-platform.md) · [07_Database_Design](../07_Database_Design.md)
**Resolves:** OD-5 (faceted search), OD-6 (default embedding model)

## Context
FR-043 requires hybrid semantic + faceted search with NFR-9's p95 < 3s. ADR-0004 chose pgvector for embeddings and left the search engine open (Postgres FTS vs OpenSearch). The default embedding model was also deferred.

## Decision
- **Search: PostgreSQL full-text search (FTS) + pgvector, in the primary Postgres store.** Facets are handled with Postgres columns/GIN indexes; semantic search via pgvector HNSW.
- **Default embeddings: Amazon Bedrock-hosted models** (Amazon Titan Text Embeddings, with Cohere-on-Bedrock as an alternative), routed through the model-agnostic LLM gateway (ADR-0003).
- If search SLOs are missed at production scale, OpenSearch (Amazon OpenSearch Service) is the escape hatch — the search layer is isolated behind an adapter.

## Consequences
### Positive
- One less store to operate; FTS + pgvector run in the same RDS instance as transactional data (ADR-0004).
- Meets NFR-9 at the product's moderate ingestion scale; simplest ops.
- Bedrock embeddings keep the embedding cost/provider story inside AWS and behind the ADR-0003 gateway (swappable to OpenAI or open-source without code change).
### Negative / Trade-offs
- Postgres FTS is weaker than OpenSearch on large-scale faceting and relevance tuning; must be re-evaluated if p95 > 3s or query volume outgrows it.
- Bedrock embeddings add API cost and egress/latency per embedding job; mitigated by deterministic gating (ADR-0006) and caching (only changed content is embedded).
### Neutral
- Embeddings and vectors versioned with the model that produced them (`model_version` on rows) per NFR-6.
