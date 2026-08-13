---
gh_issue_number: null
gh_issue_url: null
local_id: 003
type: feat
priority: high
area: [backend, data]
title: "feat(data): provision Qdrant collection + payload schema + HNSW"
module: M03b
rtm_ids: [FR-043, NFR-009, NFR-013]
filed: 2026-08-13
filed_by: orchestrator
status: open
parent_local_id: 001
sub_issue_local_ids: []
mirror_pending: true
---

# feat(data): provision Qdrant collection + payload schema + HNSW

> Sub-issue of [`001-m03b-storage-substrate`](./001-m03b-storage-substrate.md). Tracker-blocked; mirrors the would-be GitHub Issue body per [`docs/26/README.md`](../26_Open_Issues/README.md).

## Summary

Provision the Qdrant vector store that M11 (Knowledge & Search) will populate and query for the hybrid semantic-search surface. Ships the `saie_embeddings` collection, its typed payload schema, the HNSW config sized for the NFR-009 p95 < 3 s budget on the reference set, and the `QdrantAdapter` Protocol (inheriting the shape from `002`'s `RedisAdapter`).

## Linked Requirement ID(s)

`FR-043` (Semantic search + structured filters, hybrid vector + facets) · `NFR-009` (Performance — search p95 < 3 s) · `NFR-013` (Storage adapters behind interfaces)

## Parent epic ACs satisfied

`AC-1` (provisioner idempotency) · `AC-3` (Qdrant collection + p95 budget) · `AC-7` (docker-compose wiring) · `AC-8` (cross-tenant denial) · `AC-6` (Protocol contract — `QdrantAdapter`)

## Acceptance Criteria

- [ ] **AC-2a** Collection `saie_embeddings` exists with the typed payload schema: `tenant_id` (keyword, indexed, required), `source_id` (keyword, indexed), `finding_id` (keyword, indexed), `kind` (keyword, indexed, enum: `automation | architecture | opportunity | evidence`), `confidence` (float, 0.0–1.0, indexed for range filter), `ts` (integer, epoch seconds, indexed for time-window query). Vector dim matches the OpenAI embedding model selected in M05 (the M03b code must read this from `settings.embedding_dim` so the M05 model swap doesn't require a M03b change).
- [ ] **AC-2b** HNSW config: `m`, `ef_construct`, and `ef` chosen so that a reference-set query of 10 k vectors returns p95 < 3 s on a 2-vCPU / 4 GB RAM Qdrant instance. Config values recorded in `infra/qdrant/config.yaml` with a comment linking to the benchmark script.
- [ ] **AC-2c** `pytest tests/integration/test_qdrant_collection.py` green: idempotent collection creation, payload-schema validation rejects a missing `tenant_id`, range filter on `confidence` works, time-window filter on `ts` works, tenant_id filter on cross-tenant query returns zero (AC-8, FR-057).
- [ ] **AC-2d** `backend/app/storage/qdrant_adapter.py` ships the `QdrantAdapter` **implementation**, importing the Protocol from [`006`](./006-m03b-storage-adapter-interfaces.md) (`from backend.app.storage.protocols import QdrantAdapter`). The implementation must satisfy every method on the Protocol; the Protocol's method signatures, the `payload_filter_builder().tenant(tenant_id)` non-removable filter rule, and the `tenant_id`-first invariant are the source of truth and live in `006`. This sub-issue ships only the implementation — the contract is locked upstream so it cannot drift across the four adapters.
- [ ] **AC-2e** Docker Compose service: `qdrant/qdrant:v1.x` with persistent volume and resource limits matching the benchmark instance; healthcheck asserts the `/readyz` endpoint.
- [ ] **AC-2f** CI on the Ubuntu runner: spin a Qdrant container in the integration test (the M03a pattern of substrate == CI version applies — pin the Qdrant image SHA, not just the tag, to avoid silent breakage on upstream releases).

## Out of Scope

- The embedding-generation call (M05 owns the LLM gateway; M11 owns the population pipeline that generates embeddings and upserts them).
- Hybrid-search ranking (Postgres FTS + Qdrant vector fusion is M11's). M03b ships the substrate; the ranking is downstream.
- Cross-region replication / HA. Per `docs/18 §8` (open questions) Qdrant HA is tracked for the M16 deployment phase, not M03b.

## Tests Required

- **Integration** — `test_qdrant_collection.py` (AC-2c): idempotency, payload validation, range/time filters, cross-tenant denial.
- **Performance** — p95 benchmark on the reference set (AC-2b); the script lives at `backend/tests/perf/test_qdrant_p95.py` and the result is committed under `backend/tests/perf/baselines/qdrant.json` so regressions are caught.
- **Contract** — `QdrantAdapter` Protocol method signatures; M04 import smoke test.

## Definition of Done

- [ ] All ACs above checked.
- [ ] Linked RTM IDs in `docs/16` updated.
- [ ] `infra/qdrant/config.yaml` committed with the HNSW values + benchmark linkage.
- [ ] Any new CI gotcha pinned in `docs/18 §6`.
- [ ] PR title `feat(data): provision Qdrant collection + payload schema + HNSW (FR-043, NFR-009, NFR-013)`.
- [ ] Sub-issue AC ledger flipped at merge-time per `docs/25 §8`.

## Filed by

Orchestrator, 2026-08-13. Sub-issue of epic `001-m03b-storage-substrate`.
