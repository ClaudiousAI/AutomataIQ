---
gh_issue_number: null
gh_issue_url: null
local_id: 001
type: epic
priority: high
area: [backend, data]
title: "epic(data): M03b storage-layer substrate (Redis/Qdrant/Neo4j/MinIO)"
module: M03b
rtm_ids: [FR-008, FR-038, FR-041, FR-043, NFR-007, NFR-009, NFR-011, NFR-013]
filed: 2026-08-13
filed_by: orchestrator
status: open
parent_local_id: null
sub_issue_local_ids: [002, 003, 004, 005, 006, 007]
mirror_pending: true
---

# epic(data): M03b storage-layer substrate (Redis/Qdrant/Neo4j/MinIO)

> **Tracker status:** mirror-pending per [`docs/26/README.md`](../26_Open_Issues/README.md). The body below is the would-be GitHub Issue body; the `issue-maintainer` agent will file + back-fill `gh_issue_number` when `gh` (or a `$GITHUB_TOKEN` API path) is available. Until then, this file is the source of truth that the `architect` reads, the `backend-expert` + `qa-engineer` fulfill, and the conductor tracks to merge.

## Goal / Outcome

The storage-layer remainder of M03 lands. Redis Streams + DLQ consumer groups, the Qdrant collection + payload schema + HNSW config, the Neo4j constraints + seed, and the MinIO buckets + versioning + lifecycle + retention are all provisioned idempotently and exercised by the M04 storage adapters. The `app/db/tenant.py` RLS convention from M03a carries over to every cross-store query path. M04 (Core Backend) becomes unblocked; M07 (Discovery), M08 (Research), and M11 (Knowledge & Search) can begin satisfying their storage-side acceptance criteria.

## Module

