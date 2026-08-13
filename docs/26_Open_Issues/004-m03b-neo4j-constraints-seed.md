---
gh_issue_number: null
gh_issue_url: null
local_id: 004
type: feat
priority: high
area: [backend, data]
title: "feat(data): provision Neo4j constraints + seed for 11 node kinds"
module: M03b
rtm_ids: [FR-038, FR-041, NFR-013]
filed: 2026-08-13
filed_by: orchestrator
status: open
parent_local_id: 001
sub_issue_local_ids: []
mirror_pending: true
---

# feat(data): provision Neo4j constraints + seed for 11 node kinds

> Sub-issue of [`001-m03b-storage-substrate`](./001-m03b-storage-substrate.md). Tracker-blocked; mirrors the would-be GitHub Issue body per [`docs/26/README.md`](../26_Open_Issues/README.md).

## Summary

Provision the Neo4j Community graph that M11 (Knowledge & Search) will populate with the source-to-report lineage and the cross-domain query surface. Ships uniqueness + existence constraints for the 11 node kinds enumerated in `docs/07 §4` (sources, findings, automations, products, processes, industries, technologies, APIs, events, architectures, opportunities), an idempotent seed script, and the `Neo4jAdapter` Protocol.

## Linked Requirement ID(s)

`FR-038` (Knowledge graph linking) · `FR-041` (Evidence and confidence at fact/relationship level) · `NFR-013` (Storage adapters behind interfaces)

## Parent epic ACs satisfied

`AC-1` (provisioner idempotency) · `AC-4` (constraints + seed) · `AC-7` (docker-compose wiring) · `AC-8` (cross-tenant denial) · `AC-6` (Protocol contract — `Neo4jAdapter`)

## Acceptance Criteria

- [ ] **AC-3a** Uniqueness constraints on the canonical key for each of the 11 node kinds: `(Source.source_id)`, `(Finding.finding_id)`, `(Automation.automation_id)`, `(Product.product_id)`, `(Process.process_id)`, `(Industry.industry_code)`, `(Technology.technology_id)`, `(API.api_id)`, `(Event.event_id)`, `(Architecture.architecture_id)`, `(Opportunity.opportunity_id)`. The keys match `docs/07 §4` and the M03a `findings` / `automations` Postgres tables.
- [ ] **AC-3b** Existence constraints on the FR-041 evidence/confidence properties: every node has `evidence_id` (keyword) + `confidence` (float, 0.0–1.0); every relationship has `evidence_id` + `confidence`. Schema-level enforcement so a missing field is a constraint violation, not a silent downstream bug.
- [ ] **AC-3c** Idempotent seed script `backend/app/db/neo4j/seed.cypher` (or `seed.py` if a programmatic generator is preferred): re-running produces no duplicates, no orphaned nodes. Seed includes: the 16 industries from `docs/07 §5`, the 5 evidence-label enums from `docs/07 §6`, and the 6 change-classification enums from `docs/07 §7`.
- [ ] **AC-3d** `pytest tests/integration/test_neo4j_constraints.py` green: a duplicate canonical key raises; a missing `evidence_id` on a node raises; a cross-tenant traversal (a query that does not constrain by `tenant_id` first) raises at the application layer (AC-8, FR-057). Note: Neo4j does not have row-level security; tenant isolation is enforced in the adapter layer via mandatory `tenant_id` as the first predicate, plus a CI test that catches adapters that forget it.
- [ ] **AC-3e** `backend/app/storage/neo4j_adapter.py` ships `Neo4jAdapter` Protocol with: `merge_node`, `merge_relationship`, `find_path`, `cross_domain_query`, `temporal_query`, `graph_health`. Inherits the shape pattern from `002`'s `RedisAdapter`.
- [ ] **AC-3f** Docker Compose service: `neo4j:5-community` with `NEO4J_PLUGINS=[""]` (no APOC for Community), `NEO4J_AUTH=neo4j/<from-secret>`; persistent volume; healthcheck on `:7474` HTTP.
- [ ] **AC-3g** CI on the Ubuntu runner: spin a Neo4j container for integration tests; pin the image SHA; pre-allocate the heap to match the docker-compose dev sizing (the M03a pattern of substrate == CI version applies).

## Out of Scope

- The lineage-query runtime (M11 ships the actual `find_path` invocations against real findings). M03b ships the schema and the seed; M11 wires it to the M09 evidence output.
- APOC / GDS plugins. Neo4j Community does not ship them; M16's prod deployment can re-evaluate if a workload demands APOC.
- Cross-region replication / clustering. Per `docs/18 §8` Neo4j HA is a M16 concern.

## Tests Required

- **Integration** — `test_neo4j_constraints.py` (AC-3d).
- **Contract** — `Neo4jAdapter` Protocol method signatures; tenant-id-first assertion (catches adapters that forget the mandatory predicate).
- **Ops** — Docker Compose `neo4j` service healthcheck is green; seed re-run produces no diff.

## Definition of Done

- [ ] All ACs above checked.
- [ ] Linked RTM IDs in `docs/16` updated.
- [ ] `backend/app/db/neo4j/seed.cypher` (or `.py`) committed + idempotent.
- [ ] Any new CI gotcha pinned in `docs/18 §6`.
- [ ] PR title `feat(data): provision Neo4j constraints + seed for 11 node kinds (FR-038, FR-041, NFR-013)`.
- [ ] Sub-issue AC ledger flipped at merge-time per `docs/25 §8`.

## Filed by

Orchestrator, 2026-08-13. Sub-issue of epic `001-m03b-storage-substrate`.
