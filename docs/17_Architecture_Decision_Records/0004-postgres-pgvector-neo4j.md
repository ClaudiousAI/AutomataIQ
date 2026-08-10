# ADR-0004 — PostgreSQL + pgvector + Neo4j Data Stores

**Status:** Accepted
**Date:** 2026-08-10
**Related:** [07_Database_Design](../07_Database_Design.md)

## Context
SAIE needs transactional metadata, semantic retrieval, and relationship queries. Options ranged from a single document/vector store to a polyglot set. Tenancy, lineage, and audit require transactional integrity.

## Decision
- **PostgreSQL** as the system of record (transactional metadata, `tenant_id` scoping, RLS).
- **pgvector (in Postgres)** for semantic embeddings — avoids a separate vector DB.
- **Neo4j** for the knowledge-graph (cross-domain, multi-hop, temporal lineage) where relationship queries are first-class.
- **S3-compatible object storage** for snapshots/report blobs; **OpenSearch/PG-FTS** for faceted search.

## Consequences
### Positive
- Single transactional store keeps tenancy/audit/lineage strong (NFR-4, NFR-1).
- pgvector keeps vector + relational data consistent without a second system.
- Neo4j models cross-domain queries ("AI affecting MM & manufacturing") naturally.
### Negative / Trade-offs
- Polyglot: more stores to operate than a single document DB.
- Postgres/pgvector scales fine for target sizes; very large embedding workloads may later warrant a dedicated vector store.
### Neutral
- Graph data is derived from PostgreSQL (extraction writes rows, graph is a projection with lineage).