**M03b** — the second slice of [M03 (Database & Storage)](../../22_Module_Roadmap.md#m03--database--storage) in [`docs/22 §5`](../22_Module_Roadmap.md). M03a (Schema + RLS substrate) landed in PR #4 (`2a7d936`); the audit-follow-up closure landed in PR #5 (`89cddf1`). The pre-merge audit findings that drove the closure are recorded in [`docs/29_Audit_Report_Pre_M03a_Close.md`](../29_Audit_Report_Pre_M03a_Close.md); the M03a design rationale is in [`docs/28_M03a_Design.md`](../28_M03a_Design.md). M03b is the storage-layer remainder that M03a deliberately deferred.

## Linked Requirement ID(s)

- `FR-008` — Versioned snapshots (policy-compliant storage + normalized snapshot) → drives the MinIO bucket + versioning + lifecycle work.
- `FR-038` — Knowledge graph linking → drives the Neo4j constraints + seed.
- `FR-041` — Evidence and confidence at fact/relationship level → drives Neo4j evidence/confidence edge properties.
- `FR-043` — Semantic search + structured filters (hybrid vector + facets) → drives the Qdrant collection + payload schema + HNSW config.
- `NFR-007` — Recoverability (idempotent, replayable jobs) → drives Redis Streams + DLQ consumer groups + idempotent provisioning.
- `NFR-009` — Performance (search p95 < 3 s; graph p95 < 2 s; report < 30 min) → drives Qdrant HNSW + Neo4j index choices.
- `NFR-011` — Compliance (robots, terms, retention) → drives the MinIO retention / lifecycle policy.
- `NFR-013` — Model lock-in resistance (storage adapters behind interfaces, per `docs/22 §5.M04`) → drives the **portability** requirement on every new adapter.

## Scope (in)

- **Redis** — cache namespace; Streams topics (`saie.crawl`, `saie.evidence`, `saie.report`); consumer groups with at-least-once + idempotency key per `app/db/tenant.py` convention; DLQ stream + DLQ consumer group; reconnect/backoff helper.
- **Qdrant** — collection `saie_embeddings`; payload schema (tenant_id, source_id, finding_id, kind, confidence, ts); HNSW config sized for NFR-009 budget on the reference set; idempotent collection bootstrap.
- **Neo4j** — community edition; constraints (uniqueness on canonical keys; existence on required props) for the 11 node kinds enumerated in `docs/07 §4` (sources, findings, automations, products, processes, industries, technologies, APIs, events, architectures, opportunities); seed script idempotent; evidence + confidence on every edge (FR-041).
- **MinIO** — buckets: `saie-snapshots` (versioned, lifecycle: archive to warm tier after 90 d, expire after 7 y per NFR-011), `saie-artifacts` (agent output, versioned), `saie-reports` (the published Saturday report, write-once). IAM policy per bucket. Retention enforced by lifecycle rule, not application code.
- **Provisioner** — a single `saie.bootstrap` entry point (Celery task OR CLI) that is idempotent: re-running it produces no duplicates, no orphaned resources, no re-created topics. The provisioner is what the M03 acceptance criterion *"Seed re-runs produce no duplicates"* means in practice for the storage layer.
- **Storage adapters** (interfaces only; the live adapter wiring is M04's work) — typed Protocol classes for `RedisAdapter`, `QdrantAdapter`, `Neo4jAdapter`, `MinioAdapter` with the operations M04 will call. M03b ships the interfaces + the M03b-side implementations; M04 wires them into the FastAPI app and the agent framework. This split is the M03b/M04 contract — see the **Out of Scope** list for the boundary.

## Scope (out)

- **M04 work**: FastAPI app factory, request validation, OTel middleware, API versioning, the agent envelope, the LLM gateway, the event-bus runtime helpers. M03b ships **adapter interfaces** that M04 imports; M03b does not wire them into a request path.
- **M05+ work**: anything LLM, agent, or scoring. No model registry, no prompt registry, no scorer.
- **M07+ work**: discovery crawlers, change detection, evidence confidence scoring, scoring engine. The Redis Streams *topics* are provisioned; **no producer code** ships in M03b.
- **M11 work**: graph population from real findings. Neo4j constraints and seed are M03b's; the population pipeline is M11's.
- **M16 work**: deployment, secrets management, environment overlays, backup/restore, DR drill. M03b is the substrate; M16 is the runtime topology.

## Epic-Level Acceptance Criteria

(These are the module-exit-gate criteria from `docs/22 §6` plus the M03-specific ACs from `docs/22 §5.M03`, restated here as the live AC checkbox ledger per `docs/25 §8`.)

- [ ] **AC-1** `saie.bootstrap` is idempotent: running it twice from a clean state yields identical resource state; re-running it from the post-bootstrap state is a no-op (NFR-007).
- [ ] **AC-2** Redis Streams topics (`saie.crawl`, `saie.evidence`, `saie.report`) exist with their consumer groups and a `saie.dlq` DLQ stream + DLQ consumer group; a `pytest` round-trip exercises publish → consume → DLQ on a poison message (NFR-007).
- [ ] **AC-3** Qdrant collection `saie_embeddings` exists with the typed payload schema (tenant_id, source_id, finding_id, kind, confidence, ts) and HNSW config; the fixture corpus returns p95 < 3 s on the reference set (FR-043, NFR-009).
- [ ] **AC-4** Neo4j uniqueness + existence constraints exist for all 11 node kinds in `docs/07 §4`; the seed script is idempotent; FR-041 (evidence + confidence on every edge) is enforced at the schema level via property-existence constraints (FR-038, FR-041).
- [ ] **AC-5** MinIO buckets `saie-snapshots`, `saie-artifacts`, `saie-reports` exist with versioning, lifecycle, and retention per NFR-011; a synthetic retention test asserts that objects older than the rule age are tiered or expired (FR-008, NFR-011).
- [ ] **AC-6** Storage adapters (`RedisAdapter`, `QdrantAdapter`, `Neo4jAdapter`, `MinioAdapter`) exist as typed Protocol classes with documented operations; the M03b-side implementations compile against them; an M04 import smoke test (`backend/tests/test_storage_adapter_interfaces.py`) imports them and asserts the Protocol methods (NFR-013).
- [ ] **AC-7** The provisioner is wired into the M03a CI substrate (Postgres already on the runner per `docs/18 §6` gotcha) and into `docker-compose.yml` for dev — `docker compose up` brings Redis + Qdrant + Neo4j + MinIO online idempotently (NFR-007, NFR-013).
- [ ] **AC-8** Tenant isolation extends across stores: a cross-tenant Qdrant query returns zero hits; a cross-tenant Neo4j traversal raises; a cross-tenant MinIO object access is denied (FR-057, mirrors the M03a RLS guarantee).
- [ ] **AC-9** `docs/18` is updated with any new CI / runtime gotcha discovered during the M03b build (per `docs/18 §6` discipline; the M03a gotcha is the model).
- [ ] **AC-10** All linked RTM IDs (`FR-008`, `FR-038`, `FR-041`, `FR-043`, `NFR-007`, `NFR-009`, `NFR-011`, `NFR-013`) are moved to **Done** in [`docs/16`](../16_Requirement_Traceability_Matrix.md) when the closing PR merges.
- [ ] **AC-11** **Tenant isolation is a uniform, code-review-enforceable invariant across all four stores.** Every adapter method (`RedisAdapter`, `QdrantAdapter`, `Neo4jAdapter`, `MinioAdapter`) accepts `tenant_id` as the first positional argument and uses it as the first predicate in every store-side query, key, or access check — without exception, without escape hatch, without an "admin override" path. The M03a `app.tenant_id` GUC convention is the model: at the Postgres layer the GUC is set inside a `SET LOCAL` transaction; at the M03b layer the equivalent is "the adapter's first parameter IS the tenant context, and the adapter refuses to construct a query that doesn't filter on it." Enforcement is mechanical, not social: a CI test (`backend/tests/security/test_tenant_isolation_pattern.py`) greps every adapter module for the pattern `tenant_id` as the first parameter and asserts that every public method has it; the test fails the build on regression. The architect designs the test scaffolding (pytest fixture + AST or string-level check); this AC locks the *policy* — that the invariant is uniform across all four stores and that the lint is the enforcer, not human review. (FR-057, FR-008 in spirit, M03a RLS as the model.)

## Dependencies / Sequencing

- **Depends on** M01 (project foundation, merged) + M02 (auth, merged) + M03a (schema + RLS substrate, merged PR #4 + closure PR #5). All three are landed; this epic is unblocked at the source.
- **Unblocks** M04 (Core Backend — adapter wiring, event-bus runtime helpers, error envelope). M04's "Storage adapters behind interfaces" and "Redis Streams producer/consumer helpers + DLQ handling" ACs are the **direct downstream consumers** of M03b's outputs.
- **Per `docs/22 §3` wave ordering**, M04 is the next module after M03b. M04 may start **contract-first in parallel** with M03b once the M03b/M04 storage-adapter interface contract is agreed (the architect's first deliverable). M04's *live* work follows M03b.

## Sub-Issues (placeholders — mirror to GitHub sub-issues when `gh` lands)

| Local ID | Type | Title | Module slice | M03 AC it satisfies |
|---|---|---|---|---|
| [`002`](./002-m03b-redis-streams-dlq.md) | feat | feat(data): provision Redis Streams + DLQ consumer groups | M03b · Redis | AC-1, AC-2, AC-7 |
| [`003`](./003-m03b-qdrant-collection-payload.md) | feat | feat(data): provision Qdrant collection + payload schema + HNSW | M03b · Qdrant | AC-1, AC-3, AC-7, AC-8 |
| [`004`](./004-m03b-neo4j-constraints-seed.md) | feat | feat(data): provision Neo4j constraints + seed for 11 node kinds | M03b · Neo4j | AC-1, AC-4, AC-7, AC-8 |
| [`005`](./005-m03b-minio-buckets-lifecycle.md) | feat | feat(data): provision MinIO buckets + versioning + lifecycle | M03b · MinIO | AC-1, AC-5, AC-7, AC-8 |
| [`006`](./006-m03b-storage-adapter-interfaces.md) | feat | feat(data): M03b/M04 storage adapter interfaces (shared Protocols) | M03b · spine | AC-6, AC-11 |
| [`007`](./007-m03b-provisioner-cli.md) | feat | feat(data): M03b provisioner CLI - saie.bootstrap idempotent entry point | M03b · glue | AC-1, AC-7, AC-9 |

The M03b/M04 interface contract (`RedisAdapter`, `QdrantAdapter`, `Neo4jAdapter`, `MinioAdapter` Protocols) is captured in sub-issue [`006`](./006-m03b-storage-adapter-interfaces.md) as the **single source of truth**. The four store-side sub-issues `002`/`003`/`004`/`005` ship only the **implementations** and import the Protocols from `006` — they do not define the shape themselves, and they do not import from each other. This is the property the M04 import smoke test (`AC-6c`) and the AC-11 lint both depend on: drift across the four PRs is caught at import time and at build time, not by reviewer reading.

`006` is filed **before** the four store-side slices begin implementation, by conductor judgment call: the Protocol contract is the dependency gate, not a coordination convention. This is an explicit exception to the `docs/25 §7` "file after design" default — the default assumes a per-PR contract; here the contract is shared, so it must be locked first.

## Tests Required

(Per [`docs/14 §3`](../14_Testing_Strategy.md) level definitions and the M03 tests in `docs/22 §5.M03`.)

- **Integration** — provisioner idempotency on a clean state and on a post-bootstrap state (AC-1).
- **Integration** — Redis publish → consume → DLQ round-trip on a poison message (AC-2, NFR-007).
- **Performance** — Qdrant fixture p95 < 3 s on the reference set (AC-3, NFR-009).
- **Integration** — Neo4j constraint violation on a duplicate canonical key (AC-4).
- **Integration** — MinIO lifecycle on a synthetic aged object (AC-5, NFR-011).
- **Contract** — `RedisAdapter` / `QdrantAdapter` / `Neo4jAdapter` / `MinioAdapter` Protocol method signatures; M04 import smoke test (AC-6, NFR-013).
- **Security** — cross-tenant store query returns zero / denied (AC-8, FR-057).
- **Security / lint** — `backend/tests/security/test_tenant_isolation_pattern.py` asserts every public method on every adapter accepts `tenant_id` as the first parameter (AC-11). The test is the lint; regression fails the build.
- **CI** — same Ubuntu-runner substrate as M03a: `apt-get install -y postgresql postgresql-contrib` (already in the workflow per the M03a gotcha in `docs/18 §6`); add Redis, Qdrant, Neo4j, MinIO test containers or local installs as required.

## Definition of Done (epic close)

- [ ] All eleven epic-level ACs above checked (`AC-1` … `AC-11`).
- [ ] All sub-issues `002`, `003`, `004`, `005`, `006`, `007` closed.
- [ ] M03 module-exit gate per [`docs/22 §6`](../22_Module_Roadmap.md#6-module-exit-gate-checklist-applied-to-every-module) green:
  - Schema migrated on dev + staging; RLS tests green; bootstrap reproducible in a container; storage layout documented under `infra/`.
  - Linked RTM IDs in `docs/16` reflect completion.
- [ ] `docs/18` updated with any new CI / runtime gotcha.
- [ ] `docs/26_Open_Issues/` mirror runs against GitHub Issues (when `gh` lands) so the tracker is the system of record going forward.

## Filed by

Orchestrator (wizard run, 2026-08-13) on behalf of the conductor, after the conductor chose **Option B** (markdown-fallback per `docs/25 §7`) to unblock the M03b pipeline in the absence of `gh` on this machine.
